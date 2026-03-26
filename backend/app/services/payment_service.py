"""Ko'p provayderli to'lov: Stripe + Click + Payme."""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode

import httpx
import structlog
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import PaymentRecord, Plan, UserSubscription
from app.services.credit_service import credit_service
from app.services.referral_service import referral_service

log = structlog.get_logger("payment_service")


def _activate_subscription(user_id: uuid.UUID, plan_id: str, provider: str,
                             external_id: str, db: Session) -> None:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if not sub:
        sub = UserSubscription(user_id=user_id)
        db.add(sub)
    now = datetime.now(UTC)
    sub.plan_id = plan_id
    sub.status = "active"
    sub.payment_provider = provider
    sub.external_subscription_id = external_id
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=30)
    sub.cancel_at_period_end = False
    sub.cancelled_at = None
    db.commit()
    # Referral mukofoti — birinchi to'lovda
    settings = get_settings()
    referral_service.reward_referrer_on_payment(user_id, settings.referral_reward_usd, db)
    log.info("subscription_activated", user_id=str(user_id), plan=plan_id, provider=provider)


def _downgrade_to_free(user_id: uuid.UUID, db: Session) -> None:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if sub:
        sub.plan_id = "free"
        sub.status = "active"
        sub.external_subscription_id = None
        db.commit()
    log.info("downgraded_to_free", user_id=str(user_id))


class StripePaymentService:

    def create_checkout(self, user_id: uuid.UUID, plan_id: str, db: Session) -> str:
        settings = get_settings()
        if not settings.stripe_secret_key:
            raise ValueError("STRIPE_SECRET_KEY sozlanmagan")

        try:
            import stripe  # type: ignore
            stripe.api_key = settings.stripe_secret_key
        except ImportError:
            raise ValueError("stripe kutubxonasi o'rnatilmagan: pip install stripe")

        price_map = {
            "pro": settings.stripe_price_pro_monthly,
            "team": settings.stripe_price_team_monthly,
        }
        price_id = price_map.get(plan_id)
        if not price_id:
            raise ValueError(f"Stripe price ID topilmadi: {plan_id}")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            metadata={"user_id": str(user_id), "plan_id": plan_id},
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.app_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app_url}/upgrade?cancelled=1",
            allow_promotion_codes=True,
        )
        return session.url

    def handle_webhook(self, payload: bytes, sig_header: str, db: Session) -> dict:
        settings = get_settings()
        try:
            import stripe  # type: ignore
            stripe.api_key = settings.stripe_secret_key
            event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
        except Exception as e:
            raise ValueError(f"Webhook xatosi: {e}")

        if event["type"] == "checkout.session.completed":
            obj = event["data"]["object"]
            user_id = uuid.UUID(obj["metadata"]["user_id"])
            plan_id = obj["metadata"]["plan_id"]
            sub_id = obj.get("subscription", "")
            plan = db.get(Plan, plan_id)
            amount = Decimal(str((plan.price_usd if plan else 15)))
            self._save_payment(user_id, plan_id, "stripe", float(amount), sub_id, db)
            _activate_subscription(user_id, plan_id, "stripe", sub_id, db)

        elif event["type"] in ("invoice.payment_succeeded",):
            obj = event["data"]["object"]
            meta = obj.get("subscription_details", {}).get("metadata", {})
            if meta.get("user_id"):
                user_id = uuid.UUID(meta["user_id"])
                plan_id = meta.get("plan_id", "pro")
                sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
                if sub:
                    sub.current_period_end = datetime.now(UTC) + timedelta(days=30)
                    db.commit()

        elif event["type"] == "customer.subscription.deleted":
            obj = event["data"]["object"]
            meta = obj.get("metadata", {})
            if meta.get("user_id"):
                _downgrade_to_free(uuid.UUID(meta["user_id"]), db)

        return {"received": True}

    def _save_payment(self, user_id, plan_id, provider, amount, external_id, db):
        rec = PaymentRecord(
            user_id=user_id, plan_id=plan_id, provider=provider,
            amount_usd=Decimal(str(amount)), status="paid",
            external_id=external_id, paid_at=datetime.now(UTC),
        )
        db.add(rec)
        db.commit()


class ClickPaymentService:

    def create_invoice_url(self, user_id: uuid.UUID, plan_id: str,
                            amount_uzs: int, db: Session) -> str:
        settings = get_settings()
        if not settings.click_service_id:
            raise ValueError("CLICK_SERVICE_ID sozlanmagan")

        params = {
            "service_id": settings.click_service_id,
            "merchant_id": settings.click_merchant_id,
            "amount": amount_uzs,
            "transaction_param": str(user_id),
            "return_url": f"{settings.app_url}/billing/success",
        }
        rec = PaymentRecord(
            user_id=user_id, plan_id=plan_id, provider="click",
            amount_usd=Decimal(str(amount_uzs / 12800)),
            amount_local=amount_uzs, currency_local="UZS", status="pending",
        )
        db.add(rec)
        db.commit()
        return f"https://my.click.uz/services/pay?{urlencode(params)}"

    def handle_webhook(self, data: dict, db: Session) -> dict:
        settings = get_settings()
        action = data.get("action")
        sign_time = data.get("sign_time", "")
        service_id = data.get("service_id", "")
        click_trans_id = str(data.get("click_trans_id", ""))
        merchant_trans_id = data.get("merchant_trans_id", "")  # user_id
        amount = data.get("amount", 0)
        sign_string = data.get("sign_string", "")

        expected = hashlib.md5(
            f"{click_trans_id}{service_id}{settings.click_secret_key}{merchant_trans_id}{amount}{action}{sign_time}".encode()
        ).hexdigest()

        if not hmac.compare_digest(expected, sign_string):
            return {"error": -1, "error_note": "SIGN CHECK FAILED"}

        if action == 0:  # prepare
            return {"click_trans_id": click_trans_id, "merchant_trans_id": merchant_trans_id,
                    "merchant_prepare_id": click_trans_id, "error": 0, "error_note": "Success"}

        if action == 1:  # complete
            try:
                user_id = uuid.UUID(merchant_trans_id)
                # Find pending payment
                rec = (db.query(PaymentRecord)
                       .filter(PaymentRecord.user_id == user_id, PaymentRecord.provider == "click",
                               PaymentRecord.status == "pending")
                       .order_by(PaymentRecord.created_at.desc()).first())
                if rec:
                    rec.status = "paid"
                    rec.external_id = click_trans_id
                    rec.paid_at = datetime.now(UTC)
                    db.commit()
                    _activate_subscription(user_id, rec.plan_id or "pro", "click", click_trans_id, db)
            except Exception as e:
                log.error("click_webhook_error", error=str(e))
            return {"click_trans_id": click_trans_id, "merchant_trans_id": merchant_trans_id,
                    "merchant_confirm_id": click_trans_id, "error": 0, "error_note": "Success"}

        return {"error": -3, "error_note": "Action not found"}


class PaymePaymentService:

    def create_invoice_url(self, user_id: uuid.UUID, plan_id: str,
                            amount_uzs: int, db: Session) -> str:
        import base64
        settings = get_settings()
        if not settings.payme_merchant_id:
            raise ValueError("PAYME_MERCHANT_ID sozlanmagan")

        rec = PaymentRecord(
            user_id=user_id, plan_id=plan_id, provider="payme",
            amount_usd=Decimal(str(amount_uzs / 12800)),
            amount_local=amount_uzs, currency_local="UZS", status="pending",
        )
        db.add(rec)
        db.commit()

        params = json.dumps({
            "m": settings.payme_merchant_id,
            "ac.user_id": str(user_id),
            "ac.plan_id": plan_id,
            "a": amount_uzs * 100,
            "l": "uz",
            "c": f"{settings.app_url}/billing/success",
        })
        encoded = base64.b64encode(params.encode()).decode()
        host = "test.paycom.uz" if settings.payme_test_mode else "checkout.paycom.uz"
        return f"https://{host}/{encoded}"

    def handle_rpc(self, method: str, params: dict, db: Session) -> dict:
        settings = get_settings()
        if method == "CheckPerformTransaction":
            user_id_str = params.get("account", {}).get("user_id")
            if not user_id_str:
                return {"error": {"code": -31050, "message": "User topilmadi"}}
            return {"allow": True}

        if method in ("CreateTransaction", "PerformTransaction"):
            user_id_str = params.get("account", {}).get("user_id")
            plan_id = params.get("account", {}).get("plan_id", "pro")
            trans_id = params.get("id", "")
            amount = params.get("amount", 0)
            try:
                user_id = uuid.UUID(user_id_str)
                rec = (db.query(PaymentRecord)
                       .filter(PaymentRecord.user_id == user_id, PaymentRecord.provider == "payme",
                               PaymentRecord.status == "pending")
                       .order_by(PaymentRecord.created_at.desc()).first())
                if method == "PerformTransaction" and rec:
                    rec.status = "paid"
                    rec.external_id = trans_id
                    rec.paid_at = datetime.now(UTC)
                    db.commit()
                    _activate_subscription(user_id, plan_id, "payme", trans_id, db)
            except Exception as e:
                log.error("payme_rpc_error", error=str(e))
            return {"transaction": trans_id, "perform_time": int(datetime.now(UTC).timestamp() * 1000), "state": 2}

        if method == "CancelTransaction":
            trans_id = params.get("id", "")
            rec = db.query(PaymentRecord).filter(PaymentRecord.external_id == trans_id).first()
            if rec:
                rec.status = "cancelled"
                db.commit()
            return {"transaction": trans_id, "cancel_time": int(datetime.now(UTC).timestamp() * 1000), "state": -1}

        return {"error": {"code": -32601, "message": "Method not found"}}


stripe_payment = StripePaymentService()
click_payment = ClickPaymentService()
payme_payment = PaymePaymentService()
