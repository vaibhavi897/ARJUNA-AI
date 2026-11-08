"""Persisted Arjuna Interview Arena sessions."""
from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
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

    # Set once, when the score email for this session has been handed to the
    # mailer. It is claimed with a conditional UPDATE so two concurrent "end
    # interview" calls can never both send, and it is never cleared: one
    # completed interview means at most one email.
    score_email_sent_at: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # --- Optional recording. Captured only with consent, held in Supabase
    # Storage (private bucket) and auto-deleted once it expires. ---
    recording_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    recording_mime: Mapped[str | None] = mapped_column(String(60), nullable=True)
    recording_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    recording_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recording_expires_at: Mapped[str | None] = mapped_column(String(40), nullable=True)

    user = relationship("User")
