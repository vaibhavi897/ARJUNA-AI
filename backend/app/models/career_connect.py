"""Per-student Career Connect opportunities, contacts, and tracking."""
from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class CareerConnectJob(Base, TimestampMixin):
    __tablename__ = "career_connect_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "external_key", name="uq_career_connect_jobs_user_external"),
        Index("ix_career_connect_jobs_user_saved", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    external_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    experience: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))


class CareerConnectContact(Base, TimestampMixin):
    __tablename__ = "career_connect_contacts"
    __table_args__ = (
        UniqueConstraint("user_id", "profile_url", name="uq_career_connect_contacts_user_url"),
        Index("ix_career_connect_contacts_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_url: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'manual'"))


class CareerConnectTrackerItem(Base, TimestampMixin):
    __tablename__ = "career_connect_tracker_items"
    __table_args__ = (
        Index("ix_career_connect_tracker_user_status", "user_id", "status"),
        Index("ix_career_connect_tracker_user_reminder", "user_id", "reminder_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("career_connect_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("career_connect_contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'saved'"))
    reminder_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[CareerConnectJob | None] = relationship()
    contact: Mapped[CareerConnectContact | None] = relationship()
