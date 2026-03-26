"""Telegram bot uchun ichki endpointlar (faqat `X-Internal-Secret`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Server, User
from app.schemas import ServerCreate, ServerRead

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_internal(request: Request) -> None:
    s = get_settings()
    sec = (s.api_internal_secret or "").strip()
    if not sec or request.headers.get("X-Internal-Secret") != sec:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="X-Internal-Secret noto‘g‘ri")


@router.get("/servers", response_model=list[ServerRead])
def internal_list_servers(
    request: Request,
    db: Session = Depends(get_db),
) -> list[Server]:
    _require_internal(request)
    return db.query(Server).order_by(Server.name).all()


@router.post("/servers", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
def internal_create_server(
    payload: ServerCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> Server:
    _require_internal(request)
    existing = db.query(Server).filter(Server.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server name already exists")
    row = Server(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/user-subscription/{telegram_id}")
def internal_user_subscription(
    telegram_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    _require_internal(request)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(404, "User topilmadi")
    from app.services.quota_service import quota_service
    stats = quota_service.get_usage_stats(user.id, db)
    sub = quota_service.get_subscription(user.id, db)
    from app.models import AICreditBalance, Plan
    plan = db.get(Plan, sub.plan_id)
    bal = db.get(AICreditBalance, user.id)
    return {
        **stats,
        "plan_name": plan.name if plan else sub.plan_id,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "ai_credit_balance_usd": float(bal.balance_usd) if bal else 0.0,
    }


@router.get("/user-referral/{telegram_id}")
def internal_user_referral(
    telegram_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    _require_internal(request)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(404, "User topilmadi")
    from app.config import get_settings as _gs
    from app.services.referral_service import referral_service
    stats = referral_service.get_stats(user.id, db)
    settings = _gs()
    app_url = settings.app_url or "https://devagent.z7.uz"
    bot_username = "devOpsmkbot"
    return {
        **stats,
        "bot_url": f"https://t.me/{bot_username}?start=ref_{stats['code']}",
        "web_url": f"{app_url}?ref={stats['code']}",
        "reward_referrer_usd": settings.referral_reward_usd,
        "reward_referred_days": settings.referral_trial_days,
    }


@router.get("/user-credits/{telegram_id}")
def internal_user_credits(
    telegram_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    _require_internal(request)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(404, "User topilmadi")
    from app.models import AICreditBalance
    bal = db.get(AICreditBalance, user.id)
    return {
        "balance_usd": float(bal.balance_usd) if bal else 0.0,
        "total_deposited_usd": float(bal.total_deposited_usd) if bal else 0.0,
        "total_spent_usd": float(bal.total_spent_usd) if bal else 0.0,
    }
