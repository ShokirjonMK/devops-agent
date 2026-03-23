from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
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
    if not user:
        user = User(
            telegram_id=tid,
            username=body.get("username") if isinstance(body.get("username"), str) else None,
            first_name=body.get("first_name") if isinstance(body.get("first_name"), str) else None,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Hisob nofaol")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
