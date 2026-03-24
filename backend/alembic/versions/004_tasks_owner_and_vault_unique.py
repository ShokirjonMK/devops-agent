"""tasks.owner_user_id + credential_vault unique (user_id, credential_type, name)

Revision ID: 004
Revises: 003
Create Date: 2025-03-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_tasks_owner_user_id", "tasks", ["owner_user_id"], unique=False)
    op.create_foreign_key(
        "fk_tasks_owner_user_id",
        "tasks",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("uq_credential_vault_user_name", "credential_vault", type_="unique")
    op.create_unique_constraint(
        "uq_credential_vault_user_type_name",
        "credential_vault",
        ["user_id", "credential_type", "name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_credential_vault_user_type_name", "credential_vault", type_="unique")
    op.create_unique_constraint(
        "uq_credential_vault_user_name",
        "credential_vault",
        ["user_id", "name"],
    )

    op.drop_constraint("fk_tasks_owner_user_id", "tasks", type_="foreignkey")
    op.drop_index("ix_tasks_owner_user_id", table_name="tasks")
    op.drop_column("tasks", "owner_user_id")
