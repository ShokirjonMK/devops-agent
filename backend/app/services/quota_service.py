"""Foydalanuvchi tarif limitlarini tekshirish."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Plan, Server, Task, UserSubscription


class QuotaService:

    def get_subscription(self, user_id: uuid.UUID, db: Session) -> UserSubscription:
        sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
        if not sub:
            # Free planga avtomatik o'tkazish
            sub = UserSubscription(
                user_id=user_id,
                plan_id="free",
                status="active",
                current_period_start=datetime.now(UTC),
                current_period_end=datetime.now(UTC) + timedelta(days=36500),
            )
            db.add(sub)
            db.commit()
            db.refresh(sub)
        return sub

    def get_plan(self, plan_id: str, db: Session) -> Plan:
        plan = db.get(Plan, plan_id)
        if not plan:
            # fallback free
            plan = db.get(Plan, "free")
        return plan

    def get_limits(self, user_id: uuid.UUID, db: Session) -> dict:
        sub = self.get_subscription(user_id, db)
        effective_plan = sub.plan_id
        # trial aktiv bo'lsa → pro limitleri
        if sub.trial_ends_at and sub.trial_ends_at > datetime.now(UTC):
            effective_plan = "pro"
        plan = self.get_plan(effective_plan, db)
        return plan.limits if plan else {}

    def _count_tasks_today(self, user_id: uuid.UUID, db: Session) -> int:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            db.query(func.count(Task.id))
            .filter(Task.owner_user_id == user_id, Task.created_at >= today_start)
            .scalar()
            or 0
        )

    def _count_tasks_month(self, user_id: uuid.UUID, db: Session) -> int:
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return (
            db.query(func.count(Task.id))
            .filter(Task.owner_user_id == user_id, Task.created_at >= month_start)
            .scalar()
            or 0
        )

    def _count_servers(self, user_id: uuid.UUID, db: Session) -> int:
        # Server count (all servers visible to operator)
        return db.query(func.count(Server.id)).scalar() or 0

    def check_task_quota(self, user_id: uuid.UUID, db: Session) -> None:
        limits = self.get_limits(user_id, db)

        tasks_per_day = limits.get("tasks_per_day", -1)
        if tasks_per_day != -1:
            today_count = self._count_tasks_today(user_id, db)
            if today_count >= tasks_per_day:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": "QUOTA_EXCEEDED",
                        "type": "daily_tasks",
                        "current": today_count,
                        "limit": tasks_per_day,
                        "upgrade_to": "pro",
                        "message": f"Kunlik {tasks_per_day} ta task limitiga yetdingiz.",
                        "upgrade_url": "/upgrade",
                    },
                )

        tasks_per_month = limits.get("tasks_per_month", -1)
        if tasks_per_month != -1:
            month_count = self._count_tasks_month(user_id, db)
            if month_count >= tasks_per_month:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": "QUOTA_EXCEEDED",
                        "type": "monthly_tasks",
                        "current": month_count,
                        "limit": tasks_per_month,
                        "upgrade_to": "pro",
                        "message": f"Oylik {tasks_per_month} ta task limitiga yetdingiz.",
                        "upgrade_url": "/upgrade",
                    },
                )

    def check_server_quota(self, user_id: uuid.UUID, db: Session) -> None:
        limits = self.get_limits(user_id, db)
        servers_max = limits.get("servers_max", -1)
        if servers_max == -1:
            return
        count = self._count_servers(user_id, db)
        if count >= servers_max:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "type": "servers",
                    "current": count,
                    "limit": servers_max,
                    "upgrade_to": "pro",
                    "message": f"{servers_max} ta server limitiga yetdingiz.",
                    "upgrade_url": "/upgrade",
                },
            )

    def check_feature(self, user_id: uuid.UUID, feature: str, db: Session) -> None:
        limits = self.get_limits(user_id, db)
        if not limits.get(feature, False):
            sub = self.get_subscription(user_id, db)
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "FEATURE_NOT_AVAILABLE",
                    "feature": feature,
                    "current_plan": sub.plan_id,
                    "message": f"Bu funksiya {sub.plan_id} tarifida mavjud emas.",
                    "upgrade_url": "/upgrade",
                },
            )

    def get_usage_stats(self, user_id: uuid.UUID, db: Session) -> dict:
        sub = self.get_subscription(user_id, db)
        limits = self.get_limits(user_id, db)
        return {
            "plan": sub.plan_id,
            "status": sub.status,
            "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
            "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "servers": {
                "used": self._count_servers(user_id, db),
                "limit": limits.get("servers_max", -1),
            },
            "tasks_today": {
                "used": self._count_tasks_today(user_id, db),
                "limit": limits.get("tasks_per_day", -1),
            },
            "tasks_month": {
                "used": self._count_tasks_month(user_id, db),
                "limit": limits.get("tasks_per_month", -1),
            },
            "features": {
                "monitoring_enabled": limits.get("monitoring_enabled", False),
                "custom_ai_keys": limits.get("custom_ai_keys", False),
                "analytics_days": limits.get("analytics_days", 7),
                "webhook_alerts": limits.get("webhook_alerts", False),
                "api_access": limits.get("api_access", False),
            },
        }


quota_service = QuotaService()
