"""task_steps explanation and phase

Revision ID: 002
Revises: 001
Create Date: 2025-03-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("task_steps", sa.Column("explanation", sa.Text(), nullable=True))
    op.add_column("task_steps", sa.Column("phase", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("task_steps", "phase")
    op.drop_column("task_steps", "explanation")
