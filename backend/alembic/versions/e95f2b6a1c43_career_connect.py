"""career connect opportunities, contacts and tracker"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e95f2b6a1c43"
down_revision: str | None = "c3dcc88e0fb5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_connect_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_key", sa.String(64), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("company", sa.String(200)),
        sa.Column("location", sa.String(200)),
        sa.Column("experience", sa.String(100)),
        sa.Column("employment_type", sa.String(80)),
        sa.Column("description", sa.Text()),
        sa.Column("sources", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "external_key", name="uq_career_connect_jobs_user_external"),
    )
    op.create_index("ix_career_connect_jobs_user_id", "career_connect_jobs", ["user_id"])
    op.create_index("ix_career_connect_jobs_user_saved", "career_connect_jobs", ["user_id", "created_at"])

    op.create_table(
        "career_connect_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_url", sa.String(500), nullable=False),
        sa.Column("name", sa.String(200)),
        sa.Column("designation", sa.String(200)),
        sa.Column("company", sa.String(200)),
        sa.Column("department", sa.String(120)),
        sa.Column("location", sa.String(200)),
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "profile_url", name="uq_career_connect_contacts_user_url"),
    )
    op.create_index("ix_career_connect_contacts_user_id", "career_connect_contacts", ["user_id"])
    op.create_index("ix_career_connect_contacts_user_created", "career_connect_contacts", ["user_id", "created_at"])

    op.create_table(
        "career_connect_tracker_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("career_connect_jobs.id", ondelete="SET NULL")),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("career_connect_contacts.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("organization", sa.String(200)),
        sa.Column("status", sa.String(30), nullable=False, server_default="saved"),
        sa.Column("reminder_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_career_connect_tracker_items_user_id", "career_connect_tracker_items", ["user_id"])
    op.create_index("ix_career_connect_tracker_items_job_id", "career_connect_tracker_items", ["job_id"])
    op.create_index("ix_career_connect_tracker_items_contact_id", "career_connect_tracker_items", ["contact_id"])
    op.create_index("ix_career_connect_tracker_user_status", "career_connect_tracker_items", ["user_id", "status"])
    op.create_index("ix_career_connect_tracker_user_reminder", "career_connect_tracker_items", ["user_id", "reminder_at"])


def downgrade() -> None:
    op.drop_table("career_connect_tracker_items")
    op.drop_table("career_connect_contacts")
    op.drop_table("career_connect_jobs")
