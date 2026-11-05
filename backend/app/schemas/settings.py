"""Student settings schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

VISIBILITIES = ("private", "college_only", "public")
THEMES = ("light", "dark", "system")


class StudentSettingsOut(ORMModel):
    email_notifications: bool
    weekly_progress_digest: bool
    roadmap_reminders: bool
    profile_visibility: str
    theme: str
    auto_recalculate_scores: bool


class StudentSettingsIn(BaseModel):
    email_notifications: bool | None = None
    weekly_progress_digest: bool | None = None
    roadmap_reminders: bool | None = None
    profile_visibility: str | None = None
    theme: str | None = None
    auto_recalculate_scores: bool | None = None

    @field_validator("profile_visibility")
    @classmethod
    def _valid_visibility(cls, value: str | None) -> str | None:
        if value is not None and value not in VISIBILITIES:
            raise ValueError(f"profile_visibility must be one of {', '.join(VISIBILITIES)}")
        return value

    @field_validator("theme")
    @classmethod
    def _valid_theme(cls, value: str | None) -> str | None:
        if value is not None and value not in THEMES:
            raise ValueError(f"theme must be one of {', '.join(THEMES)}")
        return value


class AccountUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def _clean(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Full name is too short")
        return cleaned
