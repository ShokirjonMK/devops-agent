"""Celery: server metrikalari, alertlar, tozalash, AI usage reset."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta

from app.celery_app import celery_app
from app.config import get_settings
from app.database import SessionLocal
from app.models import AlertRule, Server, ServerMetric

log = logging.getLogger(__name__)


def _parse_float(s: str) -> float | None:
    s = s.strip().replace("%", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


@celery_app.task(name="collect_all_server_metrics")
def collect_all_server_metrics() -> str:
    db = SessionLocal()
    try:
        servers = db.query(Server).filter(Server.monitoring_enabled.is_(True)).all()
        for s in servers:
            try:
                _collect_one_server(db, s)
            except Exception as e:
                log.warning("metrics server %s: %s", s.id, e)
                s.last_check_status = "warning"
                s.last_check_at = datetime.now(UTC)
                db.add(s)
        db.commit()
    finally:
        db.close()
    return "ok"


def _collect_one_server(db, s: Server) -> None:
    from app.services.ssh_client import SSHExecutor

    settings = get_settings()
    raw_out: dict[str, str] = {}
    cpu = ram = disk = None
    load1 = load5 = load15 = None
    failed: list[str] = []
    try:
        with SSHExecutor(s, settings.ssh_connect_timeout, settings.ssh_command_timeout) as ex:
            r_load = ex.run("cat /proc/loadavg")
            raw_out["loadavg"] = r_load.combined[:2000]
            parts = (r_load.stdout or "").split()
            if len(parts) >= 3:
                load1, load5, load15 = _parse_float(parts[0]), _parse_float(parts[1]), _parse_float(parts[2])

            r_df = ex.run("df -P / 2>/dev/null | tail -1 | awk '{print $5}'")
            raw_out["disk_df"] = r_df.stdout[:500]
            disk = _parse_float((r_df.stdout or "").strip())

            r_free = ex.run(
                "free | awk '/Mem:/ {if ($2>0) printf \"%.2f\", 100*$3/$2; else print \"0\"}'"
            )
            raw_out["ram"] = r_free.stdout[:200]
            ram = _parse_float((r_free.stdout or "").strip())

            r_top = ex.run("command -v top >/dev/null && top -bn1 | head -n 5 || true")
            raw_out["top"] = r_top.stdout[:2000]
            m = re.search(r"(\d+\.?\d*)\s*%?\s*id", r_top.stdout or "")
            if m:
                idle = _parse_float(m.group(1))
                if idle is not None:
                    cpu = max(0.0, min(100.0, 100.0 - idle))

            r_fail = ex.run("systemctl list-units --failed --no-legend --plain 2>/dev/null | head -n 20")
            for line in (r_fail.stdout or "").splitlines():
                line = line.strip()
                if line:
                    failed.append(line.split()[0] if line.split() else line)
        status = "online"
    except Exception as e:
        log.info("ssh metrics skip %s: %s", s.host, e)
        status = "offline"
        raw_out["error"] = str(e)[:500]

    mrow = ServerMetric(
        server_id=s.id,
        collected_at=datetime.now(UTC),
        cpu_percent=cpu,
        ram_percent=ram,
        disk_percent=disk,
        load_1=load1,
        load_5=load5,
        load_15=load15,
        failed_services=failed[:32] or None,
        raw=raw_out,
    )
    db.add(mrow)
    s.last_check_at = datetime.now(UTC)
    s.last_check_status = status
    db.add(s)


@celery_app.task(name="check_alert_rules")
def check_alert_rules() -> str:
    db = SessionLocal()
    try:
        rules = db.query(AlertRule).filter(AlertRule.is_active.is_(True)).all()
        for rule in rules:
            if rule.server_id is None:
                continue
            latest = (
                db.query(ServerMetric)
                .filter(ServerMetric.server_id == rule.server_id)
                .order_by(ServerMetric.collected_at.desc())
                .first()
            )
            if not latest:
                continue
            val = None
            if rule.metric == "cpu":
                val = latest.cpu_percent
            elif rule.metric == "ram":
                val = latest.ram_percent
            elif rule.metric == "disk":
                val = latest.disk_percent
            elif rule.metric == "load":
                val = latest.load_1
            if val is None:
                continue
            if val > rule.threshold:
                rule.last_triggered_at = datetime.now(UTC)
                db.add(rule)
        db.commit()
    finally:
        db.close()
    return "ok"


@celery_app.task(name="cleanup_old_metrics")
def cleanup_old_metrics() -> str:
    db = SessionLocal()
    try:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        db.query(ServerMetric).filter(ServerMetric.collected_at < cutoff).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    return "ok"


@celery_app.task(name="reset_monthly_ai_usage")
def reset_monthly_ai_usage() -> str:
    from app.models import AiTokenConfig

    db = SessionLocal()
    try:
        db.query(AiTokenConfig).update({AiTokenConfig.usage_this_month_usd: 0}, synchronize_session=False)
        db.commit()
    finally:
        db.close()
    return "ok"
