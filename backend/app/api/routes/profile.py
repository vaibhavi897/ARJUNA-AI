"""Profile read/write endpoints used by the Settings & Profile screens.

These are the same section writers onboarding uses, so a change made in
settings flows through identical validation, scoring and activity logging.
That is what keeps the dashboard in sync with a single source of truth.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.models import StudentSkill
from app.modules.activity import log_activity
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.onboarding import sync_onboarding_state
from app.modules.profile import service as profile_service
from app.modules.scoring.service import refresh_scores
from app.schemas.common import ActionResult
from app.schemas.profile import (
    AcademicStepIn,
    ExperienceStepIn,
    FullProfileOut,
    PersonalInfoIn,
    PreferencesStepIn,
    ProjectsStepIn,
    SkillsStepIn,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _after_write(
    db: DbSession,
    user: CurrentUser,
    *,
    change: str,
    activity_type: str,
    activity_title: str,
    description: str | None = None,
    skill_ids: list[int] | None = None,
    data: dict | None = None,
    message: str,
) -> ActionResult:
    profile_service.compute_profile_completion(db, user)
    sync_onboarding_state(db, user)
    log_activity(db, user.id, activity_type, activity_title, description)

    recalculated: list[str] = []
    if user.onboarding_completed:
        result = refresh_scores(db, user, change=change, skill_ids=skill_ids)
        recalculated = result["recalculated_roles"]

    db.commit()
    return ActionResult(message=message, recalculated_roles=recalculated, data=data)


@router.get("", response_model=FullProfileOut)
def get_profile(user: CurrentUser, db: DbSession) -> FullProfileOut:
    """Everything the student has entered. Single fetch used by all editors."""
    profile_service.compute_profile_completion(db, user)
    db.commit()
    return profile_service.build_full_profile(db, user)


@router.put("/personal", response_model=ActionResult)
def update_personal(payload: PersonalInfoIn, user: CurrentUser, db: DbSession) -> ActionResult:
    profile_service.save_personal_info(db, user, payload)
    return _after_write(
        db,
        user,
        change="personal",
        activity_type="profile_updated",
        activity_title="Personal information updated",
        message="Personal information updated.",
    )


@router.put("/academics", response_model=ActionResult)
def update_academics(payload: AcademicStepIn, user: CurrentUser, db: DbSession) -> ActionResult:
    created, updated, deleted = profile_service.save_academics(db, user, payload)
    return _after_write(
        db,
        user,
        change="academics",
        activity_type="academics_updated",
        activity_title="Academic details updated",
        description=f"{created} added, {updated} updated, {deleted} removed.",
        data={"created": created, "updated": updated, "deleted": deleted},
        message="Academic details updated.",
    )


@router.put("/skills", response_model=ActionResult)
def update_skills(payload: SkillsStepIn, user: CurrentUser, db: DbSession) -> ActionResult:
    result = profile_service.save_skills(db, user, payload)
    skill_ids = list(
        db.scalars(select(StudentSkill.skill_id).where(StudentSkill.user_id == user.id))
    )
    return _after_write(
        db,
        user,
        change="skills",
        activity_type="skill_added" if result["created"] else "profile_updated",
        activity_title="Skills updated",
        description=(
            f"{result['created']} added, {result['updated']} updated, "
            f"{result['deleted']} removed."
        ),
        skill_ids=skill_ids,
        data=result,
        message="Skills updated.",
    )


@router.put("/projects", response_model=ActionResult)
def update_projects(payload: ProjectsStepIn, user: CurrentUser, db: DbSession) -> ActionResult:
    created, updated, deleted = profile_service.save_projects(db, user, payload)
    return _after_write(
        db,
        user,
        change="projects",
        activity_type="project_added" if created else "project_updated",
        activity_title="Projects updated",
        description=f"{created} added, {updated} updated, {deleted} removed.",
        data={"created": created, "updated": updated, "deleted": deleted},
        message="Projects updated.",
    )


@router.put("/experience", response_model=ActionResult)
def update_experience(
    payload: ExperienceStepIn, user: CurrentUser, db: DbSession
) -> ActionResult:
    result = profile_service.save_experience_step(db, user, payload)
    return _after_write(
        db,
        user,
        change="experience",
        activity_type="experience_added",
        activity_title="Experience and achievements updated",
        description=None,
        data=result,
        message="Experience, certifications and achievements updated.",
    )


@router.put("/preferences", response_model=ActionResult)
def update_preferences(
    payload: PreferencesStepIn, user: CurrentUser, db: DbSession
) -> ActionResult:
    result = profile_service.save_preferences(db, user, payload)
    return _after_write(
        db,
        user,
        change="preferences",
        activity_type="preferences_updated",
        activity_title="Career preferences updated",
        description=", ".join(result.get("selected_roles", []))[:400] or None,
        data=result,
        message="Career preferences updated.",
    )
