"""Add account-scoped Career Connect saved items."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "7a6c92e14b3f"
down_revision: str | None = "4e2901261b05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_connect_saved_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.String(length=24), nullable=False),
        sa.Column("item_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "item_type", "item_id", name="uq_career_connect_saved_user_item"),
    )
    op.create_index("ix_career_connect_saved_items_user_id", "career_connect_saved_items", ["user_id"])
    op.create_index("ix_career_connect_saved_user_type", "career_connect_saved_items", ["user_id", "item_type"])


def downgrade() -> None:
    op.drop_index("ix_career_connect_saved_user_type", table_name="career_connect_saved_items")
    op.drop_index("ix_career_connect_saved_items_user_id", table_name="career_connect_saved_items")
    op.drop_table("career_connect_saved_items")
