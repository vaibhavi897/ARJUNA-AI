"""Authentication request/response schemas with server-side validation."""

from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.common import ORMModel

USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,50}$")
MIN_PASSWORD_LENGTH = 8


def _validate_password_strength(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    if len(value) > 128:
        raise ValueError("Password must be at most 128 characters long")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number")
    return value


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Full name is required")
        return cleaned

    @field_validator("username")
    @classmethod
    def _clean_username(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not USERNAME_RE.match(cleaned):
            raise ValueError(
                "Username may contain only letters, numbers, dots, underscores and hyphens"
            )
        return cleaned

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> RegisterRequest:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    # Accepts either the email address or the username.
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def _clean(cls, value: str) -> str:
        return value.strip().lower()


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def _strong(cls, value: str) -> str:
        return _validate_password_strength(value)

    @model_validator(mode="after")
    def _match(self) -> ChangePasswordRequest:
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")
        if self.new_password == self.current_password:
            raise ValueError("New password must be different from the current password")
        return self


class UserOut(ORMModel):
    id: int
    full_name: str
    email: EmailStr
    username: str
    role: str
    is_active: bool
    is_demo: bool
    onboarding_step: int
    onboarding_completed: bool
    last_login_at: dt.datetime | None = None
    created_at: dt.datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: dt.datetime
    user: UserOut
    # Where the frontend should send the student next.
    next_route: str


class AvailabilityResponse(BaseModel):
    field: str
    value: str
    available: bool
