from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql://devops:devops@localhost:5432/devops_agent",
        validation_alias=AliasChoices("DATABASE_URL"),
    )
    redis_url: str = Field(
        default="redis://:change_me@localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL"),
    )

    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"

    ai_provider: str = "openai"

    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("CELERY_BROKER_URL"),
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("CELERY_RESULT_BACKEND"),
    )

    api_cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        validation_alias=AliasChoices("API_CORS_ORIGINS", "ALLOWED_ORIGINS"),
    )

    ssh_connect_timeout: int = 20
    ssh_command_timeout: int = 120
    ssh_connect_retries: int = 3
    ssh_retry_backoff_seconds: float = 2.0
    agent_max_iterations: int = Field(default=8, validation_alias=AliasChoices("AGENT_MAX_ITERATIONS"))

    jwt_secret: str = Field(default="", validation_alias=AliasChoices("JWT_SECRET"))
    jwt_algorithm: str = Field(default="HS256", validation_alias=AliasChoices("JWT_ALGORITHM"))
    jwt_expire_minutes: int = Field(
        default=1440,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_EXPIRE_MINUTES"),
    )
    refresh_token_expire_days: int = Field(default=30, validation_alias=AliasChoices("REFRESH_TOKEN_EXPIRE_DAYS"))

    encryption_master_key_b64: str = Field(default="", validation_alias=AliasChoices("ENCRYPTION_MASTER_KEY_B64"))
    master_encryption_key: str = Field(default="", validation_alias=AliasChoices("MASTER_ENCRYPTION_KEY"))

    telegram_bot_token: str = Field(default="", validation_alias=AliasChoices("TELEGRAM_BOT_TOKEN"))

    admin_telegram_ids: str = Field(default="", validation_alias=AliasChoices("ADMIN_TELEGRAM_IDS"))

    api_internal_secret: str = Field(default="", validation_alias=AliasChoices("API_INTERNAL_SECRET"))
    app_env: str = Field(default="development", validation_alias=AliasChoices("APP_ENV"))

    # ── Stripe ────────────────────────────────────────────────────────────
    stripe_secret_key: str = Field(default="", validation_alias=AliasChoices("STRIPE_SECRET_KEY"))
    stripe_publishable_key: str = Field(default="", validation_alias=AliasChoices("STRIPE_PUBLISHABLE_KEY"))
    stripe_webhook_secret: str = Field(default="", validation_alias=AliasChoices("STRIPE_WEBHOOK_SECRET"))
    stripe_price_pro_monthly: str = Field(default="", validation_alias=AliasChoices("STRIPE_PRICE_PRO_MONTHLY"))
    stripe_price_team_monthly: str = Field(default="", validation_alias=AliasChoices("STRIPE_PRICE_TEAM_MONTHLY"))

    # ── Click (O'zbekiston) ───────────────────────────────────────────────
    click_service_id: str = Field(default="", validation_alias=AliasChoices("CLICK_SERVICE_ID"))
    click_merchant_id: str = Field(default="", validation_alias=AliasChoices("CLICK_MERCHANT_ID"))
    click_secret_key: str = Field(default="", validation_alias=AliasChoices("CLICK_SECRET_KEY"))

    # ── Payme ─────────────────────────────────────────────────────────────
    payme_merchant_id: str = Field(default="", validation_alias=AliasChoices("PAYME_MERCHANT_ID"))
    payme_secret_key: str = Field(default="", validation_alias=AliasChoices("PAYME_SECRET_KEY"))
    payme_test_mode: bool = Field(default=True, validation_alias=AliasChoices("PAYME_TEST_MODE"))

    # ── UZS narxlar ───────────────────────────────────────────────────────
    plan_pro_price_uzs: int = Field(default=190000, validation_alias=AliasChoices("PLAN_PRO_PRICE_UZS"))
    plan_team_price_uzs: int = Field(default=620000, validation_alias=AliasChoices("PLAN_TEAM_PRICE_UZS"))
    credit_5_price_uzs: int = Field(default=64000, validation_alias=AliasChoices("CREDIT_5_PRICE_UZS"))
    credit_20_price_uzs: int = Field(default=250000, validation_alias=AliasChoices("CREDIT_20_PRICE_UZS"))
    credit_50_price_uzs: int = Field(default=620000, validation_alias=AliasChoices("CREDIT_50_PRICE_UZS"))

    # ── Referral ──────────────────────────────────────────────────────────
    referral_trial_days: int = Field(default=14, validation_alias=AliasChoices("REFERRAL_TRIAL_DAYS"))
    referral_reward_usd: float = Field(default=5.0, validation_alias=AliasChoices("REFERRAL_REWARD_USD"))

    # ── AI markup ─────────────────────────────────────────────────────────
    ai_credit_markup_percent: float = Field(default=50.0, validation_alias=AliasChoices("AI_CREDIT_MARKUP_PERCENT"))

    @field_validator("database_url", mode="before")
    @classmethod
    def _strip_asyncpg(cls, v: object) -> object:
        if isinstance(v, str) and v.startswith("postgresql+asyncpg://"):
            return "postgresql://" + v.removeprefix("postgresql+asyncpg://")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def admin_telegram_ids_list(self) -> list[int]:
        out: list[int] = []
        for p in self.admin_telegram_ids.split(","):
            p = p.strip()
            if p.isdigit():
                out.append(int(p))
        return out

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
