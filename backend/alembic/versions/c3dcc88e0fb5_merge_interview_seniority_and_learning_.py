"""merge interview seniority and learning hub

Revision ID: c3dcc88e0fb5
Revises: b41a9d2e6f30, 0b76301fe10f
Create Date: 2026-11-06 22:24:31.312062

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = 'c3dcc88e0fb5'
down_revision: str | None = ('b41a9d2e6f30', '0b76301fe10f')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
