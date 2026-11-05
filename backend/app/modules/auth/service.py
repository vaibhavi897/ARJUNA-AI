"""Registration, login and password-change logic."""

from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models import StudentProfile, StudentSettings, User
from app.modules.activity import log_activity
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest

logger = get_logger(__name__)


def _email_taken(db: Session, email: str) -> bool:
    return db.scalar(
        select(func.count()).select_from(User).where(func.lower(User.email) == email.lower())
    ) > 0


def _username_taken(db: Session, username: str) -> bool:
    return db.scalar(
        select(func.count())
        .select_from(User)
        .where(func.lower(User.username) == username.lower())
    ) > 0


def check_availability(db: Session, field: str, value: str) -> bool:
    value = value.strip().lower()
    if field == "email":
        return not _email_taken(db, value)
    if field == "username":
        return not _username_taken(db, value)
    raise HTTPException(status_code=400, detail="field must be 'email' or 'username'")


def register_student(db: Session, payload: RegisterRequest) -> User:
    """Create a student account. Duplicate email/username is rejected."""
    if _email_taken(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Try signing in instead.",
        )
    if _username_taken(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken. Please choose another.",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="student",
        onboarding_step=0,
        onboarding_completed=False,
    )
    db.add(user)

    try:
        db.flush()
    except IntegrityError as exc:  # race between the check and the insert
        db.rollback()
        logger.warning("Registration race detected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email or username was just registered. Please try again.",
        ) from exc

    # Every student starts with an empty profile and default settings so later
    # writes never have to special-case a missing row.
    db.add(StudentProfile(user_id=user.id))
    db.add(StudentSettings(user_id=user.id))
    log_activity(
        db,
        user.id,
        "account_created",
        "Account created",
        "Welcome to Arjuna AI. Your student workspace is ready.",
    )
    db.commit()
    db.refresh(user)
    logger.info("Registered student id=%s username=%s", user.id, user.username)
    return user


def authenticate(db: Session, payload: LoginRequest) -> User:
    """Verify credentials. The same error is returned for unknown user and bad password."""
    identifier = payload.identifier
    user = db.scalar(
        select(User).where(
            (func.lower(User.email) == identifier) | (func.lower(User.username) == identifier)
        )
    )

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials. Please check your email/username and password.",
    )
    if user is None:
        raise invalid
    if not verify_password(payload.password, user.password_hash):
        raise invalid
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    # Transparent upgrade if Argon2 parameters have changed since signup.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    log_activity(db, user.id, "login", "Signed in", None)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your current password is incorrect.",
        )
    user.password_hash = hash_password(payload.new_password)
    log_activity(db, user.id, "password_changed", "Password updated", None)
    db.commit()


def next_route_for(user: User) -> str:
    """Where the frontend should land this student after authenticating."""
    if user.onboarding_completed:
        return "/app/dashboard"
    step = max(1, min(user.onboarding_step + 1, 7))
    return f"/onboarding?step={step}"


def issue_token(user: User) -> tuple[str, dt.datetime]:
    return create_access_token(
        user.id, extra_claims={"username": user.username, "role": user.role}
    )
