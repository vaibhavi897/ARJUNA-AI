"""Scoring orchestration: what to rescore after a given profile change.

Deterministic scoring is cheap, but rescoring everything on every keystroke-level
change is still wasteful and makes the activity feed noisy. This module maps a
change type to the roles it can actually move, then rescores only those and
rebuilds the roadmap.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models import JobRole, RoleRequiredSkill, StudentCareerPreference, User
from app.modules.activity import log_activity
from app.modules.scoring.engine import RoleScoreResult, recalculate_assessments
from app.modules.scoring.roadmap import generate_roadmap

logger = get_logger(__name__)

ChangeType = Literal[
    "onboarding_completed",
    "personal",
    "academics",
    "skills",
    "projects",
    "experience",
    "resume",
    "preferences",
    "manual",
]

# Components that every rubric evaluates. A change to one of these can move any
# role's score, so the whole active role set is rescored.
GLOBAL_CHANGES = {
    "onboarding_completed",
    "personal",
    "academics",
    "projects",
    "experience",
    "resume",
    "manual",
}


def _preferred_ids(db: Session, user: User) -> list[int]:
    return list(
        db.scalars(
            select(StudentCareerPreference.role_id)
            .where(StudentCareerPreference.user_id == user.id)
            .order_by(StudentCareerPreference.priority)
        )
    )


def resolve_affected_roles(
    db: Session, user: User, change: ChangeType, *, skill_ids: list[int] | None = None
) -> list[int] | None:
    """Role ids to rescore. ``None`` means every active role."""
    if change in GLOBAL_CHANGES:
        return None

    if change == "preferences":
        # Preferences change what the dashboard emphasises and what the roadmap
        # targets, not how any role scores.
        return _preferred_ids(db, user)

    if change == "skills":
        preferred = set(_preferred_ids(db, user))
        if skill_ids:
            referencing = set(
                db.scalars(
                    select(RoleRequiredSkill.role_id).where(
                        RoleRequiredSkill.skill_id.in_(skill_ids)
                    )
                )
            )
        else:
            return None
        affected = preferred | referencing
        return sorted(affected) if affected else None

    return None


def refresh_scores(
    db: Session,
    user: User,
    *,
    change: ChangeType = "manual",
    skill_ids: list[int] | None = None,
    rebuild_roadmap: bool = True,
    log: bool = True,
) -> dict[str, Any]:
    """Rescore the affected roles, rebuild the roadmap and log the assessment."""
    role_ids = resolve_affected_roles(db, user, change, skill_ids=skill_ids)
    results: list[RoleScoreResult] = recalculate_assessments(
        db, user, role_ids=role_ids, reason=change
    )

    if rebuild_roadmap:
        # The roadmap needs results for the roles it targets, so when a partial
        # rescore ran, top up with the roles the roadmap will look at.
        target_ids = _preferred_ids(db, user)
        have = {r.role_id for r in results}
        missing = [rid for rid in target_ids if rid not in have]
        if missing:
            results += recalculate_assessments(db, user, role_ids=missing, reason=change)
        if results:
            generate_roadmap(db, user, results)

    role_names = [r.role_name for r in results]
    if log and results:
        top = max(results, key=lambda r: r.score)
        log_activity(
            db,
            user.id,
            "assessment_completed",
            f"Readiness scores updated ({len(results)} role(s))",
            f"Best match right now: {top.role_name} at {top.score}/100.",
            details={
                "change": change,
                "roles": [
                    {"role": r.role_name, "score": r.score, "band": r.band} for r in results
                ],
            },
        )

    return {
        "recalculated_roles": role_names,
        "scored": [{"role": r.role_name, "score": r.score, "band": r.band} for r in results],
    }


def role_by_slug(db: Session, slug: str) -> JobRole | None:
    return db.scalar(select(JobRole).where(JobRole.slug == slug))
