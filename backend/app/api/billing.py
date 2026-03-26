"""Billing API: tariflar, obuna, to'lov, kredit, referral."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import Role, get_current_user, require_role
from app.models import (
    AICreditBalance,
    AICreditTransaction,
    PaymentRecord,
    Plan,
    User,
    UserSubscription,
)
from app.services.credit_service import CREDIT_PACKAGES, credit_service
from app.services.payment_service import (
    click_payment,
    payme_payment,
    stripe_payment,
    _downgrade_to_free,
)
from app.services.quota_service import quota_service
from app.services.referral_service import referral_service

router = APIRouter(prefix="/billing", tags=["billing"])

settings = get_settings()


# ─── PLANS ────────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans(db: Session = Depends(get_db)) -> list[dict]:
    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.sort_order).all()
    result = []
    for p in plans:
        result.append({
            "id": p.id,
            "name": p.name,
            "price_usd": float(p.price_usd),
            "price_uzs": p.price_uzs,
            "billing_period": p.billing_period,
            "limits": p.limits,
            "features_list": p.features_list or [],
            "is_public": p.is_public,
        })
    return result


# ─── SUBSCRIPTION & USAGE ────────────────────────────────────────────────────

@router.get("/subscription")
def get_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    usage = quota_service.get_usage_stats(user.id, db)
    sub = quota_service.get_subscription(user.id, db)
    plan = db.get(Plan, sub.plan_id)
    bal = db.get(AICreditBalance, user.id)
    return {
        **usage,
        "plan_name": plan.name if plan else sub.plan_id,
        "price_usd": float(plan.price_usd) if plan else 0,
        "ai_credit_balance_usd": float(bal.balance_usd) if bal else 0.0,
    }


# ─── CHECKOUT ─────────────────────────────────────────────────────────────────

class CheckoutIn(BaseModel):
    plan_id: str


@router.post("/checkout/stripe")
def checkout_stripe(
    body: CheckoutIn,
    user: User = Depends(require_role(Role.OPERATOR)),
    db: Session = Depends(get_db),
) -> dict:
    if body.plan_id not in ("pro", "team", "enterprise"):
        raise HTTPException(400, "Noto'g'ri tarif ID")
    if not settings.stripe_secret_key:
        raise HTTPException(503, "Stripe sozlanmagan")
    url = stripe_payment.create_checkout(user.id, body.plan_id, db)
    return {"checkout_url": url}


@router.post("/checkout/click")
def checkout_click(
    body: CheckoutIn,
    user: User = Depends(require_role(Role.OPERATOR)),
    db: Session = Depends(get_db),
) -> dict:
    plan = db.get(Plan, body.plan_id)
    if not plan or plan.price_usd == 0:
        raise HTTPException(400, "Noto'g'ri tarif")
    if not settings.click_service_id:
        raise HTTPException(503, "Click sozlanmagan")
    amount_uzs = plan.price_uzs or int(float(plan.price_usd) * 12800)
    url = click_payment.create_invoice_url(user.id, body.plan_id, amount_uzs, db)
    return {"payment_url": url}


@router.post("/checkout/payme")
def checkout_payme(
    body: CheckoutIn,
    user: User = Depends(require_role(Role.OPERATOR)),
    db: Session = Depends(get_db),
) -> dict:
    plan = db.get(Plan, body.plan_id)
    if not plan or plan.price_usd == 0:
        raise HTTPException(400, "Noto'g'ri tarif")
    if not settings.payme_merchant_id:
        raise HTTPException(503, "Payme sozlanmagan")
    amount_uzs = plan.price_uzs or int(float(plan.price_usd) * 12800)
    url = payme_payment.create_invoice_url(user.id, body.plan_id, amount_uzs, db)
    return {"payment_url": url}


# ─── CREDIT TOPUP ─────────────────────────────────────────────────────────────

class CreditCheckoutIn(BaseModel):
    package_id: str
    provider: str = "click"


@router.post("/checkout/credit")
def checkout_credit(
    body: CreditCheckoutIn,
    user: User = Depends(require_role(Role.OPERATOR)),
    db: Session = Depends(get_db),
) -> dict:
    pkg = next((p for p in CREDIT_PACKAGES if p["id"] == body.package_id), None)
    if not pkg:
        raise HTTPException(400, "Noto'g'ri paket")

    amount_uzs_map = {
        "credit_5": settings.credit_5_price_uzs,
        "credit_20": settings.credit_20_price_uzs,
        "credit_50": settings.credit_50_price_uzs,
    }
    amount_uzs = amount_uzs_map.get(body.package_id, int(pkg["amount_usd"] * 12800))

    if body.provider == "click":
        if not settings.click_service_id:
            raise HTTPException(503, "Click sozlanmagan")
        url = click_payment.create_invoice_url(user.id, f"credit_{pkg['amount_usd']}", amount_uzs, db)
    elif body.provider == "payme":
        if not settings.payme_merchant_id:
            raise HTTPException(503, "Payme sozlanmagan")
        url = payme_payment.create_invoice_url(user.id, f"credit_{pkg['amount_usd']}", amount_uzs, db)
    elif body.provider == "stripe":
        raise HTTPException(400, "Kredit uchun Click yoki Payme tanlang")
    else:
        raise HTTPException(400, "Noma'lum provider")

    return {"payment_url": url, "amount_usd": pkg["amount_usd"], "amount_uzs": amount_uzs}


@router.get("/credit-packages")
def list_credit_packages() -> list[dict]:
    settings_ = get_settings()
    return [
        {
            "id": p["id"],
            "amount_usd": p["amount_usd"],
            "label": p["label"],
            "price_uzs": {
                "credit_5": settings_.credit_5_price_uzs,
                "credit_20": settings_.credit_20_price_uzs,
                "credit_50": settings_.credit_50_price_uzs,
            }.get(p["id"], int(p["amount_usd"] * 12800)),
        }
        for p in CREDIT_PACKAGES
    ]


@router.get("/credits")
def get_credits(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    bal = db.get(AICreditBalance, user.id)
    txns = (
        db.query(AICreditTransaction)
        .filter(AICreditTransaction.user_id == user.id)
        .order_by(AICreditTransaction.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "balance_usd": float(bal.balance_usd) if bal else 0.0,
        "total_deposited_usd": float(bal.total_deposited_usd) if bal else 0.0,
        "total_spent_usd": float(bal.total_spent_usd) if bal else 0.0,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.type,
                "amount_usd": float(t.amount_usd),
                "description": t.description,
                "provider": t.provider,
                "tokens_used": t.tokens_used,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in txns
        ],
    }


# ─── WEBHOOKS ─────────────────────────────────────────────────────────────────

@router.post("/webhook/stripe")
async def webhook_stripe(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        return stripe_payment.handle_webhook(payload, sig, db)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/webhook/click")
def webhook_click(
    data: dict = Body(...),
    db: Session = Depends(get_db),
) -> dict:
    return click_payment.handle_webhook(data, db)


@router.post("/webhook/payme")
def webhook_payme(
    body: dict = Body(...),
    db: Session = Depends(get_db),
) -> dict:
    method = body.get("method", "")
    params = body.get("params", {})
    result = payme_payment.handle_rpc(method, params, db)
    return {"jsonrpc": "2.0", "id": body.get("id"), "result": result}


# ─── SUBSCRIPTION MANAGEMENT ─────────────────────────────────────────────────

@router.post("/cancel")
def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user.id).first()
    if not sub or sub.plan_id == "free":
        raise HTTPException(400, "Bekor qilinadigan obuna yo'q")
    sub.cancel_at_period_end = True
    db.commit()
    return {"message": "Obuna davr oxirida bekor qilinadi", "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None}


@router.post("/reactivate")
def reactivate_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user.id).first()
    if not sub:
        raise HTTPException(404, "Obuna topilmadi")
    sub.cancel_at_period_end = False
    sub.cancelled_at = None
    db.commit()
    return {"message": "Obuna qayta faollashtirildi"}


# ─── INVOICES ─────────────────────────────────────────────────────────────────

@router.get("/invoices")
def list_invoices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    records = (
        db.query(PaymentRecord)
        .filter(PaymentRecord.user_id == user.id)
        .order_by(PaymentRecord.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "plan_id": r.plan_id,
            "provider": r.provider,
            "amount_usd": float(r.amount_usd),
            "amount_local": r.amount_local,
            "currency_local": r.currency_local,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "paid_at": r.paid_at.isoformat() if r.paid_at else None,
        }
        for r in records
    ]


# ─── REFERRAL ─────────────────────────────────────────────────────────────────

@router.get("/referral")
def get_referral(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stats = referral_service.get_stats(user.id, db)
    app_url = settings.app_url or "https://devagent.z7.uz"
    bot_username = "devOpsmkbot"
    return {
        **stats,
        "bot_url": f"https://t.me/{bot_username}?start=ref_{stats['code']}",
        "web_url": f"{app_url}?ref={stats['code']}",
        "reward_referrer_usd": settings.referral_reward_usd,
        "reward_referred_days": settings.referral_trial_days,
    }


# ─── ONBOARDING ───────────────────────────────────────────────────────────────

@router.get("/onboarding")
def get_onboarding(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.models import UserOnboarding
    ob = db.get(UserOnboarding, user.id)
    if not ob:
        ob = UserOnboarding(user_id=user.id, step=0)
        db.add(ob)
        db.commit()
        db.refresh(ob)
    return {
        "step": ob.step,
        "completed_at": ob.completed_at.isoformat() if ob.completed_at else None,
        "steps_data": ob.steps_data,
    }


class OnboardingUpdateIn(BaseModel):
    step: int
    steps_data: dict | None = None


@router.patch("/onboarding")
def update_onboarding(
    body: OnboardingUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.models import UserOnboarding
    ob = db.get(UserOnboarding, user.id)
    if not ob:
        ob = UserOnboarding(user_id=user.id, step=0)
        db.add(ob)
    ob.step = body.step
    if body.steps_data:
        ob.steps_data = {**(ob.steps_data or {}), **body.steps_data}
    if body.step >= 4 and not ob.completed_at:
        ob.completed_at = datetime.now(UTC)
    db.commit()
    return {"step": ob.step, "completed_at": ob.completed_at.isoformat() if ob.completed_at else None}
