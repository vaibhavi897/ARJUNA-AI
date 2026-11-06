"""Learning plans: Gemini decides WHAT to learn; the scheduler decides WHEN.

Generation never leaves a half-written plan: all Gemini calls finish and validate
before anything is persisted. Regeneration keeps completed, partial, skipped and
user-pinned work and only replaces the open future portion.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import (
    LearningGoal,
    LearningMilestone,
    LearningPlan,
    LearningTask,
    LearningTopic,
    LearningTrack,
    TopicProficiency,
    User,
)
from app.modules.careerverse import gemini_service
from app.modules.learning import ai, events, scheduler, skill_gap
from app.modules.learning.scheduler import Unit

logger = get_logger(__name__)
OPEN = ("pending", "rescheduled")
LEARNING_FILL = 0.88  # target share of learning capacity Gemini is asked to fill


class PlanError(RuntimeError):
    """Raised with a user-readable message when a plan cannot be generated."""


def today() -> dt.date:
    return dt.date.today()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ------------------------------------------------------------------ goals
def pick_track(db: Session, role: str, track_slug: str | None) -> LearningTrack | None:
    if track_slug:
        return db.scalar(select(LearningTrack).options(selectinload(LearningTrack.topics)).where(LearningTrack.slug == track_slug))
    tracks = list(db.scalars(select(LearningTrack).options(selectinload(LearningTrack.topics))))
    words = set(re.findall(r"[a-z]{3,}", role.lower()))
    best = max(tracks, key=lambda t: len(words & set(re.findall(r"[a-z]{3,}", t.title.lower()))), default=None)
    return best if best and words & set(re.findall(r"[a-z]{3,}", best.title.lower())) else None


def create_goal(db: Session, user: User, data: dict[str, Any]) -> LearningGoal:
    track = pick_track(db, data["target_role"], data.get("track_slug"))
    goal = LearningGoal(
        user_id=user.id, track_id=track.id if track else None, target_role=data["target_role"].strip(), duration_days=data["duration_days"],
        daily_hours=data["daily_hours"], study_days=sorted(set(data["study_days"])), start_date=data["start_date"],
        existing_knowledge=(data.get("existing_knowledge") or None), skip_topics=data.get("skip_topics", []), focus_areas=data.get("focus_areas", []),
        target_companies=data.get("target_companies", []), breaks=data.get("breaks", []),
    )
    db.add(goal)
    db.flush()
    events.log(db, user.id, "goal_created", "goal", goal.id, role=goal.target_role, days=goal.duration_days)
    return goal


# ------------------------------------------------------------------ generation helpers
def _topic_title_map(track: LearningTrack | None) -> dict[str, str]:
    return {t.slug: t.title for t in (track.topics if track else [])}


def _candidates(track: LearningTrack | None, phase_key: str, covered: set[str], skip: set[str]) -> list[dict[str, Any]]:
    if track is None:
        return []
    titles = _topic_title_map(track)
    out = []
    for t in track.topics:
        if t.phase != phase_key or t.slug in covered or t.slug in skip or t.title.lower() in skip:
            continue
        out.append({"title": t.title, "subject": t.subject, "hours": t.est_hours, "prerequisites": [titles.get(p, p) for p in t.prerequisites]})
    return out


def _weak_topics(db: Session, user_id: int) -> list[str]:
    rows = db.scalars(select(TopicProficiency).where(TopicProficiency.user_id == user_id, TopicProficiency.status.in_(("learning", "developing", "needs_revision"))).order_by(TopicProficiency.mastery_score))
    return [r.topic for r in rows][:12]


def _phase_shares(track: LearningTrack | None) -> list[tuple[str, str, float]]:
    phases = (track.phases if track and track.phases else [])
    work = [(p["key"], p["title"], float(p["share"])) for p in phases if p["key"] != "final"] or [("foundation", "Foundation", 0.35), ("intermediate", "Intermediate", 0.35), ("advanced", "Advanced", 0.2), ("projects", "Projects", 0.1)]
    total = sum(s for _, _, s in work)
    return [(k, t, s / total) for k, t, s in work]


def _generate_units(*, goal: LearningGoal, track: LearningTrack | None, level: str, covered: set[str], phases: list[tuple[str, str, float]], target_minutes: int, daily_minutes: int, weak: list[str], notes: str = "") -> list[Unit]:
    skip = {s.lower() for s in goal.skip_topics} | {slugify(s) for s in goal.skip_topics}
    units: list[Unit] = []
    done_titles: list[str] = [t.title for t in (track.topics if track else []) if t.slug in covered]
    for key, title, share in phases:
        budget = max(60, int(target_minutes * share))
        cands = _candidates(track, key, covered, skip)
        try:
            raw = ai.phase_units(role=goal.target_role, level=level, phase_title=title, phase_key=key, budget_minutes=budget, candidates=cands, already_covered=done_titles,
                                 focus=goal.focus_areas, companies=goal.target_companies, weak_topics=weak, notes=notes or (goal.existing_knowledge or ""), daily_minutes=daily_minutes)
        except gemini_service.GeminiUnavailable as exc:
            raise PlanError(f"Gemini could not generate the '{title}' phase right now. Nothing was saved; please try again in a minute. ({str(exc)[:120]})") from exc
        for r in raw:
            units.append(Unit(title=r["title"], est_minutes=int(r["est_minutes"]), category=r["category"], phase=key, topic=r["topic"], topic_slug=slugify(r["topic"]),
                              subtopics=r["subtopics"], objectives=r["objectives"], assignment=r["assignment"] or None,
                              resources=[{**x, "verified": False} for x in r["resources"]], difficulty=r["difficulty"]))
        done_titles += [r["topic"] for r in raw]
    return units


def _stretch(units: list[Unit], capacity: int) -> list[Unit]:
    """If Gemini under-fills the calendar, deepen practice time (bounded) instead of leaving empty days."""
    total = sum(u.est_minutes for u in units)
    if not units or total >= capacity * 0.9:
        return units
    factor = min(1.5, capacity * 0.92 / total)
    for u in units:
        u.est_minutes = int(u.est_minutes * factor)
    return units


def _fill_empty_days(slots: list[scheduler.Slot], study_dates: list[dt.date], daily_minutes: int) -> list[scheduler.Slot]:
    have = {s.date for s in slots}
    covered_topics: list[str] = []
    out: list[scheduler.Slot] = []
    by_date: dict[dt.date, list[scheduler.Slot]] = {}
    for s in slots:
        by_date.setdefault(s.date, []).append(s)
    for d in study_dates:
        if d in have:
            out += by_date[d]
            for s in by_date[d]:
                if s.unit and s.unit.topic and s.unit.topic not in covered_topics:
                    covered_topics.append(s.unit.topic)
        else:
            topic = covered_topics[(len(out)) % len(covered_topics)] if covered_topics else "your current focus area"
            out.append(scheduler.Slot(d, "practice", f"Open practice: {topic}", min(daily_minutes, 60), phase=None, topics_covered=[topic]))
    return out


def _persist_slots(db: Session, plan: LearningPlan, goal: LearningGoal, slots: list[scheduler.Slot], rest_dates: list[dt.date], week_offset: int = 0) -> None:
    pos: dict[dt.date, int] = {}
    for s in slots:
        pos[s.date] = pos.get(s.date, -1) + 1
        u = s.unit
        topics = s.topics_covered
        objectives = (u.objectives if u else
                      ([f"Review: {', '.join(topics[:4])}", "Recall from memory first, then check your notes"] if s.category == "revision" and topics else
                       ["Check your understanding of recent topics", "Review mistakes and add them to revision"] if s.category == "assessment" else []))
        assignment = (u.assignment if u else
                      (f"Generate a quiz on: {', '.join(topics[:5])}" if s.category == "assessment" and topics else None))
        db.add(LearningTask(
            plan_id=plan.id, user_id=plan.user_id, date=s.date, original_date=s.date, position=pos[s.date], category=s.category, phase=s.phase, title=s.title,
            topic=(u.topic if u else (topics[0] if topics else None)), topic_slug=(u.topic_slug if u else None), subtopics=(u.subtopics if u else topics[:8]),
            objectives=objectives, assignment=assignment, resources=(u.resources if u else []), est_minutes=s.est_minutes, difficulty=(u.difficulty if u else None),
        ))
    for d in rest_dates:
        db.add(LearningTask(plan_id=plan.id, user_id=plan.user_id, date=d, original_date=d, category="rest", title="Rest day", est_minutes=0, status="completed", progress_pct=100))
    # weekly milestones come from the assessment slots
    week = week_offset
    for s in slots:
        if s.category == "assessment":
            week += 1
            final = s.title.startswith("Final")
            topics = ", ".join(s.topics_covered[:3])
            db.add(LearningMilestone(plan_id=plan.id, week_no=week, title="Final assessment" if final else f"Checkpoint {week}: {topics or 'weekly review'}", description=("Prove readiness for the target role." if final else f"Topics: {', '.join(s.topics_covered)}"), phase=s.phase, due_date=s.date))


def _phase_summary(db: Session, plan_id: int, track: LearningTrack | None) -> list[dict[str, Any]]:
    titles = {p["key"]: p["title"] for p in (track.phases if track else [])} or {}
    rows = db.execute(select(LearningTask.phase, func.min(LearningTask.date), func.max(LearningTask.date), func.count()).where(LearningTask.plan_id == plan_id, LearningTask.phase.is_not(None), LearningTask.category != "rest").group_by(LearningTask.phase)).all()
    out = [{"key": k, "title": titles.get(k, k.title()), "start": a.isoformat(), "end": b.isoformat(), "tasks": n} for k, a, b, n in rows]
    order = {"foundation": 0, "intermediate": 1, "advanced": 2, "projects": 3, "final": 4}
    return sorted(out, key=lambda p: order.get(p["key"], 9))


# ------------------------------------------------------------------ public: generate
def generate_plan(db: Session, user: User, goal: LearningGoal) -> LearningPlan:
    track = db.scalar(select(LearningTrack).options(selectinload(LearningTrack.topics)).where(LearningTrack.id == goal.track_id)) if goal.track_id else None
    analysis = skill_gap.analyse(db, user, track, goal.skip_topics, goal.existing_knowledge or "") if track else {"starting_level": "beginner", "matched": [], "missing": [], "matched_titles": [], "missing_titles": [], "coverage": {}, "profile_has_data": False, "topic_scores": {}, "method": "no matching track"}
    explanation = skill_gap.explain(db, goal.target_role, analysis)

    daily = int(goal.daily_hours * 60)
    study_dates, rest_dates = scheduler.plan_dates(goal.start_date, goal.duration_days, goal.study_days, goal.breaks)
    if len(study_dates) < 3:
        raise PlanError("These dates leave fewer than 3 study days. Choose more study days or a longer duration.")
    capacity = scheduler.learning_capacity_minutes(study_dates, daily, goal.study_days)
    units = _generate_units(goal=goal, track=track, level=analysis["starting_level"], covered=set(analysis["matched"]) if analysis["profile_has_data"] else set(),
                            phases=_phase_shares(track), target_minutes=int(capacity * LEARNING_FILL), daily_minutes=daily, weak=_weak_topics(db, user.id))
    kept, dropped = scheduler.fit_units(units, capacity)
    kept = _stretch(kept, capacity)
    slots, unplaced, _ = scheduler.place_all(kept, study_dates, daily, goal.study_days)
    dropped = dropped + unplaced
    slots = _fill_empty_days(slots, study_dates, daily)

    for old in db.scalars(select(LearningPlan).where(LearningPlan.user_id == user.id, LearningPlan.status == "active")):
        old.status = "archived"
    end = goal.start_date + dt.timedelta(days=goal.duration_days - 1)
    version = (db.scalar(select(func.max(LearningPlan.version)).where(LearningPlan.goal_id == goal.id)) or 0) + 1
    plan = LearningPlan(goal_id=goal.id, user_id=user.id, version=version, status="active", summary=explanation.get("summary"), starting_level=analysis["starting_level"],
                        skill_gap={**analysis, "explanation": explanation, "dropped_units": [u.title for u in dropped]}, phases=[], start_date=goal.start_date, end_date=end, model=settings.GEMINI_MODEL)
    db.add(plan)
    db.flush()
    _persist_slots(db, plan, goal, slots, rest_dates)
    db.flush()
    plan.phases = _phase_summary(db, plan.id, track)
    events.log(db, user.id, "plan_generated", "plan", plan.id, days=goal.duration_days, units=len(kept), dropped=len(dropped))
    db.commit()
    return plan


# ------------------------------------------------------------------ regeneration of the future
def adaptive_adjustments(db: Session, plan: LearningPlan) -> dict[str, Any]:
    """Explainable workload advice from the learner's own completion pattern. Advisory only."""
    since = today() - dt.timedelta(days=14)
    rows = list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.date >= since, LearningTask.date < today(), LearningTask.category != "rest")))
    if len(rows) < 5:
        return {"enough_data": False, "notes": ["Not enough recent activity yet to tune the workload."]}
    done = [t for t in rows if t.status in ("completed", "partial")]
    rate = len(done) / len(rows)
    ratios = [t.actual_minutes / t.est_minutes for t in done if t.actual_minutes and t.est_minutes]
    diffs = [t.self_difficulty for t in done if t.self_difficulty]
    avg_ratio = sum(ratios) / len(ratios) if ratios else None
    avg_diff = sum(diffs) / len(diffs) if diffs else None
    factor, notes = 1.0, []
    if rate < 0.6:
        factor = 0.8
        notes.append(f"You completed {rate:.0%} of tasks in the last two weeks, so a lighter daily load (-20%) is suggested.")
    elif rate > 0.95 and (avg_ratio is None or avg_ratio < 0.85):
        factor = 1.15
        notes.append("You are finishing everything faster than planned; a slightly heavier load (+15%) would use your time better.")
    if avg_ratio and avg_ratio > 1.3:
        factor = min(factor, 0.9)
        notes.append("Tasks are taking you about 30% longer than estimated, so estimates will be raised.")
    if avg_diff and avg_diff >= 4:
        notes.append("You rated recent tasks as hard; the next topics will include more practice and prerequisites.")
    if not notes:
        notes.append("Your pace matches the plan. No change suggested.")
    return {"enough_data": True, "completion_rate": round(rate, 2), "time_ratio": round(avg_ratio, 2) if avg_ratio else None, "avg_self_difficulty": round(avg_diff, 2) if avg_diff else None, "suggested_daily_factor": factor, "notes": notes}


def regenerate_future(db: Session, user: User, plan: LearningPlan, *, daily_minutes: int | None = None, reason: str = "manual") -> dict[str, Any]:
    goal = plan.goal
    track = db.scalar(select(LearningTrack).options(selectinload(LearningTrack.topics)).where(LearningTrack.id == goal.track_id)) if goal.track_id else None
    from_date = max(today() + dt.timedelta(days=1), plan.start_date)
    if from_date > plan.end_date:
        raise PlanError("The plan has no future days left to regenerate.")
    all_tasks = list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id)))
    future_rest = [t for t in all_tasks if t.category == "rest" and t.date >= from_date]
    keep = [t for t in all_tasks if t not in future_rest and (t.date < from_date or t.status in ("completed", "partial", "skipped") or t.locked_by_user)]
    replace = [t for t in all_tasks if t not in keep and t not in future_rest]
    if not replace:
        raise PlanError("There is no open future work to regenerate.")
    daily = daily_minutes or int(goal.daily_hours * 60)
    study_dates, rest_dates = scheduler.plan_dates(from_date, (plan.end_date - from_date).days + 1, goal.study_days, goal.breaks)
    study_dates = [d for d in study_dates if not any(t.date == d and t in keep and t.category != "rest" and t.locked_by_user for t in all_tasks)]
    if len(study_dates) < 2:
        raise PlanError("Too few study days remain before the deadline. Extend your availability or the end date.")

    old_by_phase: dict[str, int] = {}
    for t in replace:
        if t.category in ("learn", "practice", "project") and t.phase:
            old_by_phase[t.phase] = old_by_phase.get(t.phase, 0) + t.est_minutes
    total_old = sum(old_by_phase.values()) or 1
    titles = {k: t for k, t, _ in _phase_shares(track)}
    phases = [(k, titles.get(k, k.title()), v / total_old) for k, v in old_by_phase.items()] or _phase_shares(track)
    covered_slugs = {t.topic_slug for t in keep if t.topic_slug and t.status in ("completed", "partial")}
    gap_covered = set(plan.skill_gap.get("matched", []))
    capacity = scheduler.learning_capacity_minutes(study_dates, daily, goal.study_days)
    weak = _weak_topics(db, user.id)
    notes = f"Regenerating the remaining plan ({reason}). Prioritise weak topics and keep prerequisites in order."
    units = _generate_units(goal=goal, track=track, level=plan.starting_level or "beginner", covered=covered_slugs | gap_covered, phases=phases, target_minutes=int(capacity * LEARNING_FILL), daily_minutes=daily, weak=weak, notes=notes)
    kept_units, dropped = scheduler.fit_units(units, capacity)
    kept_units = _stretch(kept_units, capacity)
    slots, unplaced, _ = scheduler.place_all(kept_units, study_dates, daily, goal.study_days)
    dropped = dropped + unplaced
    slots = _fill_empty_days(slots, study_dates, daily)

    for t in replace + future_rest:
        db.delete(t)
    max_week = db.scalar(select(func.max(LearningMilestone.week_no)).where(LearningMilestone.plan_id == plan.id, LearningMilestone.due_date < from_date)) or 0
    db.execute(delete(LearningMilestone).where(LearningMilestone.plan_id == plan.id, LearningMilestone.due_date >= from_date, LearningMilestone.completed.is_(False)))
    db.flush()
    _persist_slots(db, plan, goal, slots, rest_dates, week_offset=max_week)
    db.flush()
    plan.version += 1
    plan.phases = _phase_summary(db, plan.id, track)
    plan.skill_gap = {**plan.skill_gap, "dropped_units": [u.title for u in dropped]}
    events.log(db, user.id, "plan_regenerated", "plan", plan.id, reason=reason, replaced=len(replace), new=len(slots))
    db.commit()
    return {"replaced": len(replace), "created": len(slots), "kept": len(keep), "dropped_units": [u.title for u in dropped]}


# ------------------------------------------------------------------ missed work
def _open_missed(db: Session, plan: LearningPlan) -> list[LearningTask]:
    return list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.status.in_(OPEN), LearningTask.date < today(), LearningTask.category != "rest").order_by(LearningTask.date, LearningTask.position)))


def missed_preview(db: Session, plan: LearningPlan) -> dict[str, Any]:
    goal = plan.goal
    missed = _open_missed(db, plan)
    if not missed:
        return {"missed": 0, "moves": [], "overflow": [], "significant": False}
    daily = int(goal.daily_hours * 60)
    study_dates, _ = scheduler.plan_dates(today(), (plan.end_date - today()).days + 1, goal.study_days, goal.breaks)
    load: dict[dt.date, int] = {}
    for t in db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.status.in_(OPEN), LearningTask.date >= today(), LearningTask.category != "rest")):
        load[t.date] = load.get(t.date, 0) + t.est_minutes
    # assessments/final stay the last items; only move learn/practice/project/revision
    movable = [t for t in missed if t.category != "assessment" or not t.title.startswith("Final")]
    moves, overflow = scheduler.redistribute([(t.id, t.date, t.position, t.est_minutes) for t in movable], study_dates, load, daily)
    by_id = {t.id: t for t in missed}
    return {
        "missed": len(missed),
        "moves": [{"task_id": m.task_id, "title": by_id[m.task_id].title, "from": m.from_date.isoformat(), "to": m.to_date.isoformat()} for m in moves],
        "overflow": [{"task_id": i, "title": by_id[i].title} for i in overflow],
        "significant": len(moves) >= 5 or bool(overflow),
        "deadline": plan.end_date.isoformat(),
        "message": (f"{len(moves)} missed task(s) can be moved before your deadline." + (f" {len(overflow)} will not fit unless you add study time or skip them." if overflow else "")),
    }


def missed_apply(db: Session, user: User, plan: LearningPlan) -> dict[str, Any]:
    preview = missed_preview(db, plan)
    moved = 0
    for m in preview["moves"]:
        t = db.get(LearningTask, m["task_id"])
        if t and t.plan_id == plan.id:
            t.date = dt.date.fromisoformat(m["to"])
            t.status = "rescheduled"
            t.reschedule_count += 1
            moved += 1
    events.log(db, user.id, "missed_redistributed", "plan", plan.id, moved=moved, overflow=len(preview["overflow"]))
    db.commit()
    return {"moved": moved, "overflow": preview["overflow"]}
