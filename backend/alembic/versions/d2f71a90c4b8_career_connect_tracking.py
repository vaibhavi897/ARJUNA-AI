"""Persist opportunity application stages."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d2f71a90c4b8"
down_revision: str | Sequence[str] | None = ("7a6c92e14b3f", "9d3b1f2a6c41")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("career_connect_saved_items", sa.Column("status", sa.String(length=24), server_default="interested", nullable=False))


def downgrade() -> None:
    op.drop_column("career_connect_saved_items", "status")
