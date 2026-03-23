from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://devops:devops@localhost:5432/devops_agent"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"

    ai_provider: str = "openai"  # openai | anthropic

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    api_cors_origins: str = "http://localhost:5173,http://localhost:3000"

    ssh_connect_timeout: int = 20
    ssh_command_timeout: int = 120
    ssh_connect_retries: int = 3
    ssh_retry_backoff_seconds: float = 2.0
    agent_max_iterations: int = 8

    jwt_secret: str = ""
    jwt_expire_minutes: int = 1440
    encryption_master_key_b64: str = ""
    telegram_bot_token: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
