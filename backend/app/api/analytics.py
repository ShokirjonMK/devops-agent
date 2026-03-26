"""Analytics: vazifalar, AI tokenlar, server metrikalari (viewer+)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Role, require_role
from app.models import AiTokenConfig, Server, ServerMetric, Task, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def analytics_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.VIEWER)),
):
    now = datetime.now(UTC)
    day_30 = now - timedelta(days=30)
    tasks = (
        db.query(Task)
        .filter(Task.created_at >= day_30)
        .order_by(Task.created_at.asc())
        .all()
    )
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"day": "", "ok": 0, "bad": 0})
    for t in tasks:
        d = t.created_at.date().isoformat() if t.created_at else ""
        by_day[d]["day"] = d
        if t.status == "done":
            by_day[d]["ok"] += 1
        elif t.status == "error":
            by_day[d]["bad"] += 1
    series = sorted(by_day.values(), key=lambda x: x["day"])[-30:]

    ai_rows = db.query(AiTokenConfig).filter(AiTokenConfig.user_id == user.id).all()
    ai_by_provider: dict[str, float] = defaultdict(float)
    for r in ai_rows:
        try:
            ai_by_provider[r.provider] += float(r.usage_this_month_usd or 0)
        except (TypeError, ValueError):
            pass
    ai_pie = [{"name": k, "value": round(v, 4)} for k, v in sorted(ai_by_provider.items())]

    servers = db.query(Server).all()
    srv_uptime: list[dict[str, object]] = []
    for s in servers:
        online = 1.0 if (s.last_check_status or "") == "online" else 0.0
        srv_uptime.append({"name": s.name, "uptime_score": online * 100.0})

    heat: dict[str, int] = defaultdict(int)
    for t in tasks:
        if t.owner_user_id == user.id and t.created_at:
            heat[t.created_at.date().isoformat()] += 1
    heat_list = sorted(({"day": k, "count": v} for k, v in heat.items()), key=lambda x: x["day"])[-120:]

    total = len(tasks)
    ok = sum(1 for t in tasks if t.status == "done")
    err = sum(1 for t in tasks if t.status == "error")
    success_pct = round(100.0 * ok / total, 1) if total else 0.0
    online_n = sum(1 for s in servers if s.last_check_status == "online")
    uptime_pct = round(100.0 * online_n / len(servers), 1) if servers else 0.0

    try:
        my_ai = float(
            db.query(func.coalesce(func.sum(AiTokenConfig.usage_this_month_usd), 0))
            .filter(AiTokenConfig.user_id == user.id)
            .scalar()
            or 0
        )
    except (TypeError, ValueError):
        my_ai = 0.0

    return {
        "tasks_total_30d": total,
        "tasks_success_30d": ok,
        "tasks_error_30d": err,
        "success_rate_percent": success_pct,
        "uptime_percent": uptime_pct,
        "ai_cost_month_usd": round(my_ai, 4),
        "series_tasks_by_day": series,
        "ai_cost_by_provider": ai_pie,
        "server_uptime_bars": srv_uptime,
        "activity_heatmap": heat_list,
    }


@router.get("/servers/{server_id}/metrics")
def analytics_server_metrics(
    server_id: int,
    hours: int = Query(168, ge=1, le=24 * 60),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.VIEWER)),
):
    row = db.get(Server, server_id)
    if not row:
        return {"error": "not_found", "points": []}
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = (
        db.query(ServerMetric)
        .filter(ServerMetric.server_id == server_id, ServerMetric.collected_at >= since)
        .order_by(ServerMetric.collected_at.asc())
        .all()
    )
    return {
        "server_id": server_id,
        "points": [
            {
                "t": m.collected_at.isoformat() if m.collected_at else None,
                "cpu": m.cpu_percent,
                "ram": m.ram_percent,
                "disk": m.disk_percent,
            }
            for m in rows
        ],
    }
