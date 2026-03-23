from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.services.task_events import task_channel

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/tasks/{task_id}/stream")
async def task_event_stream(websocket: WebSocket, task_id: int) -> None:
    await websocket.accept()
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = client.pubsub()
    ch = task_channel(task_id)
    await pubsub.subscribe(ch)
    try:
        async for message in pubsub.listen():
            if message.get("type") == "message" and message.get("data"):
                try:
                    await websocket.send_text(message["data"])
                except (WebSocketDisconnect, RuntimeError):
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(ch)
        await pubsub.aclose()
        await client.aclose()
