"""Reference data: skills, career domains, job roles and role requirements.

These tables are data-driven on purpose: adding a career role or changing its
rubric is a seed/row change, never a code change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    from app.models.assessment import RoleAssessment, StudentCareerPreference
    from app.models.profile import StudentSkill

SKILL_CATEGORIES = (
    "programming",
    "data_ai",
    "cloud_devops",
    "cs_fundamentals",
    "finance",
    "business",
    "tools",
    "soft_skills",
    "other",
)

PROFICIENCY_LEVELS = ("beginner", "intermediate", "advanced")
PROFICIENCY_RANK = {"beginner": 1, "intermediate": 2, "advanced": 3}
IMPORTANCE_LEVELS = ("required", "preferred")


class Skill(Base, TimestampMixin):
    """Canonical skill catalogue. Students may also create custom skills."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'other'"), index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Custom skills typed by a student are flagged so the catalogue stays clean.
    is_custom: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    aliases: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    student_skills: Mapped[list[StudentSkill]] = relationship(back_populates="skill")
    role_requirements: Mapped[list[RoleRequiredSkill]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Skill {self.name!r}>"


class CareerDomain(Base, TimestampMixin):
    """A broad career family, e.g. Software Engineering or Investment Banking."""

    __tablename__ = "career_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    roles: Mapped[list[JobRole]] = relationship(
        back_populates="domain", cascade="all, delete-orphan"
    )


class JobRole(Base, TimestampMixin):
    """A target role plus its own scoring rubric.

    Weights are stored per role so no single universal formula is used.
    They are expressed in points and are expected to total 100.
    """

    __tablename__ = "job_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("career_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    short_label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    # --- rubric weights (points out of 100) ---
    weight_skills: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("30")
    )
    weight_projects: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("20")
    )
    weight_academics: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("15")
    )
    weight_experience: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("15")
    )
    weight_certifications: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("8")
    )
    weight_domain_knowledge: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("7")
    )
    weight_resume_quality: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("5")
    )

    # --- rubric expectations ---
    min_cgpa: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("6.0"))
    target_cgpa: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("8.0")
    )
    expected_projects: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("2")
    )
    expected_internships: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    expected_certifications: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    # Keywords drive the resume-quality and domain-knowledge signals.
    resume_keywords: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    relevant_project_categories: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    domain: Mapped[CareerDomain] = relationship(back_populates="roles")
    required_skills: Mapped[list[RoleRequiredSkill]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    assessments: Mapped[list[RoleAssessment]] = relationship(back_populates="role")
    preferences: Mapped[list[StudentCareerPreference]] = relationship(
        back_populates="role"
    )

    @property
    def total_weight(self) -> float:
        return (
            self.weight_skills
            + self.weight_projects
            + self.weight_academics
            + self.weight_experience
            + self.weight_certifications
            + self.weight_domain_knowledge
            + self.weight_resume_quality
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<JobRole {self.name!r}>"


class RoleRequiredSkill(Base, TimestampMixin):
    """Which skills a role needs, how important, and at what proficiency."""

    __tablename__ = "role_required_skills"
    __table_args__ = (
        UniqueConstraint(
            "role_id", "skill_id", name="uq_role_required_skills_role_skill"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    importance: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'required'")
    )
    expected_proficiency: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'intermediate'")
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("1.0"))

    role: Mapped[JobRole] = relationship(back_populates="required_skills")
    skill: Mapped[Skill] = relationship(back_populates="role_requirements")
