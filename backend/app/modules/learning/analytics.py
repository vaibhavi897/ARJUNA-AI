"""Overview, progress & mastery analytics and explainable recommendations."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LearningEvent, LearningMilestone, LearningPlan, LearningTask, PersonalizationFeedback, QuizSession, RevisionSchedule, TopicProficiency, User
from app.modules.learning import planner, revision
from app.modules.learning import tasks as task_service

STATUS_LABEL = {"not_started": "Not started", "learning": "Learning", "developing": "Developing", "needs_revision": "Needs revision", "strong": "Strong", "mastered": "Mastered"}
RL_MIN_EVENTS = 1500  # interactions needed before a learned policy could be trusted


def _minutes(t: LearningTask) -> int:
    return t.actual_minutes if t.actual_minutes else (t.est_minutes if t.status == "completed" else int(t.est_minutes * t.progress_pct / 100))


def streak(db: Session, user: User, today: dt.date | None = None) -> dict[str, int]:
    today = today or dt.date.today()
    days = set(d for (d,) in db.execute(select(func.date(LearningTask.completed_at)).where(LearningTask.user_id == user.id, LearningTask.completed_at.is_not(None))))
    days |= set(d for (d,) in db.execute(select(func.date(QuizSession.submitted_at)).where(QuizSession.user_id == user.id, QuizSession.submitted_at.is_not(None))))
    cur = 0
    d = today if today in days else today - dt.timedelta(days=1)
    while d in days:
        cur += 1
        d -= dt.timedelta(days=1)
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best, prev = max(best, run), d
    return {"current": cur, "best": best, "active_days": len(days)}


def recommendations(db: Session, user: User, plan: LearningPlan | None) -> list[dict[str, Any]]:
    """Rule-based policy. Every item states WHY it was suggested; the learner stays in control."""
    today = dt.date.today()
    recs: list[dict[str, Any]] = []
    if plan:
        missed = planner._open_missed(db, plan)
        if missed:
            recs.append({"id": "missed", "kind": "reschedule", "title": f"Reschedule {len(missed)} missed task{'s' if len(missed) > 1 else ''}", "reason": f"Open tasks from earlier dates are piling up (oldest: {missed[0].date.isoformat()}). Moving them keeps your deadline realistic.", "action": {"type": "open_missed"}})
        todays = list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.date == today, LearningTask.status.in_(task_service.OPEN), LearningTask.category != "rest")))
        if todays:
            recs.append({"id": "today", "kind": "task", "title": f"Start: {todays[0].title}", "reason": f"It is the first of {len(todays)} task(s) planned for today (~{sum(t.est_minutes for t in todays)} min).", "action": {"type": "open_day", "date": today.isoformat()}})
    due = [r for r in revision.due_reviews(db, user, within_days=0)]
    if due:
        recs.append({"id": "srs", "kind": "revision", "title": f"Revise: {due[0].topic}" + (f" (+{len(due) - 1} more)" if len(due) > 1 else ""), "reason": "Spaced repetition says these topics are due now; reviewing at this point locks them into long-term memory.", "action": {"type": "revision_quiz"}})
    weak = list(db.scalars(select(TopicProficiency).where(TopicProficiency.user_id == user.id, TopicProficiency.status.in_(("learning", "developing", "needs_revision"))).order_by(TopicProficiency.mastery_score).limit(2)))
    for w in weak:
        recs.append({"id": f"weak-{w.id}", "kind": "practice", "title": f"Practise {w.topic}", "reason": f"Your mastery is {w.mastery_score:.0f}% ({STATUS_LABEL[w.status].lower()}), based on {w.attempts} answered question(s).", "action": {"type": "quiz", "topic": w.topic}})
    st = streak(db, user)
    if st["current"] == 0 and st["best"] > 0:
        recs.append({"id": "streak", "kind": "habit", "title": "Do a 20-minute session today", "reason": f"Your best streak was {st['best']} days. A short session restarts the habit.", "action": {"type": "open_day", "date": today.isoformat()}})
    if not recs:
        recs.append({"id": "explore", "kind": "explore", "title": "Generate notes on a topic you are curious about" if plan else "Create your first learning plan", "reason": "Nothing urgent right now.", "action": {"type": "materials" if plan else "new_plan"}})
    return recs[:5]


def overview(db: Session, user: User) -> dict[str, Any]:
    today = dt.date.today()
    plan = task_service.active_plan(db, user)
    st = streak(db, user)
    quizzes = list(db.scalars(select(QuizSession).where(QuizSession.user_id == user.id, QuizSession.status == "submitted").order_by(QuizSession.submitted_at.desc()).limit(5)))
    weak = list(db.scalars(select(TopicProficiency).where(TopicProficiency.user_id == user.id, TopicProficiency.status.in_(("learning", "developing", "needs_revision"))).order_by(TopicProficiency.mastery_score).limit(5)))
    out: dict[str, Any] = {
        "has_plan": plan is not None, "streak": st,
        "recent_quizzes": [{"id": q.id, "topic": q.topic, "accuracy": q.report.get("accuracy"), "score": q.score, "max_score": q.max_score, "at": q.submitted_at.isoformat() if q.submitted_at else None} for q in quizzes],
        "weak_topics": [{"topic": w.topic, "mastery": w.mastery_score, "status": w.status, "status_label": STATUS_LABEL[w.status]} for w in weak],
        "upcoming_revisions": [{"topic": r.topic, "due": r.due_date.isoformat(), "interval_days": r.interval_days} for r in revision.due_reviews(db, user, within_days=7)[:6]],
        "recommendations": recommendations(db, user, plan), "plan": None,
    }
    if not plan:
        return out
    tasks = list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.category != "rest").order_by(LearningTask.date, LearningTask.position)))
    done = [t for t in tasks if t.status == "completed"]
    week_start = today - dt.timedelta(days=today.weekday())
    week = [t for t in tasks if week_start <= t.date < week_start + dt.timedelta(days=7)]
    nxt = db.scalar(select(LearningMilestone).where(LearningMilestone.plan_id == plan.id, LearningMilestone.due_date >= today, LearningMilestone.completed.is_(False)).order_by(LearningMilestone.due_date).limit(1))
    out["plan"] = {
        "id": plan.id, "goal": plan.goal.target_role, "starting_level": plan.starting_level, "summary": plan.summary, "start": plan.start_date.isoformat(), "end": plan.end_date.isoformat(),
        "day_number": max(1, min((today - plan.start_date).days + 1, (plan.end_date - plan.start_date).days + 1)), "total_days": (plan.end_date - plan.start_date).days + 1,
        "completion_pct": round(100 * len(done) / len(tasks), 1) if tasks else 0.0, "tasks_done": len(done), "tasks_total": len(tasks),
        "week": {"done": sum(1 for t in week if t.status == "completed"), "total": len(week)},
        "today": [task_service.task_out(t, today) for t in tasks if t.date == today],
        "upcoming": [task_service.task_out(t, today) for t in tasks if today < t.date <= today + dt.timedelta(days=7) and t.category != "rest"][:6],
        "missed": sum(1 for t in tasks if t.status in task_service.OPEN and t.date < today),
        "next_milestone": {"title": nxt.title, "due": nxt.due_date.isoformat()} if nxt else None, "phases": plan.phases,
    }
    return out


def progress(db: Session, user: User) -> dict[str, Any]:
    today = dt.date.today()
    plan = task_service.active_plan(db, user)
    since = today - dt.timedelta(days=119)
    rows = db.execute(select(LearningTask.completed_at, LearningTask.category).where(LearningTask.user_id == user.id, LearningTask.completed_at.is_not(None), LearningTask.completed_at >= dt.datetime.combine(since, dt.time.min, tzinfo=dt.timezone.utc))).all()
    heat: dict[str, dict[str, int]] = defaultdict(lambda: {"tasks": 0})
    for at, _ in rows:
        heat[at.date().isoformat()]["tasks"] += 1
    weekly = []
    if rows:
        by_week: dict[dt.date, int] = defaultdict(int)
        for r in rows:
            day = r[0].date()
            by_week[day - dt.timedelta(days=day.weekday())] += 1
        weekly = [{"week": w.isoformat(), "tasks": n} for w, n in sorted(by_week.items())]
    quizzes = list(db.scalars(select(QuizSession).where(QuizSession.user_id == user.id, QuizSession.status == "submitted").order_by(QuizSession.submitted_at)))
    prof = list(db.scalars(select(TopicProficiency).where(TopicProficiency.user_id == user.id).order_by(TopicProficiency.mastery_score.desc())))
    counts = {k: 0 for k in STATUS_LABEL}
    for p in prof:
        counts[p.status] += 1
    rev_total = rev_done = 0
    milestones: list[dict[str, Any]] = []
    phase_progress: list[dict[str, Any]] = []
    if plan:
        rv = list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.category == "revision")))
        rev_total, rev_done = len(rv), sum(1 for t in rv if t.status == "completed")
        milestones = [{"title": m.title, "due": m.due_date.isoformat(), "week": m.week_no, "completed": m.completed or m.due_date < today and _week_done(db, plan, m)} for m in plan.milestones]
        for ph in plan.phases:
            ts = list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.phase == ph["key"], LearningTask.category != "rest")))
            phase_progress.append({"key": ph["key"], "title": ph["title"], "done": sum(1 for t in ts if t.status == "completed"), "total": len(ts)})
    srs_count = db.scalar(select(func.count()).select_from(RevisionSchedule).where(RevisionSchedule.user_id == user.id)) or 0
    return {
        "heatmap": [{"date": k, **v} for k, v in sorted(heat.items())], "weekly": weekly, "streak": streak(db, user),
        "quiz_trend": [{"id": q.id, "topic": q.topic, "accuracy": q.report.get("accuracy", 0), "at": q.submitted_at.isoformat() if q.submitted_at else None, "scope": q.scope} for q in quizzes],
        "mastery": [{"topic": p.topic, "score": p.mastery_score, "status": p.status, "status_label": STATUS_LABEL[p.status], "attempts": p.attempts, "signals": p.signals} for p in prof], "mastery_counts": counts,
        "assessment_history": [{"id": q.id, "topic": q.topic, "scope": q.scope, "accuracy": q.report.get("accuracy"), "score": q.score, "max_score": q.max_score, "seconds": q.time_taken_seconds, "at": q.submitted_at.isoformat() if q.submitted_at else None} for q in reversed(quizzes)][:20],
        "revision": {"tasks_total": rev_total, "tasks_done": rev_done, "topics_tracked": srs_count, "due_now": len(revision.due_reviews(db, user, within_days=0))},
        "milestones": milestones, "phases": phase_progress, "weak": [p.topic for p in prof if p.status in ("learning", "developing", "needs_revision")][:8],
        "improvement": _improvement(quizzes), "status_labels": STATUS_LABEL,
    }


def _week_done(db: Session, plan: LearningPlan, m: LearningMilestone) -> bool:
    ts = list(db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.date > m.due_date - dt.timedelta(days=7), LearningTask.date <= m.due_date, LearningTask.category != "rest")))
    return bool(ts) and all(t.status == "completed" for t in ts)


def _improvement(quizzes: list[QuizSession]) -> list[dict[str, Any]]:
    by: dict[str, list[float]] = defaultdict(list)
    for q in quizzes:
        by[q.topic].append(q.report.get("accuracy", 0))
    return [{"topic": k, "first": v[0], "latest": v[-1], "change": round(v[-1] - v[0], 1), "attempts": len(v)} for k, v in by.items() if len(v) >= 2]


def personalization_status(db: Session, user: User) -> dict[str, Any]:
    events = db.scalar(select(func.count()).select_from(LearningEvent).where(LearningEvent.user_id == user.id)) or 0
    fb = db.scalar(select(func.count()).select_from(PersonalizationFeedback).where(PersonalizationFeedback.user_id == user.id)) or 0
    return {"policy": "rule_based", "events_collected": events, "feedback_collected": fb, "rl_min_events": RL_MIN_EVENTS, "rl_ready": events >= RL_MIN_EVENTS,
            "note": "Recommendations are transparent rules today. A learned policy (contextual bandit, then RL) is only enabled once enough real interaction data exists; it will optimise retention, assessment gains, consistency and sustainable workload, never time-in-app."}
