from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

import redis

from app.config import get_settings
from app.database import get_db

router = APIRouter(tags=["health"])


def _celery_worker_count() -> int:
    try:
        from app.celery_app import celery_app

        insp = celery_app.control.inspect(timeout=0.75)
        if insp is None:
            return 0
        stats = insp.stats()
        if not stats:
            return 0
        return len(stats)
    except Exception:
        return 0


@router.get("/health")
def api_health(db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = get_settings()
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    redis_ok = False
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=False)
        redis_ok = bool(r.ping())
        r.close()
    except Exception:
        redis_ok = False

    workers = _celery_worker_count()
    workers_ok = workers > 0

    # DB + Redis majburiy; worker keyin ishga tushishi mumkin (depends_on api healthy — tiqilish bo‘lmasin).
    overall = "healthy" if db_ok and redis_ok else "degraded"

    return {
        "status": overall,
        "components": {
            "database": "ok" if db_ok else "down",
            "redis": "ok" if redis_ok else "down",
            "workers": {"count": workers, "ok": workers_ok},
        },
    }
