from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security_jwt import decode_token
from app.services.encryption_service import EncryptionService, encryption_service_from_env
from app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def get_encryption_service() -> EncryptionService:
    s = get_settings()
    svc = encryption_service_from_env(s.encryption_master_key_b64)
    if svc is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shifrlash sozlanmagan: ENCRYPTION_MASTER_KEY_B64 (32 bayt base64)",
        )
    return svc


def get_current_user(
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Bearer token kerak")
    try:
        uid = decode_token(creds.credentials)
    except ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token muddati tugagan")
    except (InvalidTokenError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Noto‘g‘ri token")
    user = db.get(User, uid)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi yoki nofaol")
    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    try:
        uid = decode_token(creds.credentials)
    except (ExpiredSignatureError, InvalidTokenError, ValueError):
        return None
    user = db.get(User, uid)
    if not user or not user.is_active:
        return None
    return user
