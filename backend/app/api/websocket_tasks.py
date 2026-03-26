from __future__ import annotations

import asyncio
import json
import logging
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Task, User
from app.security_jwt import decode_token
from app.services.task_events import task_channel

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


def _role_level(role: str | None) -> int:
    r = (role or "viewer").lower()
    return {"viewer": 0, "operator": 1, "admin": 2, "owner": 3}.get(r, 0)


async def _ping_loop(ws: WebSocket) -> None:
    while True:
        await asyncio.sleep(30)
        try:
            await ws.send_json({"type": "ping"})
        except Exception:
            break


def _ws_authorize_task(db: Session, task_id: int, user_id: uuid.UUID | None) -> bool:
    task = db.get(Task, task_id)
    if not task:
        return False
    if user_id is None:
        if task.owner_user_id is not None:
            return False
        return True
    u = db.get(User, user_id)
    if not u or not u.is_active:
        return False
    if _role_level(u.role) >= 2:
        return True
    if task.owner_user_id is None:
        return True
    return task.owner_user_id == user_id


async def run_task_event_websocket(websocket: WebSocket, task_id: int, token: str | None) -> None:
    user_uuid: uuid.UUID | None = None
    if token:
        try:
            user_uuid = decode_token(token)
        except (ExpiredSignatureError, InvalidTokenError, ValueError):
            await websocket.close(code=4401)
            return

    db = SessionLocal()
    try:
        if not _ws_authorize_task(db, task_id, user_uuid):
            await websocket.close(code=4403)
            return
    finally:
        db.close()

    await websocket.accept()
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = client.pubsub()
    ch = task_channel(task_id)
    await pubsub.subscribe(ch)
    ping_task = asyncio.create_task(_ping_loop(websocket))
    try:
        async for message in pubsub.listen():
            if message.get("type") == "message" and message.get("data"):
                raw = message["data"]
                try:
                    await websocket.send_text(raw)
                except (WebSocketDisconnect, RuntimeError):
                    break
                try:
                    data = json.loads(raw)
                    if data.get("type") in ("task_done", "task_error", "task_cancelled"):
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.debug("ws stream: %s", e)
    finally:
        ping_task.cancel()
        try:
            await pubsub.unsubscribe(ch)
            await pubsub.aclose()
            await client.aclose()
        except Exception:
            pass


@router.websocket("/tasks/{task_id}/stream")
async def task_event_stream(
    websocket: WebSocket,
    task_id: int,
    token: str | None = Query(default=None),
) -> None:
    await run_task_event_websocket(websocket, task_id, token)
