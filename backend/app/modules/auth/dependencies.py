"""Auth dependencies. Every protected route resolves the caller from the JWT."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated. Please sign in again.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the authenticated student, or raise 401."""
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    claims = decode_access_token(credentials.credentials)
    if not claims:
        raise CREDENTIALS_ERROR

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise CREDENTIALS_ERROR from None

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_onboarded(user: CurrentUser) -> User:
    """Guard for routes that only make sense once onboarding is finished."""
    if not user.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete onboarding to access this resource.",
        )
    return user


OnboardedUser = Annotated[User, Depends(require_onboarded)]
