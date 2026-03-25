from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import Role
from app.models import User
from app.security_jwt import create_access_token
from app.services.telegram_auth import verify_telegram_login

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/telegram", response_model=TokenResponse)
def login_telegram(
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    for key in ("id", "hash", "auth_date"):
        if key not in body:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Maydon kerak: {key}")
    if not settings.jwt_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET sozlanmagan",
        )
    if not settings.telegram_bot_token:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TELEGRAM_BOT_TOKEN sozlanmagan",
        )
    if not verify_telegram_login(body, settings.telegram_bot_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Telegram tekshiruvi muvaffaqiyatsiz")

    tid = int(body["id"])
    user = db.query(User).filter(User.telegram_id == tid).first()
    owner_ids = settings.admin_telegram_ids_list
    if not user:
        initial_role = Role.OWNER.value if tid in owner_ids else Role.OPERATOR.value
        user = User(
            telegram_id=tid,
            username=body.get("username") if isinstance(body.get("username"), str) else None,
            first_name=body.get("first_name") if isinstance(body.get("first_name"), str) else None,
            is_active=True,
            role=initial_role,
        )
        db.add(user)
    elif not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Hisob nofaol")
    else:
        if tid in owner_ids and user.role not in (Role.OWNER.value, Role.ADMIN.value):
            user.role = Role.OWNER.value
    user.last_seen_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


class BotLoginIn(BaseModel):
    telegram_id: int
    internal_secret: str


class BotLoginOut(BaseModel):
    access_token: str
    user_id: str
    is_new: bool
    is_active: bool


@router.post("/bot-login", response_model=BotLoginOut)
def bot_login(body: BotLoginIn, db: Session = Depends(get_db)) -> BotLoginOut:
    """Telegram bot uchun ichki maxfiy kalit bilan JWT (Web UI token formati bilan mos)."""
    settings = get_settings()
    if not settings.jwt_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET sozlanmagan",
        )
    if not settings.api_internal_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_INTERNAL_SECRET sozlanmagan",
        )
    a, b = body.internal_secret, settings.api_internal_secret
    if len(a) != len(b) or not secrets.compare_digest(a, b):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")

    user = db.query(User).filter(User.telegram_id == body.telegram_id).first()
    owner_ids = settings.admin_telegram_ids_list
    is_new = False
    if not user:
        initial_role = Role.OWNER.value if body.telegram_id in owner_ids else Role.OPERATOR.value
        user = User(telegram_id=body.telegram_id, is_active=True, role=initial_role)
        db.add(user)
        is_new = True
    elif not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Hisob nofaol")
    else:
        if body.telegram_id in owner_ids and user.role not in (Role.OWNER.value, Role.ADMIN.value):
            user.role = Role.OWNER.value
    user.last_seen_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, expire_minutes=60 * 24 * 7)
    return BotLoginOut(
        access_token=token,
        user_id=str(user.id),
        is_new=is_new,
        is_active=user.is_active,
    )
