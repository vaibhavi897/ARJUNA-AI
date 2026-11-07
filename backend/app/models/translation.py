"""Shared cache of translated strings, so the same text is never paid for twice."""
from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class TranslationCache(Base, TimestampMixin):
    __tablename__ = "translation_cache"
    __table_args__ = (UniqueConstraint("lang", "text_hash", name="uq_translation_lang_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lang: Mapped[str] = mapped_column(String(12), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
