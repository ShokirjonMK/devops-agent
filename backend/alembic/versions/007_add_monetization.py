"""Plans, subscriptions, AI credits, referrals, onboarding, payments.

Revision ID: 007
Revises: 006
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── plans ─────────────────────────────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_uzs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("billing_period", sa.String(16), nullable=False, server_default="'monthly'"),
        sa.Column("limits", postgresql.JSONB, nullable=False, server_default="'{}'::jsonb"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("features_list", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── seed plans ────────────────────────────────────────────────────────
    op.execute("""
    INSERT INTO plans (id, name, price_usd, price_uzs, limits, features_list, sort_order) VALUES
    ('free', 'Free', 0, 0,
     '{"servers_max":3,"tasks_per_day":10,"tasks_per_month":50,"team_members":1,
       "monitoring_enabled":false,"custom_ai_keys":false,"analytics_days":7,
       "webhook_alerts":false,"api_access":false,"sla_percent":99.0}'::jsonb,
     '["3 ta server","50 task/oy","Community AI","7 kunlik analytics"]'::jsonb,
     1),
    ('pro', 'Pro', 15, 190000,
     '{"servers_max":20,"tasks_per_day":200,"tasks_per_month":-1,"team_members":1,
       "monitoring_enabled":true,"custom_ai_keys":true,"analytics_days":90,
       "webhook_alerts":true,"api_access":false,"sla_percent":99.5}'::jsonb,
     '["20 ta server","Cheksiz task","O''z AI kalitlari","Monitoring + alertlar","90 kunlik analytics","Webhook bildirishnomalar"]'::jsonb,
     2),
    ('team', 'Team', 49, 620000,
     '{"servers_max":-1,"tasks_per_day":-1,"tasks_per_month":-1,"team_members":10,
       "monitoring_enabled":true,"custom_ai_keys":true,"analytics_days":365,
       "webhook_alerts":true,"api_access":true,"sla_percent":99.9}'::jsonb,
     '["Cheksiz server","10 jamoa a''zosi","To''liq RBAC","API access","1 yillik analytics","SLA 99.9%","Priority support"]'::jsonb,
     3),
    ('enterprise', 'Enterprise', 299, 3800000,
     '{"servers_max":-1,"tasks_per_day":-1,"tasks_per_month":-1,"team_members":-1,
       "monitoring_enabled":true,"custom_ai_keys":true,"analytics_days":-1,
       "webhook_alerts":true,"api_access":true,"white_label":true,"sla_percent":99.99}'::jsonb,
     '["Cheksiz hamma narsa","White-label","On-premise variant","Dedicated support","Custom SLA"]'::jsonb,
     4)
    ON CONFLICT (id) DO NOTHING;
    """)

    # ── user_subscriptions ────────────────────────────────────────────────
    op.create_table(
        "user_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("plan_id", sa.String(32), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="'active'"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("payment_provider", sa.String(32), nullable=True),
        sa.Column("external_subscription_id", sa.String(128), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])

    # Existing users → Free plan
    op.execute("""
    INSERT INTO user_subscriptions (user_id, plan_id, status, current_period_start, current_period_end)
    SELECT id, 'free', 'active', now(), now() + interval '100 years'
    FROM users
    ON CONFLICT (user_id) DO NOTHING;
    """)

    # Trigger: new users auto get Free plan
    op.execute("""
    CREATE OR REPLACE FUNCTION auto_assign_free_plan()
    RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO user_subscriptions (user_id, plan_id, status, current_period_start, current_period_end)
        VALUES (NEW.id, 'free', 'active', now(), now() + interval '100 years')
        ON CONFLICT (user_id) DO NOTHING;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trigger_user_free_plan
    AFTER INSERT ON users FOR EACH ROW EXECUTE FUNCTION auto_assign_free_plan();
    """)

    # ── ai_credit_balances ────────────────────────────────────────────────
    op.create_table(
        "ai_credit_balances",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("balance_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("total_deposited_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("total_spent_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("last_deposit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.execute("""
    INSERT INTO ai_credit_balances (user_id, balance_usd)
    SELECT id, 0 FROM users ON CONFLICT (user_id) DO NOTHING;
    """)

    # ── ai_credit_transactions ────────────────────────────────────────────
    op.create_table(
        "ai_credit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("amount_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("description", sa.String(256), nullable=True),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("cost_price_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("retail_price_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("markup_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_credit_transactions_user_id", "ai_credit_transactions", ["user_id"])

    # ── referral_codes ────────────────────────────────────────────────────
    op.create_table(
        "referral_codes",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("uses_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_earned_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_referral_codes_owner_id", "referral_codes", ["owner_id"])

    # Existing users get referral codes
    op.execute("""
    INSERT INTO referral_codes (code, owner_id)
    SELECT upper(left(replace(gen_random_uuid()::text, '-', ''), 8)), id
    FROM users
    ON CONFLICT (owner_id) DO NOTHING;
    """)

    # ── referral_conversions ──────────────────────────────────────────────
    op.create_table(
        "referral_conversions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("referrer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("referred_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="'pending'"),
        sa.Column("reward_value", sa.Numeric(10, 4), nullable=True),
        sa.Column("first_payment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rewarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_referral_conversions_referrer_id", "referral_conversions", ["referrer_id"])

    # ── user_onboarding ───────────────────────────────────────────────────
    op.create_table(
        "user_onboarding",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("steps_data", postgresql.JSONB, nullable=False, server_default="'{}'::jsonb"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.execute("""
    INSERT INTO user_onboarding (user_id, step)
    SELECT id, 0 FROM users ON CONFLICT (user_id) DO NOTHING;
    """)

    # ── payment_records ───────────────────────────────────────────────────
    op.create_table(
        "payment_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.String(32), nullable=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("amount_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount_local", sa.Integer, nullable=True),
        sa.Column("currency_local", sa.String(8), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="'pending'"),
        sa.Column("external_id", sa.String(256), nullable=True),
        sa.Column("payment_metadata", postgresql.JSONB, nullable=False, server_default="'{}'::jsonb"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_payment_records_user_id", "payment_records", ["user_id"])
    op.create_index("ix_payment_records_external_id", "payment_records", ["external_id"])


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_user_free_plan ON users;")
    op.execute("DROP FUNCTION IF EXISTS auto_assign_free_plan();")
    op.drop_table("payment_records")
    op.drop_table("user_onboarding")
    op.drop_table("referral_conversions")
    op.drop_table("referral_codes")
    op.drop_table("ai_credit_transactions")
    op.drop_table("ai_credit_balances")
    op.drop_table("user_subscriptions")
    op.drop_table("plans")
