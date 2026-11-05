"""Improvement roadmap generation.

Tasks are derived from the same gap data that produced the scores, so every
recommendation can state which role it helps and how many points are at stake.
Completion state survives regeneration: a task the student already ticked off
stays completed if it reappears.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.logging_config import get_logger
from app.models import (
    ImprovementRoadmap,
    JobRole,
    RoadmapTask,
    RoleAssessment,
    SkillGapAnalysis,
    StudentCareerPreference,
    User,
)
from app.modules.scoring.engine import RoleScoreResult

logger = get_logger(__name__)

MAX_TASKS = 12

DURATIONS = {
    "learn_skill": "3-4 weeks",
    "deepen_skill": "2-3 weeks",
    "build_project": "4-6 weeks",
    "demonstrate_skill": "2-3 weeks",
    "certification": "4-8 weeks",
    "domain_study": "1-2 weeks",
    "resume": "2-3 days",
    "experience": "1-2 months",
    "academics": "1 semester",
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _target_roles(db: Session, user: User, results: list[RoleScoreResult]) -> list[int]:
    """Preferred roles if set, else the three best-scoring roles."""
    preferred = list(
        db.scalars(
            select(StudentCareerPreference.role_id)
            .where(StudentCareerPreference.user_id == user.id)
            .order_by(StudentCareerPreference.priority)
        )
    )
    if preferred:
        return preferred
    return [r.role_id for r in sorted(results, key=lambda r: r.score, reverse=True)[:3]]


def generate_roadmap(
    db: Session,
    user: User,
    results: list[RoleScoreResult],
    *,
    generator: str = "rule_based",
) -> ImprovementRoadmap:
    """Rebuild the student's active roadmap from the latest assessment data."""
    target_ids = _target_roles(db, user, results)
    by_role = {r.role_id: r for r in results}
    role_rows = {
        role.id: role
        for role in db.scalars(select(JobRole).where(JobRole.id.in_(target_ids or [0])))
    }

    candidates: list[dict[str, Any]] = []

    for role_id in target_ids:
        result = by_role.get(role_id)
        role = role_rows.get(role_id)
        if result is None or role is None:
            continue

        components = {c.component: c for c in result.components}

        missing = sorted(
            (g for g in result.gaps if g.status == "missing"),
            key=lambda g: (g.importance != "required", -g.points_lost),
        )
        for gap in missing[:3]:
            candidates.append(
                {
                    "title": f"Learn {gap.skill_name}",
                    "reason": (
                        f"{gap.skill_name} is a {gap.importance} skill for {role.name} at "
                        f"{gap.expected_proficiency} level, and it is missing from your profile."
                    ),
                    "priority": "high" if gap.importance == "required" else "medium",
                    "action_type": "learn_skill",
                    "expected_improvement_area": "Role Skills Match",
                    "expected_score_gain": _as_percentage_points(gap.points_lost, result),
                    "role_id": role_id,
                    "skill_id": gap.skill_id,
                }
            )

        for gap in [g for g in result.gaps if g.status == "claimed_only"][:2]:
            candidates.append(
                {
                    "title": f"Demonstrate {gap.skill_name} in a project or internship",
                    "reason": (
                        f"You list {gap.skill_name} but nothing in your profile uses it. "
                        "Evidence-backed skills earn close to full credit; claimed-only "
                        "skills do not."
                    ),
                    "priority": "medium",
                    "action_type": "demonstrate_skill",
                    "expected_improvement_area": "Role Skills Match",
                    "expected_score_gain": _as_percentage_points(gap.points_lost, result),
                    "role_id": role_id,
                    "skill_id": gap.skill_id,
                }
            )

        for gap in sorted(
            (g for g in result.gaps if g.status == "below_expected"),
            key=lambda g: -g.points_lost,
        )[:2]:
            candidates.append(
                {
                    "title": f"Take {gap.skill_name} to {gap.expected_proficiency} level",
                    "reason": (
                        f"{role.name} expects {gap.expected_proficiency} proficiency in "
                        f"{gap.skill_name}; your profile says {gap.student_proficiency}."
                    ),
                    "priority": "medium",
                    "action_type": "deepen_skill",
                    "expected_improvement_area": "Role Skills Match",
                    "expected_score_gain": _as_percentage_points(gap.points_lost, result),
                    "role_id": role_id,
                    "skill_id": gap.skill_id,
                }
            )

        projects = components.get("projects")
        if projects is not None and projects.ratio < 0.65:
            expected = projects.details.get("expected", 2)
            candidates.append(
                {
                    "title": f"Build a {role.short_label or role.name} style project",
                    "reason": (
                        f"You have {projects.details.get('relevant_count', 0)} clearly relevant "
                        f"project(s); this role expects around {expected}. A focused project is "
                        "the fastest way to convert listed skills into evidence."
                    ),
                    "priority": "high" if projects.ratio < 0.4 else "medium",
                    "action_type": "build_project",
                    "expected_improvement_area": "Projects & Practical Work",
                    "expected_score_gain": _component_headroom(projects, result),
                    "role_id": role_id,
                    "skill_id": None,
                }
            )

        domain = components.get("domain_knowledge")
        if domain is not None and domain.ratio < 0.6 and domain.details.get("missing"):
            topics = ", ".join(domain.details["missing"][:4])
            candidates.append(
                {
                    "title": f"Study core {role.domain.name} concepts: {topics}",
                    "reason": (
                        f"These concepts never appear in your profile or resume, so "
                        f"{role.name} interviewers have nothing to assess."
                    ),
                    "priority": "medium",
                    "action_type": "domain_study",
                    "expected_improvement_area": "Domain Knowledge",
                    "expected_score_gain": _component_headroom(domain, result),
                    "role_id": role_id,
                    "skill_id": None,
                }
            )

        certifications = components.get("certifications")
        if certifications is not None and certifications.ratio < 0.5:
            candidates.append(
                {
                    "title": f"Complete a certification relevant to {role.name}",
                    "reason": (
                        "This role's rubric expects at least "
                        f"{certifications.details.get('expected', 1)} certification(s). "
                        "A recognised course also strengthens your resume keywords."
                    ),
                    "priority": "low",
                    "action_type": "certification",
                    "expected_improvement_area": "Certifications",
                    "expected_score_gain": _component_headroom(certifications, result),
                    "role_id": role_id,
                    "skill_id": None,
                }
            )

        experience = components.get("experience")
        if experience is not None and experience.ratio < 0.4:
            candidates.append(
                {
                    "title": f"Apply for an internship aligned to {role.name}",
                    "reason": experience.explanation,
                    "priority": "high",
                    "action_type": "experience",
                    "expected_improvement_area": "Internships & Experience",
                    "expected_score_gain": _component_headroom(experience, result),
                    "role_id": role_id,
                    "skill_id": None,
                }
            )

        resume = components.get("resume_quality")
        if resume is not None and not resume.details.get("has_resume"):
            candidates.append(
                {
                    "title": "Upload a resume so it can be analysed",
                    "reason": resume.explanation,
                    "priority": "high",
                    "action_type": "resume",
                    "expected_improvement_area": "Resume Quality",
                    "expected_score_gain": _component_headroom(resume, result),
                    "role_id": None,
                    "skill_id": None,
                }
            )
        elif resume is not None and resume.ratio < 0.75:
            missing_keywords = resume.details.get("keyword_misses") or []
            detail = (
                "Missing role keywords: " + ", ".join(missing_keywords[:5])
                if missing_keywords
                else resume.explanation
            )
            candidates.append(
                {
                    "title": "Strengthen your resume bullets and keywords",
                    "reason": detail,
                    "priority": "medium",
                    "action_type": "resume",
                    "expected_improvement_area": "Resume Quality",
                    "expected_score_gain": _component_headroom(resume, result),
                    "role_id": role_id,
                    "skill_id": None,
                }
            )

        academics = components.get("academics")
        if (
            academics is not None
            and academics.details.get("cgpa_provided")
            and academics.ratio < 0.6
        ):
            candidates.append(
                {
                    "title": "Offset a below-target CGPA with demonstrable work",
                    "reason": (
                        f"{academics.explanation} CGPA moves slowly, so the practical route is "
                        "stronger projects, an internship and a relevant certification."
                    ),
                    "priority": "low",
                    "action_type": "academics",
                    "expected_improvement_area": "Academic Profile",
                    "expected_score_gain": None,
                    "role_id": role_id,
                    "skill_id": None,
                }
            )

    # Deduplicate by title, keeping the highest-priority / highest-gain instance.
    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = candidate["title"].lower()
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = candidate
            continue
        if PRIORITY_ORDER[candidate["priority"]] < PRIORITY_ORDER[existing["priority"]] or (
            (candidate.get("expected_score_gain") or 0) > (existing.get("expected_score_gain") or 0)
        ):
            deduped[key] = candidate

    ordered = sorted(
        deduped.values(),
        key=lambda c: (
            PRIORITY_ORDER[c["priority"]],
            -(c.get("expected_score_gain") or 0),
            c["title"],
        ),
    )[:MAX_TASKS]

    # Carry over completion state from the roadmap we are replacing.
    previous_status: dict[str, tuple[str, dt.datetime | None]] = {}
    for old in db.scalars(
        select(ImprovementRoadmap)
        .options(selectinload(ImprovementRoadmap.tasks))
        .where(ImprovementRoadmap.user_id == user.id, ImprovementRoadmap.is_active.is_(True))
    ):
        for task in old.tasks:
            previous_status[task.title.lower()] = (task.status, task.completed_at)
        old.is_active = False

    roadmap = ImprovementRoadmap(
        user_id=user.id,
        role_id=None,
        title="Your personalised improvement roadmap",
        summary=_summary_text(ordered, role_rows, target_ids),
        generator=generator,
        is_active=True,
        generated_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(roadmap)
    db.flush()

    for order, candidate in enumerate(ordered):
        status, completed_at = previous_status.get(candidate["title"].lower(), ("pending", None))
        db.add(
            RoadmapTask(
                roadmap_id=roadmap.id,
                related_skill_id=candidate.get("skill_id"),
                title=candidate["title"][:200],
                reason=candidate["reason"],
                priority=candidate["priority"],
                suggested_duration=DURATIONS.get(candidate["action_type"], "2-4 weeks"),
                expected_improvement_area=candidate.get("expected_improvement_area"),
                expected_score_gain=candidate.get("expected_score_gain"),
                action_type=candidate["action_type"],
                status=status,
                completed_at=completed_at,
                display_order=order,
            )
        )

    db.flush()
    logger.info("Generated roadmap with %s task(s) for user=%s", len(ordered), user.id)
    return roadmap


def _as_percentage_points(points_lost: float, result: RoleScoreResult) -> float | None:
    """Convert rubric points into points on the 0-100 score scale."""
    possible = result.match_summary.get("points_possible") or 0
    if not possible:
        return None
    return round(100 * points_lost / possible, 1)


def _component_headroom(component: Any, result: RoleScoreResult) -> float | None:
    possible = result.match_summary.get("points_possible") or 0
    if not possible:
        return None
    return round(100 * (component.weight - component.points) / possible, 1)


def _summary_text(
    tasks: list[dict[str, Any]], roles: dict[int, JobRole], target_ids: list[int]
) -> str:
    if not tasks:
        return (
            "No gaps were detected against your target roles. Keep your profile current "
            "and add new work as you complete it."
        )
    role_names = [roles[rid].name for rid in target_ids if rid in roles]
    high = sum(1 for t in tasks if t["priority"] == "high")
    focus = ", ".join(role_names[:3]) if role_names else "your best-matching roles"
    return (
        f"{len(tasks)} action(s) generated from your latest assessment, {high} marked "
        f"high priority. Targeted at: {focus}."
    )


def roadmap_payload(db: Session, user: User) -> dict[str, Any]:
    """The active roadmap in dashboard shape."""
    roadmap = db.scalar(
        select(ImprovementRoadmap)
        .options(
            selectinload(ImprovementRoadmap.tasks).selectinload(RoadmapTask.related_skill)
        )
        .where(ImprovementRoadmap.user_id == user.id, ImprovementRoadmap.is_active.is_(True))
        .order_by(ImprovementRoadmap.generated_at.desc())
    )
    if roadmap is None:
        return {
            "generated_at": None,
            "generator": "rule_based",
            "total_tasks": 0,
            "completed_tasks": 0,
            "completion_percent": 0,
            "tasks": [],
        }

    tasks = sorted(roadmap.tasks, key=lambda t: t.display_order)
    completed = sum(1 for t in tasks if t.status == "completed")
    return {
        "generated_at": roadmap.generated_at,
        "generator": roadmap.generator,
        "total_tasks": len(tasks),
        "completed_tasks": completed,
        "completion_percent": int(round(100 * completed / len(tasks))) if tasks else 0,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "reason": task.reason,
                "priority": task.priority,
                "suggested_duration": task.suggested_duration,
                "expected_improvement_area": task.expected_improvement_area,
                "expected_score_gain": task.expected_score_gain,
                "action_type": task.action_type,
                "status": task.status,
                "completed_at": task.completed_at,
                "related_skill": task.related_skill.name if task.related_skill else None,
                "role_name": None,
                "role_slug": None,
            }
            for task in tasks
        ],
    }


def latest_assessment_time(db: Session, user: User) -> dt.datetime | None:
    return db.scalar(
        select(RoleAssessment.computed_at)
        .where(RoleAssessment.user_id == user.id)
        .order_by(RoleAssessment.computed_at.desc())
        .limit(1)
    )


def gaps_for_role(db: Session, user_id: int, role_id: int) -> list[SkillGapAnalysis]:
    return list(
        db.scalars(
            select(SkillGapAnalysis)
            .where(
                SkillGapAnalysis.user_id == user_id,
                SkillGapAnalysis.role_id == role_id,
            )
            .order_by(SkillGapAnalysis.points_lost.desc())
        )
    )
