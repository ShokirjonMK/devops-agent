"""Referral tizimi — kod yaratish, qo'llash, mukofot berish."""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.orm import Session

from app.models import ReferralCode, ReferralConversion, UserSubscription

log = structlog.get_logger("referral_service")


class ReferralService:

    def generate_code(self, user_id: uuid.UUID, db: Session) -> ReferralCode:
        existing = db.query(ReferralCode).filter(ReferralCode.owner_id == user_id).first()
        if existing:
            return existing
        # Noyob 8 belgilik kod
        for _ in range(10):
            candidate = secrets.token_urlsafe(6).upper()[:8]
            if not db.get(ReferralCode, candidate):
                code = ReferralCode(code=candidate, owner_id=user_id)
                db.add(code)
                db.commit()
                db.refresh(code)
                return code
        raise ValueError("Referral kod yaratib bo'lmadi")

    def get_code(self, user_id: uuid.UUID, db: Session) -> ReferralCode | None:
        return db.query(ReferralCode).filter(ReferralCode.owner_id == user_id).first()

    def apply_referral(
        self,
        new_user_id: uuid.UUID,
        code: str,
        db: Session,
        trial_days: int = 14,
    ) -> bool:
        rc = db.get(ReferralCode, code.upper())
        if not rc or rc.owner_id == new_user_id:
            return False
        # Har bir user faqat bir marta referral oladi
        existing = (
            db.query(ReferralConversion)
            .filter(ReferralConversion.referred_id == new_user_id)
            .first()
        )
        if existing:
            return False

        # Trial Pro
        self._activate_trial(new_user_id, trial_days, db)

        conv = ReferralConversion(
            referrer_id=rc.owner_id,
            referred_id=new_user_id,
            code=code.upper(),
            status="pending",
        )
        db.add(conv)
        rc.uses_count += 1
        db.commit()
        log.info("referral_applied", referrer=str(rc.owner_id), referred=str(new_user_id), code=code)
        return True

    def reward_referrer_on_payment(
        self,
        payer_id: uuid.UUID,
        reward_usd: float,
        db: Session,
    ) -> bool:
        """Yangi user birinchi to'lovini amalga oshirganda referrer ga $5 kredit."""
        from app.services.credit_service import credit_service

        conv = (
            db.query(ReferralConversion)
            .filter(
                ReferralConversion.referred_id == payer_id,
                ReferralConversion.status == "pending",
            )
            .first()
        )
        if not conv:
            return False

        credit_service.add_bonus_credit(
            conv.referrer_id, reward_usd, f"Referral mukofoti (ref: {str(payer_id)[:8]})", db
        )

        # referral code total_earned yangilash
        rc = db.get(ReferralCode, conv.code)
        if rc:
            from decimal import Decimal
            rc.total_earned_usd = (rc.total_earned_usd or 0) + Decimal(str(reward_usd))

        conv.status = "rewarded"
        conv.first_payment_at = datetime.now(UTC)
        conv.rewarded_at = datetime.now(UTC)
        conv.reward_value = reward_usd
        db.commit()
        log.info("referral_rewarded", referrer=str(conv.referrer_id), amount=reward_usd)
        return True

    def _activate_trial(self, user_id: uuid.UUID, days: int, db: Session) -> None:
        sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
        if not sub:
            return
        now = datetime.now(UTC)
        sub.trial_ends_at = now + timedelta(days=days)
        db.commit()
        log.info("trial_activated", user_id=str(user_id), days=days)

    def get_stats(self, user_id: uuid.UUID, db: Session) -> dict:
        rc = self.get_code(user_id, db)
        if not rc:
            rc = self.generate_code(user_id, db)
        rewarded = (
            db.query(ReferralConversion)
            .filter(
                ReferralConversion.referrer_id == user_id,
                ReferralConversion.status == "rewarded",
            )
            .count()
        )
        return {
            "code": rc.code,
            "uses_count": rc.uses_count,
            "rewarded_count": rewarded,
            "total_earned_usd": float(rc.total_earned_usd or 0),
        }


referral_service = ReferralService()
