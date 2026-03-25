"""Users/servers columns, system user, tasks.telegram_message_id, admin_settings seed.

Revision ID: 006
Revises: 005
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(16), nullable=False, server_default="viewer"))
    op.add_column(
        "users",
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    op.add_column(
        "servers",
        sa.Column("environment", sa.String(16), nullable=False, server_default="production"),
    )
    op.add_column(
        "servers",
        sa.Column("monitoring_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "servers",
        sa.Column("monitoring_interval_minutes", sa.Integer(), nullable=False, server_default="5"),
    )
    op.add_column(
        "servers",
        sa.Column("last_check_status", sa.String(16), nullable=False, server_default="unknown"),
    )
    op.add_column("servers", sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "servers",
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=True),
    )

    op.add_column("tasks", sa.Column("telegram_message_id", sa.BigInteger(), nullable=True))

    op.execute(
        """
        UPDATE users SET role = 'operator'
        WHERE telegram_id > 0 AND (role IS NULL OR role = 'viewer')
        """
    )

    op.execute(
        f"""
        INSERT INTO users (id, telegram_id, username, first_name, role, is_active)
        VALUES ('{SYSTEM_USER_ID}'::uuid, -1, 'system', 'Platform', 'owner', false)
        ON CONFLICT (telegram_id) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO admin_settings (key, value, description) VALUES
        ('default_ai_provider', to_jsonb('openai'::text), 'Fallback AI provider'),
        ('default_ai_model', to_jsonb('gpt-4o-mini'::text), 'Fallback AI model'),
        ('default_ai_cost_per_1k', to_jsonb(0.002::numeric), 'USD per 1k tokens for default'),
        ('require_admin_approval', to_jsonb(false), 'New users need admin approval'),
        ('max_tasks_per_day', to_jsonb(100), 'Max tasks per user/day'),
        ('registration_open', to_jsonb(true), 'Allow new registrations')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_column("tasks", "telegram_message_id")
    op.drop_column("servers", "metadata")
    op.drop_column("servers", "last_check_at")
    op.drop_column("servers", "last_check_status")
    op.drop_column("servers", "monitoring_interval_minutes")
    op.drop_column("servers", "monitoring_enabled")
    op.drop_column("servers", "environment")
    op.drop_column("users", "last_seen_at")
    op.drop_column("users", "settings")
    op.drop_column("users", "role")
    op.execute(sa.text("DELETE FROM users WHERE id = CAST(:sid AS uuid)").bindparams(sid=SYSTEM_USER_ID))
