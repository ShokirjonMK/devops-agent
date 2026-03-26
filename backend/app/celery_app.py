from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "devops_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "beat-heartbeat-5m": {
            "task": "beat_heartbeat",
            "schedule": 300.0,
        },
        "collect-metrics-5m": {
            "task": "collect_all_server_metrics",
            "schedule": 300.0,
        },
        "check-alerts-2m": {
            "task": "check_alert_rules",
            "schedule": 120.0,
        },
        "cleanup-metrics-daily": {
            "task": "cleanup_old_metrics",
            "schedule": crontab(hour=2, minute=0),
        },
        "reset-ai-usage-monthly": {
            "task": "reset_monthly_ai_usage",
            "schedule": crontab(day_of_month=1, hour=0, minute=0),
        },
        "check-trial-expirations-daily": {
            "task": "check_trial_expirations",
            "schedule": crontab(hour=9, minute=0),
        },
        "check-quota-warnings-daily": {
            "task": "check_quota_warnings",
            "schedule": crontab(hour=10, minute=0),
        },
        "check-low-credits-daily": {
            "task": "check_low_credits",
            "schedule": crontab(hour=11, minute=0),
        },
        "process-renewals-hourly": {
            "task": "process_subscription_renewals",
            "schedule": crontab(minute=0),
        },
    },
)

import app.worker_tasks  # noqa: E402, F401
import app.beat_tasks  # noqa: E402, F401
import app.monitoring_tasks  # noqa: E402, F401
import app.billing_tasks  # noqa: E402, F401
