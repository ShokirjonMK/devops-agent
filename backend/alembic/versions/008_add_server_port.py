"""Add port column to servers table.

Revision ID: 008
Revises: 007
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("port", sa.Integer(), server_default="22", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("servers", "port")
