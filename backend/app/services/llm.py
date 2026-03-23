from __future__ import annotations

import json
from typing import Any

import httpx
from openai import OpenAI

from app.config import get_settings


def complete_json(system: str, user: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.ai_provider == "anthropic" and settings.anthropic_api_key:
        return _anthropic_json(system, user, settings)
    return _openai_json(system, user, settings)


def _openai_json(system: str, user: str, settings: Any) -> dict[str, Any]:
    client = OpenAI(
        api_key=settings.openai_api_key or "dummy",
        base_url=settings.openai_base_url or None,
    )
    if not settings.openai_api_key and not settings.openai_base_url:
        raise RuntimeError("OPENAI_API_KEY or OPENAI_BASE_URL (local LLM) is required for ai_provider=openai")
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


def _anthropic_json(system: str, user: str, settings: Any) -> dict[str, Any]:
    api_key = settings.anthropic_api_key
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for ai_provider=anthropic")
    body = {
        "model": settings.anthropic_model,
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
