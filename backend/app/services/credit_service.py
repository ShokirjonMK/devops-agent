"""AI kredit tizimi — 50% ustama bilan to'lov."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy.orm import Session

from app.models import AICreditBalance, AICreditTransaction, AiTokenConfig

log = structlog.get_logger("credit_service")

AI_COSTS_PER_1K_TOKENS: dict[str, float] = {
    "openai:gpt-4o": 0.005,
    "openai:gpt-4o-mini": 0.000150,
    "openai:gpt-4-turbo": 0.010,
    "anthropic:claude-opus-4-6": 0.015,
    "anthropic:claude-sonnet-4-6": 0.003,
    "anthropic:claude-haiku-4-5": 0.000250,
    "anthropic:claude-3-5-haiku-20241022": 0.000250,
    "google:gemini-flash": 0.000075,
    "groq:llama-3.3-70b": 0.000059,
}

CREDIT_PACKAGES = [
    {"id": "credit_5", "amount_usd": 5.0, "label": "$5 kredit"},
    {"id": "credit_20", "amount_usd": 20.0, "label": "$20 kredit"},
    {"id": "credit_50", "amount_usd": 50.0, "label": "$50 kredit"},
]


class CreditService:

    def __init__(self, markup_percent: float = 50.0):
        self.markup = markup_percent / 100.0

    def get_or_create_balance(self, user_id: uuid.UUID, db: Session) -> AICreditBalance:
        bal = db.get(AICreditBalance, user_id)
        if not bal:
            bal = AICreditBalance(user_id=user_id, balance_usd=Decimal("0"))
            db.add(bal)
            db.commit()
            db.refresh(bal)
        return bal

    def has_own_key(self, user_id: uuid.UUID, provider: str, db: Session) -> bool:
        return (
            db.query(AiTokenConfig)
            .filter(
                AiTokenConfig.user_id == user_id,
                AiTokenConfig.provider == provider,
                AiTokenConfig.is_active.is_(True),
            )
            .first()
            is not None
        )

    def charge_for_task(
        self,
        user_id: uuid.UUID,
        task_id: int,
        provider: str,
        model: str,
        tokens_used: int,
        db: Session,
    ) -> bool:
        """Task tugagandan keyin kredit yechish. True = muvaffaqiyatli."""
        if self.has_own_key(user_id, provider, db):
            return True  # O'z kaliti — kredit yechilmaydi

        cost_key = f"{provider}:{model}"
        cost_per_1k = AI_COSTS_PER_1K_TOKENS.get(cost_key, 0.002)
        cost_usd = Decimal(str((tokens_used / 1000) * cost_per_1k))
        retail_usd = cost_usd * Decimal(str(1 + self.markup))

        bal = self.get_or_create_balance(user_id, db)
        if bal.balance_usd < retail_usd:
            log.warning("low_credit", user_id=str(user_id), balance=float(bal.balance_usd), needed=float(retail_usd))
            return False

        bal.balance_usd -= retail_usd
        bal.total_spent_usd += retail_usd
        bal.updated_at = datetime.now(UTC)

        txn = AICreditTransaction(
            user_id=user_id,
            type="spend",
            amount_usd=-retail_usd,
            task_id=task_id,
            provider=provider,
            tokens_used=tokens_used,
            cost_price_usd=cost_usd,
            retail_price_usd=retail_usd,
            markup_percent=Decimal(str(self.markup * 100)),
            description=f"Task AI: {provider}/{model}, {tokens_used} tokens",
        )
        db.add(txn)
        db.commit()
        return True

    def add_credit(
        self,
        user_id: uuid.UUID,
        amount_usd: float,
        payment_description: str,
        db: Session,
    ) -> AICreditBalance:
        """To'lovdan keyin kredit qo'shish."""
        amount = Decimal(str(amount_usd))
        bal = self.get_or_create_balance(user_id, db)
        bal.balance_usd += amount
        bal.total_deposited_usd += amount
        bal.last_deposit_at = datetime.now(UTC)
        bal.updated_at = datetime.now(UTC)

        txn = AICreditTransaction(
            user_id=user_id,
            type="deposit",
            amount_usd=amount,
            description=payment_description,
        )
        db.add(txn)
        db.commit()
        db.refresh(bal)
        return bal

    def add_bonus_credit(
        self,
        user_id: uuid.UUID,
        amount_usd: float,
        reason: str,
        db: Session,
    ) -> None:
        amount = Decimal(str(amount_usd))
        bal = self.get_or_create_balance(user_id, db)
        bal.balance_usd += amount
        bal.total_deposited_usd += amount
        bal.updated_at = datetime.now(UTC)

        txn = AICreditTransaction(
            user_id=user_id,
            type="bonus",
            amount_usd=amount,
            description=f"Bonus: {reason}",
        )
        db.add(txn)
        db.commit()

    def get_transactions(self, user_id: uuid.UUID, db: Session, limit: int = 50) -> list:
        return (
            db.query(AICreditTransaction)
            .filter(AICreditTransaction.user_id == user_id)
            .order_by(AICreditTransaction.created_at.desc())
            .limit(limit)
            .all()
        )


credit_service = CreditService()
