"""Persisted Arjuna Interview Arena sessions."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class InterviewSession(Base, TimestampMixin):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    personas: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    focus: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, default=dict)
    seniority: Mapped[str] = mapped_column(String(30), nullable=False, default="Mid-Level")
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    consent_media: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[str] = mapped_column(String(40), nullable=False)
    ended_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    transcript: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    integrity_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    user = relationship("User")
