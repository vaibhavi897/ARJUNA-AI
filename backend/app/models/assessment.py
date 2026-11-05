"""Career preferences, role assessments, gap analysis and improvement roadmaps."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
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
    from app.models.catalog import JobRole, Skill
    from app.models.user import User

SCORE_COMPONENTS = (
    "skills",
    "projects",
    "academics",
    "experience",
    "certifications",
    "domain_knowledge",
    "resume_quality",
)
GAP_STATUSES = ("missing", "claimed_only", "below_expected", "met")
TASK_PRIORITIES = ("high", "medium", "low")
TASK_STATUSES = ("pending", "in_progress", "completed")


class StudentCareerPreference(Base, TimestampMixin):
    """A role the student wants to target (step 7). Many per student."""

    __tablename__ = "student_career_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_student_career_pref_user_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    user: Mapped[User] = relationship(back_populates="career_preferences")
    role: Mapped[JobRole] = relationship(back_populates="preferences")


class RoleAssessment(Base, TimestampMixin):
    """A readiness score for one student against one role, at one point in time.

    Historical rows are retained; the newest row per (user, role) carries
    ``is_current = true`` so progress over time is queryable.
    """

    __tablename__ = "role_assessments"
    __table_args__ = (
        Index("ix_role_assessments_user_role_current", "user_id", "role_id", "is_current"),
        Index("ix_role_assessments_user_computed", "user_id", "computed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )

    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    readiness_band: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_delta: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Explainability payloads produced by the deterministic engine.
    strengths: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    improvements: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    insights: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    match_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # True only when an external LLM actually enriched this assessment.
    ai_enriched: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    computed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="assessments")
    role: Mapped[JobRole] = relationship(back_populates="assessments")
    breakdowns: Mapped[list[AssessmentScoreBreakdown]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    skill_gaps: Mapped[list[SkillGapAnalysis]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RoleAssessment user={self.user_id} role={self.role_id} score={self.overall_score}>"


class AssessmentScoreBreakdown(Base, TimestampMixin):
    """Per-component contribution to a role score. This is what makes a score explainable."""

    __tablename__ = "assessment_score_breakdowns"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "component", name="uq_assessment_breakdown_component"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("role_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    component: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    raw_ratio: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1
    points_earned: Mapped[float] = mapped_column(Float, nullable=False)
    points_possible: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    assessment: Mapped[RoleAssessment] = relationship(back_populates="breakdowns")


class SkillGapAnalysis(Base, TimestampMixin):
    """Per-skill comparison of the student against a role's requirements."""

    __tablename__ = "skill_gap_analysis"
    __table_args__ = (
        Index("ix_skill_gap_user_role", "user_id", "role_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("role_assessments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    skill_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_proficiency: Mapped[str] = mapped_column(String(20), nullable=False)
    student_proficiency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_evidence_backed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    points_lost: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("0"))
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped[RoleAssessment | None] = relationship(back_populates="skill_gaps")
    skill: Mapped[Skill] = relationship()


class ImprovementRoadmap(Base, TimestampMixin):
    """A generated improvement plan, optionally scoped to one role."""

    __tablename__ = "improvement_roadmaps"
    __table_args__ = (
        Index("ix_improvement_roadmaps_user_role", "user_id", "role_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    generator: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'rule_based'")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    generated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="roadmaps")
    role: Mapped[JobRole | None] = relationship()
    tasks: Mapped[list[RoadmapTask]] = relationship(
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapTask.display_order",
    )


class RoadmapTask(Base, TimestampMixin):
    """One actionable recommendation the student can complete."""

    __tablename__ = "roadmap_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    related_skill_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'medium'"), index=True
    )
    suggested_duration: Mapped[str | None] = mapped_column(String(60), nullable=True)
    expected_improvement_area: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expected_score_gain: Mapped[float | None] = mapped_column(Float, nullable=True)
    action_type: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'learn_skill'")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"), index=True
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    roadmap: Mapped[ImprovementRoadmap] = relationship(back_populates="tasks")
    related_skill: Mapped[Skill | None] = relationship()
