"""Resume upload, review and import endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import settings
from app.models import Resume
from app.modules.activity import log_activity
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.onboarding import sync_onboarding_state
from app.modules.profile.service import compute_profile_completion
from app.modules.resume import service as resume_service
from app.modules.scoring.service import refresh_scores
from app.schemas.common import ActionResult

router = APIRouter(prefix="/resume", tags=["resume"])


class ImportSelection(BaseModel):
    """What the student approved for import after reviewing the parse."""

    import_contact: bool = True
    skills: list[str] = Field(default_factory=list, max_length=80)
    projects: list[str] = Field(default_factory=list, max_length=30)
    experience: list[str] = Field(default_factory=list, max_length=30)
    certifications: list[str] = Field(default_factory=list, max_length=30)
    achievements: list[str] = Field(default_factory=list, max_length=30)


def _active_resume(db: DbSession, user_id: int) -> Resume | None:
    return db.scalar(
        select(Resume)
        .where(Resume.user_id == user_id, Resume.is_active.is_(True))
        .order_by(Resume.uploaded_at.desc())
    )


@router.get("/limits")
def limits() -> dict[str, Any]:
    return {
        "allowed_extensions": [".pdf", ".docx"],
        "max_size_mb": settings.MAX_UPLOAD_SIZE_MB,
    }


@router.post("/upload")
async def upload(
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(description="PDF or DOCX resume")],
) -> dict[str, Any]:
    """Store the resume, extract its text and return the parse for review.

    Nothing is written into the student's profile here.
    """
    resume = await resume_service.store_upload(db, user, file)
    compute_profile_completion(db, user)
    sync_onboarding_state(db, user)
    log_activity(
        db,
        user.id,
        "resume_uploaded",
        f"Resume uploaded: {resume.original_filename}",
        (
            f"Parse status: {resume.parse_status}."
            + (f" Quality score {resume.quality_score}/100." if resume.quality_score else "")
        ),
        details={"resume_id": resume.id, "parse_status": resume.parse_status},
    )

    recalculated: list[str] = []
    if user.onboarding_completed:
        recalculated = refresh_scores(db, user, change="resume")["recalculated_roles"]

    review = resume_service.build_review_payload(db, user, resume)
    db.commit()
    return {
        "message": (
            "Resume uploaded and analysed."
            if resume.parse_status == "parsed"
            else "Resume uploaded, but the text could not be read."
        ),
        "recalculated_roles": recalculated,
        "review": review,
    }


@router.get("/review")
def review(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    """The current resume's parse, annotated against the existing profile."""
    resume = _active_resume(db, user.id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No resume uploaded yet."
        )
    payload = resume_service.build_review_payload(db, user, resume)
    db.commit()
    return payload


@router.post("/import", response_model=ActionResult)
def import_selected(
    payload: ImportSelection, user: CurrentUser, db: DbSession
) -> ActionResult:
    """Import only what the student ticked. Existing entries are never replaced."""
    resume = _active_resume(db, user.id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No resume uploaded yet."
        )
    if resume.parse_status != "parsed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This resume could not be parsed, so there is nothing to import.",
        )

    added = resume_service.apply_resume_data(db, user, resume, payload.model_dump())
    compute_profile_completion(db, user)
    sync_onboarding_state(db, user)
    log_activity(
        db,
        user.id,
        "resume_reviewed",
        "Resume data reviewed and imported",
        ", ".join(f"{key}: {value}" for key, value in added.items() if value) or "Nothing imported.",
        details=added,
    )

    recalculated: list[str] = []
    if user.onboarding_completed:
        recalculated = refresh_scores(db, user, change="resume")["recalculated_roles"]

    db.commit()
    return ActionResult(
        message="Imported the selected items.",
        recalculated_roles=recalculated,
        data=added,
    )


@router.post("/skip", response_model=ActionResult)
def skip(user: CurrentUser, db: DbSession) -> ActionResult:
    """Mark the resume step as reviewed without importing anything."""
    resume = _active_resume(db, user.id)
    if resume is not None:
        resume.reviewed_by_student = True
    db.commit()
    return ActionResult(message="Resume step skipped. You can upload one later from Settings.")
