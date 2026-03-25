"""JWT yaratish va tekshirish (access token)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings


def create_access_token(user_id: uuid.UUID, *, expire_minutes: int | None = None) -> str:
    s = get_settings()
    if not s.jwt_secret:
        raise RuntimeError("JWT_SECRET sozlanmagan")
    now = datetime.now(UTC)
    mins = expire_minutes if expire_minutes is not None else s.jwt_expire_minutes
    exp = now + timedelta(minutes=mins)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> uuid.UUID:
    s = get_settings()
    if not s.jwt_secret:
        raise RuntimeError("JWT_SECRET sozlanmagan")
    payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    sub = payload.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("missing sub")
    return uuid.UUID(str(sub))
