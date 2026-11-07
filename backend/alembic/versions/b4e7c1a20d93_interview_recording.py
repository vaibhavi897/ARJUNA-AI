"""Store optional interview recordings held in Supabase Storage."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b4e7c1a20d93"
down_revision: str | Sequence[str] | None = "d2f71a90c4b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("interview_sessions", sa.Column("recording_path", sa.String(length=300), nullable=True))
    op.add_column("interview_sessions", sa.Column("recording_mime", sa.String(length=60), nullable=True))
    op.add_column("interview_sessions", sa.Column("recording_bytes", sa.BigInteger(), nullable=True))
    op.add_column("interview_sessions", sa.Column("recording_seconds", sa.Integer(), nullable=True))
    op.add_column("interview_sessions", sa.Column("recording_expires_at", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("interview_sessions", "recording_expires_at")
    op.drop_column("interview_sessions", "recording_seconds")
    op.drop_column("interview_sessions", "recording_bytes")
    op.drop_column("interview_sessions", "recording_mime")
    op.drop_column("interview_sessions", "recording_path")
