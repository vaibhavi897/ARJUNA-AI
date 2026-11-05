"""Student activity feed."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

ACTIVITY_TYPES = (
    "account_created",
    "login",
    "logout",
    "onboarding_step_completed",
    "onboarding_completed",
    "profile_updated",
    "academics_updated",
    "skill_added",
    "skill_removed",
    "project_added",
    "project_updated",
    "project_removed",
    "experience_added",
    "experience_removed",
    "certification_added",
    "achievement_added",
    "resume_uploaded",
    "resume_reviewed",
    "preferences_updated",
    "assessment_completed",
    "roadmap_generated",
    "roadmap_task_completed",
    "password_changed",
    "settings_updated",
)


class StudentActivityLog(Base):
    """Append-only feed powering the dashboard's Recent Activity panel."""

    __tablename__ = "student_activity_logs"
    __table_args__ = (
        Index("ix_activity_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="activity_logs")
