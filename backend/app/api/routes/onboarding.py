"""Onboarding wizard endpoints.

Each step saves independently, so progress is never lost between steps and an
interrupted onboarding resumes exactly where the student stopped.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.models import StudentSkill
from app.modules import onboarding as wizard
from app.modules.activity import log_activity
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.profile import service as profile_service
from app.modules.scoring.service import refresh_scores
from app.schemas.onboarding import OnboardingStatusOut, StepSaveResult
from app.schemas.profile import (
    AcademicStepIn,
    ExperienceStepIn,
    PersonalInfoIn,
    PreferencesStepIn,
    ProjectsStepIn,
    SkillsStepIn,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _finalise(
    db: DbSession,
    user: CurrentUser,
    step: int,
    message: str,
    *,
    change: str,
    data: dict | None = None,
    skill_ids: list[int] | None = None,
) -> StepSaveResult:
    """Shared tail for every step: completion, state, scoring, activity, commit."""
    completion, _ = profile_service.compute_profile_completion(db, user)
    flags = wizard.sync_onboarding_state(db, user)

    log_activity(
        db,
        user.id,
        "onboarding_step_completed",
        f"Completed onboarding step {step}: {wizard.STEP_BY_NUMBER[step].title}",
        None,
        details={"step": step},
    )

    recalculated: list[str] = []
    # Scores are only meaningful once the student has picked target roles and
    # has something to score; before that, scoring is skipped.
    if user.onboarding_completed:
        result = refresh_scores(db, user, change=change, skill_ids=skill_ids)
        recalculated = result["recalculated_roles"]

    db.commit()

    next_step = wizard.first_incomplete_step(flags)
    return StepSaveResult(
        message=message,
        step=step,
        next_step=next_step,
        completed=user.onboarding_completed,
        profile_completion=completion,
        companion_message=wizard.companion_message_for(step, done=True),
        recalculated_roles=recalculated,
        data=data,
    )


@router.get("/status", response_model=OnboardingStatusOut)
def status_endpoint(user: CurrentUser, db: DbSession) -> OnboardingStatusOut:
    wizard.sync_onboarding_state(db, user)
    db.commit()
    return OnboardingStatusOut(**wizard.build_status(db, user))


@router.post("/personal", response_model=StepSaveResult)
def save_personal(payload: PersonalInfoIn, user: CurrentUser, db: DbSession) -> StepSaveResult:
    profile_service.save_personal_info(db, user, payload)
    return _finalise(db, user, 1, "Personal information saved.", change="personal")


@router.post("/academics", response_model=StepSaveResult)
def save_academics(payload: AcademicStepIn, user: CurrentUser, db: DbSession) -> StepSaveResult:
    if not payload.entries:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add at least one education entry.",
        )
    created, updated, deleted = profile_service.save_academics(db, user, payload)
    return _finalise(
        db,
        user,
        2,
        "Academic background saved.",
        change="academics",
        data={"created": created, "updated": updated, "deleted": deleted},
    )


@router.post("/skills", response_model=StepSaveResult)
def save_skills(payload: SkillsStepIn, user: CurrentUser, db: DbSession) -> StepSaveResult:
    if not payload.skills:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add at least one skill.",
        )
    result = profile_service.save_skills(db, user, payload)
    skill_ids = list(
        db.scalars(select(StudentSkill.skill_id).where(StudentSkill.user_id == user.id))
    )
    return _finalise(
        db, user, 3, "Skills saved.", change="skills", data=result, skill_ids=skill_ids
    )


@router.post("/projects", response_model=StepSaveResult)
def save_projects(payload: ProjectsStepIn, user: CurrentUser, db: DbSession) -> StepSaveResult:
    # Projects are optional: a student with none is scored on their skills and
    # experience instead, so an empty list is a valid answer, not an error.
    created, updated, deleted = profile_service.save_projects(db, user, payload)
    return _finalise(
        db,
        user,
        4,
        "Projects saved." if payload.projects else "No projects added - that is fine.",
        change="projects",
        data={"created": created, "updated": updated, "deleted": deleted},
    )


@router.post("/experience", response_model=StepSaveResult)
def save_experience(
    payload: ExperienceStepIn, user: CurrentUser, db: DbSession
) -> StepSaveResult:
    # Experience is optional. A fresher with no internship is assessed on
    # projects and skills rather than penalised for the gap.
    result = profile_service.save_experience_step(db, user, payload)
    message = (
        "Experience and achievements saved."
        if (payload.experiences or payload.certifications or payload.achievements)
        else "Nothing added here - freshers are not penalised for this."
    )
    return _finalise(db, user, 5, message, change="experience", data=result)


@router.post("/preferences", response_model=StepSaveResult)
def save_preferences(
    payload: PreferencesStepIn, user: CurrentUser, db: DbSession
) -> StepSaveResult:
    if not payload.role_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select at least one target role so your profile can be scored.",
        )
    result = profile_service.save_preferences(db, user, payload)
    return _finalise(
        db, user, 7, "Career preferences saved.", change="preferences", data=result
    )


@router.post("/complete", response_model=StepSaveResult)
def complete(user: CurrentUser, db: DbSession) -> StepSaveResult:
    """Finish onboarding and run the first full assessment."""
    flags = wizard.completed_steps(db, user)
    if not wizard.all_required_complete(flags):
        missing = [
            wizard.STEP_BY_NUMBER[step].title
            for step in wizard.REQUIRED_STEPS
            if not flags.get(step)
        ]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Still incomplete: {', '.join(missing)}",
        )

    already = user.onboarding_completed
    user.onboarding_completed = True
    user.onboarding_step = wizard.TOTAL_STEPS
    completion, _ = profile_service.compute_profile_completion(db, user)

    if not already:
        log_activity(
            db,
            user.id,
            "onboarding_completed",
            "Onboarding completed",
            "Your first role-wise readiness assessment has been generated.",
        )

    result = refresh_scores(db, user, change="onboarding_completed")
    db.commit()

    return StepSaveResult(
        message="Onboarding complete. Your readiness scores are ready.",
        step=wizard.TOTAL_STEPS,
        next_step=wizard.TOTAL_STEPS,
        completed=True,
        profile_completion=completion,
        companion_message="All set. Generating your role-wise readiness scores now.",
        recalculated_roles=result["recalculated_roles"],
        data={"scored": result["scored"]},
    )
