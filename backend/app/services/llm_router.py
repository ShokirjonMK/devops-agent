"""LLM tanlash va OpenAI-mos HTTP chaqiruvlar (sync)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AdminSetting, AiTokenConfig, CredentialVault
from app.services.encryption_service import EncryptedBlob, EncryptionService

log = structlog.get_logger()

PROVIDER_LIST: dict[str, dict[str, Any]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini", "o3-mini"],
    },
    "anthropic": {
        "base_url": None,
        "models": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
    },
    "google": {"base_url": None, "models": ["gemini-2.0-flash", "gemini-1.5-pro"]},
    "mistral": {"base_url": "https://api.mistral.ai/v1", "models": ["mistral-large", "codestral"]},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "models": ["llama-3.3-70b", "mixtral-8x7b"]},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "models": ["deepseek-chat", "deepseek-coder"]},
    "xai": {"base_url": "https://api.x.ai/v1", "models": ["grok-2", "grok-beta"]},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "models": ["*"]},
    "together": {"base_url": "https://api.together.xyz/v1", "models": ["*"]},
    "custom": {"base_url": "user_defined", "models": ["*"]},
}

OPENAI_COMPATIBLE = frozenset(
    {"openai", "mistral", "groq", "deepseek", "xai", "openrouter", "together", "custom"}
)


def _vault_ctx(user_id: uuid.UUID, name: str) -> str:
    return f"{user_id}:ai_token:{name}"


class LLMRouter:
    def __init__(self, enc: EncryptionService) -> None:
        self._enc = enc

    def _decrypt_vault_row(self, user_id: uuid.UUID, vault: CredentialVault) -> dict[str, Any]:
        blob = EncryptedBlob.from_storage(vault.cipher_text, vault.iv, vault.salt, vault.tag)
        plain = self._enc.decrypt(blob, _vault_ctx(user_id, vault.name))
        data = json.loads(plain)
        if not isinstance(data, dict):
            raise ValueError("invalid secret json")
        return data

    def pick_default_config(self, db: Session, user_id: uuid.UUID) -> tuple[AiTokenConfig, CredentialVault] | None:
        q = (
            db.query(AiTokenConfig)
            .filter(
                AiTokenConfig.user_id == user_id,
                AiTokenConfig.is_active.is_(True),
            )
            .order_by(AiTokenConfig.is_default.desc(), AiTokenConfig.created_at.desc())
        )
        for cfg in q.all():
            if cfg.monthly_budget_usd is not None and cfg.usage_this_month_usd >= cfg.monthly_budget_usd:
                continue
            v = db.get(CredentialVault, cfg.secret_id)
            if v:
                return cfg, v
        return None

    def test_completion_sync(
        self,
        db: Session,
        user_id: uuid.UUID,
        cfg: AiTokenConfig,
        vault: CredentialVault,
    ) -> tuple[str, int, str]:
        secret = self._decrypt_vault_row(user_id, vault)
        token = (secret.get("token") or "").strip()
        if not token:
            raise ValueError("Token bo‘sh")
        model = (cfg.model_override or secret.get("model") or "").strip()
        if not model:
            models = PROVIDER_LIST.get(cfg.provider, {}).get("models") or []
            model = str(models[0]) if models and models[0] != "*" else get_settings().openai_model
        if cfg.provider in OPENAI_COMPATIBLE:
            bu = (cfg.base_url or secret.get("base_url") or "").strip()
            if not bu or bu == "user_defined":
                bu = str(PROVIDER_LIST.get(cfg.provider, {}).get("base_url") or "https://api.openai.com/v1")
            bu = bu.rstrip("/")
            payload: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a test probe. Reply with JSON {\"ok\":true}."},
                    {"role": "user", "content": "ping"},
                ],
                "max_tokens": 64,
                "response_format": {"type": "json_object"},
            }
            with httpx.Client(timeout=60.0) as client:
                r = client.post(
                    f"{bu}/chat/completions",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()
            text = data["choices"][0]["message"]["content"]
            usage = int(data.get("usage", {}).get("total_tokens") or 0)
            cost_key = db.get(AdminSetting, "default_ai_cost_per_1k")
            per_1k = Decimal("0.002")
            if cost_key is not None:
                try:
                    per_1k = Decimal(str(cost_key.value))
                except Exception:
                    pass
            add_usd = (Decimal(usage) / Decimal(1000)) * per_1k
            cfg.usage_this_month_usd = (cfg.usage_this_month_usd or Decimal(0)) + add_usd
            cfg.last_used_at = datetime.now(UTC)
            db.add(cfg)
            db.commit()
            return text, usage, model
        if cfg.provider == "anthropic":
            bu = "https://api.anthropic.com/v1"
            payload_a = {
                "model": model,
                "max_tokens": 64,
                "system": "Reply with a single word: ok",
                "messages": [{"role": "user", "content": "ping"}],
            }
            with httpx.Client(timeout=60.0) as client:
                r = client.post(
                    f"{bu}/messages",
                    headers={
                        "x-api-key": token,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=payload_a,
                )
                r.raise_for_status()
                data = r.json()
            parts = data.get("content") or []
            text = ""
            if parts and isinstance(parts, list):
                text = str(parts[0].get("text", ""))
            usage = int(data.get("usage", {}).get("input_tokens", 0)) + int(
                data.get("usage", {}).get("output_tokens", 0)
            )
            cfg.last_used_at = datetime.now(UTC)
            db.add(cfg)
            db.commit()
            return text, usage, model
        raise ValueError(f"Test uchun provayder qo‘llab-quvvatlanmaydi: {cfg.provider}")
