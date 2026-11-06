"""CareerVerse: career exploration data (reference) and per-student state.

Reference tables (``careers`` and children) are seeded from
``app/data/careers_seed.json`` and enriched by O*NET / BLS syncs. Student
state tables hang off the existing ``users`` table; nothing from the resume or
profile tables is duplicated here.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import (
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

SKILL_KINDS = ("technical", "soft", "knowledge", "tool")
QUALIFICATION_KINDS = ("degree", "certification")
SALARY_REGIONS = ("india", "us", "global")
SOURCE_KINDS = ("seed", "onet", "bls", "ncs", "adzuna", "curated")


def _jsonb_default(literal: str) -> Any:
    return text(f"'{literal}'::jsonb")


class Career(Base, TimestampMixin):
    __tablename__ = "careers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    industry: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    short_description: Mapped[str] = mapped_column(String(400), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    industries: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    work_environment: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_life_balance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("{}")
    )
    outlook: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("{}")
    )
    advantages: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    disadvantages: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    geography: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    visual_theme: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'office'")
    )
    # Occupation mappings. Modern titles often have no exact O*NET match, so
    # these are maintained by hand and may be null.
    onet_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    soc_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    onet_synced_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    onet_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("{}")
    )
    last_updated: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    salaries: Mapped[list[CareerSalary]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    companies: Mapped[list[CareerCompany]] = relationship(
        back_populates="career", cascade="all, delete-orphan", order_by="CareerCompany.position"
    )
    skills: Mapped[list[CareerSkill]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    qualifications: Mapped[list[CareerQualification]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    trajectory: Mapped[list[CareerTrajectory]] = relationship(
        back_populates="career", cascade="all, delete-orphan", order_by="CareerTrajectory.stage"
    )
    exits: Mapped[list[CareerExit]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    sources: Mapped[list[CareerSource]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    stories: Mapped[list[CareerStory]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )


class CareerSource(Base, TimestampMixin):
    """Where a piece of career data came from, with a verification date."""

    __tablename__ = "career_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    covers: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_verified: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    career: Mapped[Career] = relationship(back_populates="sources")


class CareerSalary(Base, TimestampMixin):
    """One sourced salary datapoint. Never populated without a source."""

    __tablename__ = "career_salaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    region: Mapped[str] = mapped_column(String(20), nullable=False)  # india | us | global
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(60), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    salary_type: Mapped[str] = mapped_column(String(40), nullable=False)  # median_annual, base, total_comp
    level: Mapped[str] = mapped_column(String(30), nullable=False)  # entry | mid | senior | median | top
    experience_min_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_max_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    range_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    range_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'year'"))
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_verified: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    career: Mapped[Career] = relationship(back_populates="salaries")


class CareerCompany(Base, TimestampMixin):
    __tablename__ = "career_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    job_titles: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    regions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    source_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'curated'")
    )

    career: Mapped[Career] = relationship(back_populates="companies")


class CareerSkill(Base, TimestampMixin):
    __tablename__ = "career_skills"
    __table_args__ = (UniqueConstraint("career_id", "name", "kind", name="uq_career_skills_career_name_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # technical|soft|knowledge|tool
    importance: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'core'")
    )
    source_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'seed'")
    )

    career: Mapped[Career] = relationship(back_populates="skills")


class CareerQualification(Base, TimestampMixin):
    __tablename__ = "career_qualifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # degree | certification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    career: Mapped[Career] = relationship(back_populates="qualifications")


class CareerTrajectory(Base, TimestampMixin):
    __tablename__ = "career_trajectories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 entry .. 4 leadership
    level_name: Mapped[str] = mapped_column(String(30), nullable=False)
    designation: Mapped[str] = mapped_column(String(160), nullable=False)
    experience_min_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_max_years: Mapped[float | None] = mapped_column(Float, nullable=True)

    career: Mapped[Career] = relationship(back_populates="trajectory")


class CareerExit(Base, TimestampMixin):
    __tablename__ = "career_exits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # role | industry | qualification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    career: Mapped[Career] = relationship(back_populates="exits")


class CareerStory(Base, TimestampMixin):
    """A stored day-in-the-life story. Generated once; never on page load."""

    __tablename__ = "career_stories"
    __table_args__ = (UniqueConstraint("career_id", "version", name="uq_career_stories_career_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'seed'"))
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    scene_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    career: Mapped[Career] = relationship(back_populates="stories")
    scenes: Mapped[list[CareerStoryScene]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        order_by="CareerStoryScene.scene_number",
    )


class CareerStoryScene(Base, TimestampMixin):
    __tablename__ = "career_story_scenes"
    __table_args__ = (UniqueConstraint("story_id", "scene_number", name="uq_career_story_scenes_story_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    story_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("career_stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    time_of_day: Mapped[str] = mapped_column(String(40), nullable=False)
    heading: Mapped[str] = mapped_column(String(200), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    activities: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    tools: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    responsibilities: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    industry_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_key: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'desk'")
    )

    story: Mapped[CareerStory] = relationship(back_populates="scenes")


# ---------------------------------------------------------------------------
# Per-student state. Linked to the existing users table only.
# ---------------------------------------------------------------------------


class UserCareerView(Base):
    __tablename__ = "user_career_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    view_type: Mapped[str] = mapped_column(String(20), nullable=False)  # story | insights
    viewed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    career: Mapped[Career] = relationship()


class UserCareerProgress(Base, TimestampMixin):
    __tablename__ = "user_career_progress"
    __table_args__ = (UniqueConstraint("user_id", "career_id", name="uq_user_career_progress_user_career"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    story_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("career_stories.id", ondelete="SET NULL"), nullable=True
    )
    last_scene_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    furthest_scene_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    story_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    insights_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_saved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), index=True)

    career: Mapped[Career] = relationship()


class UserCareerFit(Base, TimestampMixin):
    """Latest Career Fit result per student and career (cached by input hash)."""

    __tablename__ = "user_career_fit"
    __table_args__ = (UniqueConstraint("user_id", "career_id", name="uq_user_career_fit_user_career"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    components: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("{}")
    )
    weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("{}")
    )
    strengths: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    gaps: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    recommendations: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("[]")
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'rule_based'")
    )
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    career: Mapped[Career] = relationship()


class CareerAiOutput(Base, TimestampMixin):
    """Cache for Gemini outputs so identical requests never hit the API twice."""

    __tablename__ = "career_ai_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=_jsonb_default("{}")
    )
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
