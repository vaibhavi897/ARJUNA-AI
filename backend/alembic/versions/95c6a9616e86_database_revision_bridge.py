"""Recognize the deployed database revision missing from this checkout.

The configured database already records this revision and contains the active
application schema. This no-op bridge restores Alembic's revision graph so
subsequent additive migrations can be applied without resetting database
revision state or touching existing data.
"""
from collections.abc import Sequence

revision: str = "95c6a9616e86"
down_revision: str | None = "537c73c23e9b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
