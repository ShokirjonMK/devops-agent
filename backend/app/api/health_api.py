from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

import redis

from app.config import get_settings
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def api_health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    redis_ok = False
    try:
        r = redis.Redis.from_url(settings.redis_url)
        redis_ok = bool(r.ping())
        r.close()
    except Exception:
        redis_ok = False
    overall = "healthy" if db_ok and redis_ok else "degraded"
    return {
        "status": overall,
        "components": {
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
    }
