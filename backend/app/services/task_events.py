"""Vazifa hodisalarini Redis pub/sub orqali yuborish (worker → WebSocket mijozlar)."""

from __future__ import annotations

import json
from typing import Any

import redis

from app.config import get_settings


def _client() -> redis.Redis:
    s = get_settings()
    return redis.Redis.from_url(s.redis_url, decode_responses=True)


def task_channel(task_id: int) -> str:
    return f"task:{task_id}:events"


def publish_task_event(task_id: int, event_type: str, payload: dict[str, Any]) -> None:
    body = json.dumps({"type": event_type, "task_id": task_id, **payload}, ensure_ascii=False)
    try:
        _client().publish(task_channel(task_id), body)
    except Exception:
        pass
