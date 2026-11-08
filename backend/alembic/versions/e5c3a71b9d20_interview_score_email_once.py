"""Record when an interview score email was sent, so it is sent only once."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e5c3a71b9d20"
down_revision: str | Sequence[str] | None = "b4e7c1a20d93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("score_email_sent_at", sa.String(length=40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interview_sessions", "score_email_sent_at")
