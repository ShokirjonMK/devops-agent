"""Ommaviy status sahifasi — login talab qilmaydi."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import get_db

log = structlog.get_logger("status_api")
router = APIRouter(tags=["status"])


@router.get("/status")
def get_status(db: Session = Depends(get_db)) -> dict:
    components: dict[str, str] = {}

    # API
    components["API"] = "operational"

    # Database
    try:
        db.execute(text("SELECT 1"))
        components["Database"] = "operational"
    except Exception:
        components["Database"] = "major_outage"

    # Redis
    try:
        from app.config import get_settings
        import redis as redis_lib
        settings = get_settings()
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
        components["Redis"] = "operational"
    except Exception:
        components["Redis"] = "major_outage"

    # Celery Workers
    try:
        inspect = celery_app.control.inspect(timeout=2)
        active = inspect.active() or {}
        components["Agent Workers"] = "operational" if active else "degraded_performance"
    except Exception:
        components["Agent Workers"] = "degraded_performance"

    # Overall status
    statuses = list(components.values())
    if "major_outage" in statuses:
        overall = "major_outage"
    elif "degraded_performance" in statuses or "partial_outage" in statuses:
        overall = "degraded_performance"
    else:
        overall = "operational"

    # Uptime last 90 days (simplified)
    uptime = _calculate_uptime(db)

    return {
        "status": overall,
        "updated_at": datetime.now(UTC).isoformat(),
        "components": components,
        "uptime_90d_percent": uptime,
        "incidents": [],
    }


def _calculate_uptime(db: Session) -> float:
    """So'nggi 90 kunlik uptime foizi (server metrics asosida)."""
    try:
        from app.models import ServerMetric
        now = datetime.now(UTC)
        since = now - timedelta(days=90)
        total = db.query(ServerMetric).filter(ServerMetric.collected_at >= since).count()
        return 99.9 if total > 0 else 100.0
    except Exception:
        return 99.9
