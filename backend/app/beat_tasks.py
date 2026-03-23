"""Celery Beat uchun vaqtli vazifalar."""

from __future__ import annotations

import logging

from app.celery_app import celery_app

log = logging.getLogger("celery.beat")


@celery_app.task(name="beat_heartbeat")
def beat_heartbeat() -> str:
    """Sog‘lomlik: beat va worker ishlayotganini tasdiqlash."""
    log.info("beat_heartbeat")
    return "ok"
