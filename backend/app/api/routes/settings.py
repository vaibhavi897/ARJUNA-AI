"""Student settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.models import StudentSettings
from app.modules.activity import log_activity
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.schemas.common import ActionResult
from app.schemas.settings import AccountUpdateIn, StudentSettingsIn, StudentSettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create(db: DbSession, user_id: int) -> StudentSettings:
    row = db.scalar(select(StudentSettings).where(StudentSettings.user_id == user_id))
    if row is None:
        row = StudentSettings(user_id=user_id)
        db.add(row)
        db.flush()
    return row


@router.get("", response_model=StudentSettingsOut)
def get_settings(user: CurrentUser, db: DbSession) -> StudentSettingsOut:
    row = _get_or_create(db, user.id)
    db.commit()
    return StudentSettingsOut.model_validate(row)


@router.put("", response_model=StudentSettingsOut)
def update_settings(
    payload: StudentSettingsIn, user: CurrentUser, db: DbSession
) -> StudentSettingsOut:
    row = _get_or_create(db, user.id)
    changed: list[str] = []
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None and getattr(row, field) != value:
            setattr(row, field, value)
            changed.append(field)
    if changed:
        log_activity(
            db,
            user.id,
            "settings_updated",
            "Settings updated",
            ", ".join(changed),
            details={"fields": changed},
        )
    db.commit()
    return StudentSettingsOut.model_validate(row)


@router.put("/account", response_model=ActionResult)
def update_account(
    payload: AccountUpdateIn, user: CurrentUser, db: DbSession
) -> ActionResult:
    """Account-level fields. Email changes go through the profile endpoint."""
    if payload.full_name and payload.full_name != user.full_name:
        user.full_name = payload.full_name
        log_activity(db, user.id, "profile_updated", "Display name updated", None)
    db.commit()
    return ActionResult(message="Account updated.", data={"full_name": user.full_name})
