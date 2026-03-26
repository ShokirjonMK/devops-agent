"""Billing Celery tasks: trial expiry, quota warnings, renewals, low credit alerts."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

from app.celery_app import celery_app
from app.database import SessionLocal

log = structlog.get_logger("billing_tasks")


@celery_app.task(name="check_trial_expirations")
def check_trial_expirations() -> None:
    """Trial muddati tugayotgan va tugagan foydalanuvchilarga bildirishnoma."""
    from app.models import User, UserSubscription
    from app.services.notification_service import notification_service

    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        warn_at = now + timedelta(days=3)

        # 3 kun qolgan triallar
        subs = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.trial_ends_at.isnot(None),
                UserSubscription.trial_ends_at > now,
                UserSubscription.trial_ends_at <= warn_at,
                UserSubscription.plan_id != "free",
            )
            .all()
        )
        for sub in subs:
            user = db.get(User, sub.user_id)
            if user and user.telegram_id:
                days_left = max(1, (sub.trial_ends_at - now).days)
                notification_service.trial_ending_soon(user.telegram_id, days_left)
                log.info("trial_ending_soon_sent", user_id=str(sub.user_id), days_left=days_left)

        # Tugagan triallar — Free ga tushirish
        expired = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.trial_ends_at.isnot(None),
                UserSubscription.trial_ends_at <= now,
                UserSubscription.plan_id != "free",
                UserSubscription.status == "trialing",
            )
            .all()
        )
        for sub in expired:
            user = db.get(User, sub.user_id)
            old_plan = sub.plan_id
            sub.plan_id = "free"
            sub.status = "active"
            sub.trial_ends_at = None
            db.commit()
            if user and user.telegram_id:
                notification_service.trial_expired(user.telegram_id)
            log.info("trial_expired_downgraded", user_id=str(sub.user_id), was=old_plan)
    finally:
        db.close()


@celery_app.task(name="check_quota_warnings")
def check_quota_warnings() -> None:
    """Foydalanuvchilar kvotasini tekshirib, 80% va 100% da ogohlantirish yuborish."""
    from app.models import Task, User, UserSubscription
    from app.services.notification_service import notification_service
    from app.services.quota_service import quota_service

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        for user in users:
            if not user.telegram_id:
                continue
            try:
                stats = quota_service.get_usage_stats(user.id, db)
                limits = quota_service.get_limits(user.id, db)

                task_limit = limits.get("tasks_per_month", 0)
                if task_limit and task_limit > 0:
                    used = stats.get("tasks_used_month", 0)
                    pct = int(used / task_limit * 100)
                    if pct >= 100:
                        notification_service.quota_exceeded(user.telegram_id, "Vazifalar")
                    elif pct >= 80:
                        notification_service.quota_warning(user.telegram_id, "Vazifalar", pct)
            except Exception as e:
                log.error("quota_check_error", user_id=str(user.id), error=str(e))
    finally:
        db.close()


@celery_app.task(name="check_low_credits")
def check_low_credits() -> None:
    """AI kredit balansi $2 dan kam bo'lgan foydalanuvchilarga ogohlantirish."""
    from app.models import AICreditBalance, User
    from app.services.notification_service import notification_service

    db = SessionLocal()
    try:
        low_threshold = 2.0
        balances = (
            db.query(AICreditBalance)
            .filter(AICreditBalance.balance_usd < low_threshold, AICreditBalance.balance_usd > 0)
            .all()
        )
        for bal in balances:
            user = db.get(User, bal.user_id)
            if user and user.telegram_id:
                notification_service.low_credit_warning(user.telegram_id, float(bal.balance_usd))
                log.info("low_credit_warning_sent", user_id=str(bal.user_id), balance=float(bal.balance_usd))
    finally:
        db.close()


@celery_app.task(name="process_subscription_renewals")
def process_subscription_renewals() -> None:
    """Obuna muddati tugayotganlarni tekshirish."""
    from app.models import User, UserSubscription
    from app.services.notification_service import notification_service
    from app.services.payment_service import _downgrade_to_free

    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        # cancel_at_period_end=True va muddat tugagan obunalar
        expired = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.cancel_at_period_end.is_(True),
                UserSubscription.current_period_end <= now,
                UserSubscription.plan_id != "free",
            )
            .all()
        )
        for sub in expired:
            user = db.get(User, sub.user_id)
            _downgrade_to_free(sub.user_id, db)
            if user and user.telegram_id:
                notification_service.trial_expired(user.telegram_id)
            log.info("subscription_cancelled_downgraded", user_id=str(sub.user_id))
    finally:
        db.close()
