"""Per-student saved items for the curated Career Connect directory."""
from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CareerConnectSavedItem(Base, TimestampMixin):
    __tablename__ = "career_connect_saved_items"
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", name="uq_career_connect_saved_user_item"),
        Index("ix_career_connect_saved_user_type", "user_id", "item_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(24), nullable=False)
    item_id: Mapped[str] = mapped_column(String(100), nullable=False)

