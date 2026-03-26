import os
import sys
from logging.config import fileConfig

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import Base
from app.models import (  # noqa: F401
    AdminSetting,
    AICreditBalance,
    AICreditTransaction,
    AiTokenConfig,
    AlertRule,
    AuditLog,
    CredentialVault,
    Notification,
    PaymentRecord,
    Plan,
    PlatformAuditLog,
    ReferralCode,
    ReferralConversion,
    Server,
    ServerMetric,
    Task,
    TaskStep,
    User,
    UserOnboarding,
    UserSubscription,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    u = os.environ.get("DATABASE_URL", "postgresql://devops:devops@localhost:5432/devops_agent")
    if u.startswith("postgresql+asyncpg://"):
        return "postgresql://" + u.removeprefix("postgresql+asyncpg://")
    return u


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
