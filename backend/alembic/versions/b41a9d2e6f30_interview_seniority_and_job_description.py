"""add interview seniority and optional job description"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b41a9d2e6f30"
down_revision: str | None = "9d2e1f4a7c10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("seniority", sa.String(length=30), nullable=False, server_default="Mid-Level (4–8 years)"),
    )
    op.add_column(
        "interview_sessions",
        sa.Column("job_description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interview_sessions", "job_description")
    op.drop_column("interview_sessions", "seniority")
