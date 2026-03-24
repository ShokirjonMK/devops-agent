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
    if settings.ai_provider == "anthropic":
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


def _anthropic_json(
    system: str,
    user: str,
    settings: Any,
    *,
    db: Session | None = None,
    owner_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    api_key = settings.anthropic_api_key
    model = settings.anthropic_model
    if db and owner_user_id:
        ucfg = user_anthropic_config(db, owner_user_id)
        if ucfg and ucfg.get("api_key"):
            api_key = str(ucfg["api_key"])
            if ucfg.get("model"):
                model = str(ucfg["model"])
    if not api_key:
        raise RuntimeError(
            "Anthropic API kaliti yo‘q: .env (ANTHROPIC_API_KEY) yoki /api/ai-keys orqali qo‘shing"
        )
    body = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": [{"role": "user", "content": user + "\n\nReply with a single JSON object only, no markdown."}],
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(
            "https://api.anthropic.com/v1/messages",
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
