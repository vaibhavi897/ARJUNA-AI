"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.modules.auth import service
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.profile.service import compute_profile_completion
from app.schemas.auth import (
    AvailabilityResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.common import Message

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    """Create a student account and sign the student straight into onboarding."""
    user = service.register_student(db, payload)
    compute_profile_completion(db, user)
    db.commit()
    token, expires_at = service.issue_token(user)
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        user=UserOut.model_validate(user),
        next_route=service.next_route_for(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    """Sign in with email or username."""
    user = service.authenticate(db, payload)
    token, expires_at = service.issue_token(user)
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        user=UserOut.model_validate(user),
        next_route=service.next_route_for(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/availability", response_model=AvailabilityResponse)
def availability(
    db: DbSession,
    field: str = Query(pattern="^(email|username)$"),
    value: str = Query(min_length=3, max_length=255),
) -> AvailabilityResponse:
    """Live check used by the registration form."""
    available = service.check_availability(db, field, value)
    return AvailabilityResponse(field=field, value=value.strip().lower(), available=available)


@router.post("/change-password", response_model=Message)
def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> Message:
    service.change_password(db, user, payload)
    return Message(
        message="Password updated.",
        detail="Use your new password the next time you sign in.",
    )


@router.post("/logout", response_model=Message)
def logout(user: CurrentUser, db: DbSession) -> Message:
    """Record the sign-out. Tokens are stateless, so the client discards it."""
    from app.modules.activity import log_activity

    log_activity(db, user.id, "logout", "Signed out", None)
    db.commit()
    return Message(
        message="Signed out.",
        detail="Access token discarded on the client. It also expires on its own.",
    )
