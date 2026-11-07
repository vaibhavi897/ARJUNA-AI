"""Add the shared translation cache."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "9d3b1f2a6c41"
down_revision: str | None = "7a6c92e14b3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "translation_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lang", sa.String(length=12), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("lang", "text_hash", name="uq_translation_lang_hash"),
    )


def downgrade() -> None:
    op.drop_table("translation_cache")
