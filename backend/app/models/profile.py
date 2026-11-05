"""Student profile entities: academics, skills, projects, experience, resumes."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.catalog import Skill
    from app.models.user import User

EXPERIENCE_TYPES = (
    "internship",
    "job",
    "position_of_responsibility",
    "extracurricular",
)
ACHIEVEMENT_CATEGORIES = ("competition", "academic", "extracurricular", "other")
SKILL_SOURCES = ("manual", "resume", "both")
ACADEMIC_LEVELS = ("class_10", "class_12", "diploma", "undergraduate", "postgraduate", "other")


class StudentProfile(Base, TimestampMixin):
    """One-to-one extension of :class:`User` holding onboarding step 1 + 7 data."""

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # --- personal ---
    phone: Mapped[str | None] = mapped_column(String(25), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- current academics ---
    college: Mapped[str | None] = mapped_column(String(180), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(120), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(120), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_academic_year: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cgpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    cgpa_scale: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("10.0")
    )

    # --- portfolio links (step 7) ---
    github_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    other_links: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    # --- derived completeness, recomputed on every profile write ---
    profile_completion: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    completion_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    user: Mapped[User] = relationship(back_populates="profile")


class AcademicDetail(Base, TimestampMixin):
    """Education history rows plus academic achievements / coursework (step 2)."""

    __tablename__ = "academic_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    level: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'other'")
    )
    institution: Mapped[str] = mapped_column(String(180), nullable=False)
    board_or_university: Mapped[str | None] = mapped_column(String(180), nullable=True)
    degree_or_program: Mapped[str | None] = mapped_column(String(160), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(160), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # cgpa|percentage
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    achievements: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevant_coursework: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    user: Mapped[User] = relationship(back_populates="academic_details")


class StudentSkill(Base, TimestampMixin):
    """A skill claim by a student, with its evidence trail.

    ``evidence_count`` is how many projects/experiences reference this skill.
    The scoring engine treats a claimed-only skill differently from an
    evidence-backed one, so the two are stored separately and never merged.
    """

    __tablename__ = "student_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_student_skills_user_skill"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    proficiency: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'beginner'")
    )
    years_of_experience: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'manual'")
    )
    # Evidence is recomputed from projects/experience, never user-supplied.
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_evidence_backed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="student_skills")
    skill: Mapped[Skill] = relationship(back_populates="student_skills")


class Project(Base, TimestampMixin):
    """Step 4 project entry."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    is_ongoing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    team_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    live_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'manual'")
    )

    user: Mapped[User] = relationship(back_populates="projects")
    technologies: Mapped[list[ProjectTechnology]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectTechnology(Base, TimestampMixin):
    """Tech/skill used in a project. ``skill_id`` is null for unmatched free text."""

    __tablename__ = "project_technologies"
    __table_args__ = (
        UniqueConstraint("project_id", "raw_name", name="uq_project_tech_project_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_name: Mapped[str] = mapped_column(String(120), nullable=False)

    project: Mapped[Project] = relationship(back_populates="technologies")
    skill: Mapped[Skill | None] = relationship()


class Experience(Base, TimestampMixin):
    """Internships, jobs, positions of responsibility, extracurriculars (step 5)."""

    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    experience_type: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'internship'"), index=True
    )
    organization: Mapped[str] = mapped_column(String(180), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skills_used: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'manual'")
    )

    user: Mapped[User] = relationship(back_populates="experiences")


class Certification(Base, TimestampMixin):
    """Certifications and supporting credentials (step 5 / step 7)."""

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    issue_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    credential_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    credential_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    related_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'manual'")
    )

    user: Mapped[User] = relationship(back_populates="certifications")


class Achievement(Base, TimestampMixin):
    """Competitions, academic honours and other achievements (step 5)."""

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'other'"), index=True
    )
    scope: Mapped[str | None] = mapped_column(String(60), nullable=True)  # college|national|...
    date_awarded: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'manual'")
    )

    user: Mapped[User] = relationship(back_populates="achievements")


class Resume(Base, TimestampMixin):
    """An uploaded resume plus its extracted text and parsed structure (step 6).

    Parsed output is kept separate from the student's manual entries. It is
    surfaced for review and only merged in on explicit confirmation.
    """

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    original_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(260), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)

    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    quality_report: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    parse_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    reviewed_by_student: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    uploaded_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="resumes")
