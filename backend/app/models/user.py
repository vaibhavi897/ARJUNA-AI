"""Authentication-level entities."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.activity import StudentActivityLog
    from app.models.assessment import (
        ImprovementRoadmap,
        RoleAssessment,
        StudentCareerPreference,
    )
    from app.models.profile import (
        AcademicDetail,
        Achievement,
        Certification,
        Experience,
        Project,
        Resume,
        StudentProfile,
        StudentSkill,
    )

# Onboarding is a 7-step wizard; 0 => nothing submitted yet.
ONBOARDING_TOTAL_STEPS = 7


class User(Base, TimestampMixin):
    """A student account. The only account type in this phase."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'student'")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_demo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    onboarding_step: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    last_login_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- relationships ---
    profile: Mapped[StudentProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    settings: Mapped[StudentSettings | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    academic_details: Mapped[list[AcademicDetail]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    student_skills: Mapped[list[StudentSkill]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    experiences: Mapped[list[Experience]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    certifications: Mapped[list[Certification]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[list[Achievement]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    career_preferences: Mapped[list[StudentCareerPreference]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    assessments: Mapped[list[RoleAssessment]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    roadmaps: Mapped[list[ImprovementRoadmap]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list[StudentActivityLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User id={self.id} username={self.username!r}>"


class StudentSettings(Base, TimestampMixin):
    """Per-student preferences. Created lazily on first read."""

    __tablename__ = "student_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    email_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    weekly_progress_digest: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    roadmap_reminders: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    profile_visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'private'")
    )
    theme: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'light'")
    )
    auto_recalculate_scores: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    user: Mapped[User] = relationship(back_populates="settings")
