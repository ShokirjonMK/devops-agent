from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.vault_llm import user_anthropic_config, user_openai_config


def complete_json(
    system: str,
    user: str,
    *,
    db: Session | None = None,
    owner_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    provider = settings.ai_provider  # global default

    # Auto-detect: use whichever key the user actually configured in vault
    if db and owner_user_id:
        anthropic_cfg = user_anthropic_config(db, owner_user_id) or {}
        openai_cfg = user_openai_config(db, owner_user_id) or {}
        has_anthropic = bool(anthropic_cfg.get("api_key"))
        has_openai = bool(openai_cfg.get("api_key"))
        if has_anthropic and not has_openai:
            provider = "anthropic"
        elif has_openai and not has_anthropic:
            provider = "openai"
        # if both or neither: use global setting

    if provider == "anthropic":
        return _anthropic_json(system, user, settings, db=db, owner_user_id=owner_user_id)
    return _openai_json(system, user, settings, db=db, owner_user_id=owner_user_id)


def _openai_json(
    system: str,
    user: str,
    settings: Any,
    *,
    db: Session | None = None,
    owner_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    api_key = (settings.openai_api_key or "").strip()
    base_url = settings.openai_base_url or None
    model = settings.openai_model
    if db and owner_user_id:
        ucfg = user_openai_config(db, owner_user_id)
        if ucfg and ucfg.get("api_key"):
            api_key = str(ucfg["api_key"]).strip()
            if ucfg.get("base_url"):
                base_url = str(ucfg["base_url"])
            if ucfg.get("model"):
                model = str(ucfg["model"])
    if not api_key and not base_url:
        raise RuntimeError(
            "OpenAI API kaliti yo‘q: .env (OPENAI_API_KEY) yoki profil uchun /api/ai-keys orqali qo‘shing"
        )
    client = OpenAI(
        api_key=api_key or "not-needed",
        base_url=base_url,
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


# Snapshot IDs first — ba’zi hisoblarda alias (masalan claude-sonnet-4-6) hali yo‘q; 404 bo‘lsa ketma-ket sinaymiz.
_ANTHROPIC_FALLBACK_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001",
    "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307",
]


def _anthropic_http_detail(exc: httpx.HTTPStatusError) -> str:
    try:
        data = exc.response.json()
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
            typ = err.get("type")
            if msg and typ:
                return f"{typ}: {msg}"
            if msg:
                return str(msg)
    except Exception:
        pass
    text = (exc.response.text or "").strip()
    if text:
        return text[:800]
    return str(exc)


def _call_anthropic(
    api_key: str,
    model: str,
    system: str,
    user: str,
    *,
    base_url: str | None = None,
) -> dict[str, Any]:
    root = (base_url or "https://api.anthropic.com").rstrip("/")
    url = f"{root}/v1/messages"
    body = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": [{"role": "user", "content": user + "\n\nReply with a single JSON object only, no markdown."}],
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(
            url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
        )
        r.raise_for_status()
        data = r.json()
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].removesuffix("```").strip()
    return json.loads(text)


def _anthropic_json(
    system: str,
    user: str,
    settings: Any,
    *,
    db: Session | None = None,
    owner_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    api_key = (settings.anthropic_api_key or "").strip()
    model = (settings.anthropic_model or "").strip()
    base_url: str | None = None
    if db and owner_user_id:
        ucfg = user_anthropic_config(db, owner_user_id)
        if ucfg and ucfg.get("api_key"):
            api_key = str(ucfg["api_key"]).strip()
            if ucfg.get("base_url"):
                base_url = str(ucfg["base_url"]).strip() or None
            if ucfg.get("model"):
                model = str(ucfg["model"]).strip()
    if not api_key:
        raise RuntimeError(
            "Anthropic API kaliti yo’q: .env (ANTHROPIC_API_KEY) yoki /ai-keys sahifasiga qo’shing"
        )
    # Try the configured model, fall back to alternatives if model missing / not allowed
    models_to_try = [model] + [m for m in _ANTHROPIC_FALLBACK_MODELS if m != model]
    last_err: httpx.HTTPStatusError | None = None
    for m in models_to_try:
        try:
            return _call_anthropic(api_key, m, system, user, base_url=base_url)
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code == 401:
                raise RuntimeError(
                    "Anthropic: API kaliti yaroqsiz (401). "
                    "https://platform.claude.com/settings/keys yoki workspace kalitlaridan yangi kalit yarating; "
                    "bo‘sh joy qo‘shmasdan nusxalang."
                ) from e
            if code == 402:
                raise RuntimeError(
                    "Anthropic: hisobda mablag‘ yetarli emas (402). "
                    "https://platform.claude.com da billing/to‘lovni tekshiring."
                ) from e
            if code in (404, 400, 403):
                last_err = e
                continue
            raise RuntimeError(
                f"Anthropic API xatosi ({code}): {_anthropic_http_detail(e)}"
            ) from e
    assert last_err is not None
    raise RuntimeError(
        "Anthropic so‘rovi rad etildi (odatda model ID noto‘g‘ri yoki bu kalit uchun model mavjud emas — 404/403). "
        "/ai-keys da kalitni o‘chirib, model sifatida «Claude Sonnet 4 (20250514)» ni tanlab qayta saqlang. "
        f"Javob: {_anthropic_http_detail(last_err)}"
    ) from last_err
