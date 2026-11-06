"""AI Learning Hub data model.

Seeded reference data is limited to track metadata, topic taxonomy and topic
prerequisites. Everything a student actually sees (plans, notes, quizzes,
roadmaps) is generated on demand and stored per user. Every user-owned table
links to the existing ``users`` table.
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

TASK_CATEGORIES = ("learn", "practice", "project", "revision", "assessment", "milestone", "rest")
TASK_STATUSES = ("pending", "completed", "partial", "skipped", "rescheduled")
MASTERY_STATUSES = ("not_started", "learning", "developing", "needs_revision", "strong", "mastered")


def _j(default: str) -> Any:
    return text(f"'{default}'::jsonb")


# ---------------------------------------------------------------- reference (seeded)
class LearningTrack(Base, TimestampMixin):
    """A career track: a structured starting framework Gemini builds journeys from."""

    __tablename__ = "learning_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    phases: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    career_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)

    topics: Mapped[list[LearningTopic]] = relationship(back_populates="track", cascade="all, delete-orphan", order_by="LearningTopic.position")


class LearningTopic(Base, TimestampMixin):
    """Taxonomy node with prerequisites (slugs). No educational content is stored."""

    __tablename__ = "learning_topics"
    __table_args__ = (UniqueConstraint("track_id", "slug", name="uq_learning_topics_track_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    phase: Mapped[str] = mapped_column(String(30), nullable=False)  # foundation | intermediate | advanced
    est_hours: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("3"))
    prerequisites: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    track: Mapped[LearningTrack] = relationship(back_populates="topics")


class LearningResource(Base, TimestampMixin):
    """Optional, manually VERIFIED resource catalogue. Empty unless curated; never AI-written."""

    __tablename__ = "learning_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    verified_on: Mapped[dt.date | None] = mapped_column(Date, nullable=True)


# ---------------------------------------------------------------- goals, plans, tasks
class LearningGoal(Base, TimestampMixin):
    __tablename__ = "learning_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("learning_tracks.id", ondelete="SET NULL"), nullable=True)
    target_role: Mapped[str] = mapped_column(String(160), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_hours: Mapped[float] = mapped_column(Float, nullable=False)
    study_days: Mapped[list[int]] = mapped_column(JSONB, nullable=False, server_default=_j("[0,1,2,3,4,5,6]"))  # 0=Mon
    start_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    existing_knowledge: Mapped[str | None] = mapped_column(Text, nullable=True)
    skip_topics: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    focus_areas: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    target_companies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    breaks: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))  # [{start,end,reason}]
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))

    track: Mapped[LearningTrack | None] = relationship()
    plans: Mapped[list[LearningPlan]] = relationship(back_populates="goal", cascade="all, delete-orphan")


class LearningPlan(Base, TimestampMixin):
    __tablename__ = "learning_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"), index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    starting_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    skill_gap: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    phases: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    start_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)

    goal: Mapped[LearningGoal] = relationship(back_populates="plans")
    tasks: Mapped[list[LearningTask]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    milestones: Mapped[list[LearningMilestone]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="LearningMilestone.due_date")


class LearningMilestone(Base, TimestampMixin):
    __tablename__ = "learning_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    week_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    due_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    plan: Mapped[LearningPlan] = relationship(back_populates="milestones")


class LearningTask(Base, TimestampMixin):
    """One calendar activity. ``date`` moves on reschedule; ``original_date`` never does."""

    __tablename__ = "learning_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    original_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    topic_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subtopics: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    objectives: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    assignment: Mapped[str | None] = mapped_column(Text, nullable=True)
    resources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    est_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("60"))
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"), index=True)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    self_difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 easy .. 5 hard
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reschedule_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locked_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))  # pinned dates survive regeneration

    plan: Mapped[LearningPlan] = relationship(back_populates="tasks")


# ---------------------------------------------------------------- generated content
class GeneratedMaterial(Base, TimestampMixin):
    __tablename__ = "generated_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    depth: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'standard'"))
    kind: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'notes'"))  # notes | diagram | examples | implementation
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("generated_materials.id", ondelete="SET NULL"), nullable=True)
    task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("learning_tasks.id", ondelete="SET NULL"), nullable=True)
    followups: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)


class YoutubeImport(Base, TimestampMixin):
    __tablename__ = "youtube_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(300), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(200), nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(300), nullable=True)
    transcript_status: Mapped[str] = mapped_column(String(20), nullable=False)  # available | unavailable | pasted
    transcript: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)


# ---------------------------------------------------------------- notebooks
class Notebook(Base, TimestampMixin):
    __tablename__ = "notebooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cover_style: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'forest'"))
    folder: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    # Real privacy: server refuses page access without a short-lived unlock token
    # that is only issued after verifying this Argon2 hash.
    lock_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("learning_plans.id", ondelete="SET NULL"), nullable=True)

    chapters: Mapped[list[NotebookChapter]] = relationship(back_populates="notebook", cascade="all, delete-orphan", order_by="NotebookChapter.position")
    pages: Mapped[list[NotebookPage]] = relationship(back_populates="notebook", cascade="all, delete-orphan", order_by="NotebookPage.page_no")


class NotebookChapter(Base, TimestampMixin):
    __tablename__ = "notebook_chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notebook_id: Mapped[int] = mapped_column(Integer, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    notebook: Mapped[Notebook] = relationship(back_populates="chapters")


class NotebookPage(Base, TimestampMixin):
    __tablename__ = "notebook_pages"
    __table_args__ = (UniqueConstraint("notebook_id", "page_no", name="uq_notebook_pages_notebook_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notebook_id: Mapped[int] = mapped_column(Integer, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("notebook_chapters.id", ondelete="SET NULL"), nullable=True)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, server_default=text("'Untitled page'"))
    content: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    bookmarked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'manual'"))  # manual|gemini|youtube|upload
    source_ref: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("learning_tasks.id", ondelete="SET NULL"), nullable=True)

    notebook: Mapped[Notebook] = relationship(back_populates="pages")
    versions: Mapped[list[NotebookPageVersion]] = relationship(back_populates="page", cascade="all, delete-orphan", order_by="NotebookPageVersion.id.desc()")


class NotebookPageVersion(Base):
    __tablename__ = "notebook_page_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(Integer, ForeignKey("notebook_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    saved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    page: Mapped[NotebookPage] = relationship(back_populates="versions")


# ---------------------------------------------------------------- quizzes
class QuizSession(Base, TimestampMixin):
    __tablename__ = "quiz_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("learning_plans.id", ondelete="SET NULL"), nullable=True)
    topic: Mapped[str] = mapped_column(String(240), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'topic'"))  # topic|subject|week|roadmap|revision
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'in_progress'"), index=True)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    submitted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    retry_of: Mapped[int | None] = mapped_column(Integer, ForeignKey("quiz_sessions.id", ondelete="SET NULL"), nullable=True)

    questions: Mapped[list[QuizQuestion]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="QuizQuestion.position")


class QuizQuestion(Base, TimestampMixin):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    qtype: Mapped[str] = mapped_column(String(30), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    subtopic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    answer_key: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    test_cases: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=_j("[]"))
    starter_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    points: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("1"))

    session: Mapped[QuizSession] = relationship(back_populates="questions")


class QuizAttempt(Base, TimestampMixin):
    __tablename__ = "quiz_attempts"
    __table_args__ = (UniqueConstraint("question_id", name="uq_quiz_attempts_question"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    score: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("0"))
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    evaluated_by: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'deterministic'"))
    feedback: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))


# ---------------------------------------------------------------- mastery, SRS, events
class TopicProficiency(Base, TimestampMixin):
    __tablename__ = "topic_proficiency"
    __table_args__ = (UniqueConstraint("user_id", "topic_key", name="uq_topic_proficiency_user_topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_key: Mapped[str] = mapped_column(String(200), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    mastery_score: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'not_started'"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    last_assessed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RevisionSchedule(Base, TimestampMixin):
    __tablename__ = "revision_schedules"
    __table_args__ = (UniqueConstraint("user_id", "topic_key", name="uq_revision_schedules_user_topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_key: Mapped[str] = mapped_column(String(200), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    ease: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("2.5"))
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    due_date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    last_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningSettings(Base, TimestampMixin):
    __tablename__ = "learning_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    interval_scale: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("1.0"))  # SRS: <1 more frequent
    preferred_depth: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'standard'"))


class LearningEvent(Base):
    """Append-only log of learning behaviour. The raw material for later personalisation."""

    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"), index=True)


class PersonalizationFeedback(Base):
    """Explicit signals: self-reported difficulty, satisfaction, recommendation outcomes."""

    __tablename__ = "personalization_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)  # difficulty | satisfaction | recommendation
    ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=_j("{}"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
