from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security_jwt import decode_token
from app.services.encryption_service import EncryptionService, build_encryption_service
from app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def _internal_secret_ok(request: Request) -> bool:
    s = get_settings()
    sec = (s.api_internal_secret or "").strip()
    if not sec:
        return False
    return request.headers.get("X-Internal-Secret") == sec


def _strict_internal_mode() -> bool:
    return bool((get_settings().api_internal_secret or "").strip())


@dataclass(frozen=True)
class TaskAccess:
    """Kim so‘rayapti: ichki xizmat (bot) yoki JWT foydalanuvchi."""

    user: User | None
    is_internal: bool
    allow_anonymous: bool


def get_task_access(
    request: Request,
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TaskAccess:
    if _internal_secret_ok(request):
        return TaskAccess(user=None, is_internal=True, allow_anonymous=False)
    if not _strict_internal_mode():
        if creds and creds.scheme.lower() == "bearer":
            try:
                uid = decode_token(creds.credentials)
            except (ExpiredSignatureError, InvalidTokenError, ValueError):
                return TaskAccess(user=None, is_internal=False, allow_anonymous=True)
            u = db.get(User, uid)
            if not u or not u.is_active:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi yoki nofaol")
            return TaskAccess(user=u, is_internal=False, allow_anonymous=False)
        return TaskAccess(user=None, is_internal=False, allow_anonymous=True)
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Bearer yoki X-Internal-Secret kerak")
    try:
        uid = decode_token(creds.credentials)
    except ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token muddati tugagan")
    except (InvalidTokenError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Noto‘g‘ri token")
    u = db.get(User, uid)
    if not u or not u.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi yoki nofaol")
    return TaskAccess(user=u, is_internal=False, allow_anonymous=False)


def get_task_submit_access(
    request: Request,
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TaskAccess:
    if _internal_secret_ok(request):
        return TaskAccess(user=None, is_internal=True, allow_anonymous=False)
    if not _strict_internal_mode():
        if creds and creds.scheme.lower() == "bearer":
            try:
                uid = decode_token(creds.credentials)
            except (ExpiredSignatureError, InvalidTokenError, ValueError):
                return TaskAccess(user=None, is_internal=False, allow_anonymous=True)
            u = db.get(User, uid)
            if not u or not u.is_active:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi yoki nofaol")
            ur = ROLE_HIERARCHY.get((u.role or Role.VIEWER.value).lower(), 0)
            if ur < ROLE_HIERARCHY[Role.OPERATOR.value]:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Ruxsat yetarli emas: kerak operator",
                )
            return TaskAccess(user=u, is_internal=False, allow_anonymous=False)
        return TaskAccess(user=None, is_internal=False, allow_anonymous=True)
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Bearer yoki X-Internal-Secret kerak")
    try:
        uid = decode_token(creds.credentials)
    except ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token muddati tugagan")
    except (InvalidTokenError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Noto‘g‘ri token")
    u = db.get(User, uid)
    if not u or not u.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi yoki nofaol")
    ur = ROLE_HIERARCHY.get((u.role or Role.VIEWER.value).lower(), 0)
    if ur < ROLE_HIERARCHY[Role.OPERATOR.value]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Ruxsat yetarli emas: kerak operator")
    return TaskAccess(user=u, is_internal=False, allow_anonymous=False)


def get_encryption_service() -> EncryptionService:
    s = get_settings()
    try:
        svc = build_encryption_service(
            master_encryption_key_hex=s.master_encryption_key,
            encryption_master_key_b64=s.encryption_master_key_b64,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    if svc is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shifrlash sozlanmagan: MASTER_ENCRYPTION_KEY (64 hex) yoki ENCRYPTION_MASTER_KEY_B64",
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


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


ROLE_HIERARCHY: dict[str, int] = {
    Role.VIEWER.value: 0,
    Role.OPERATOR.value: 1,
    Role.ADMIN.value: 2,
    Role.OWNER.value: 3,
}


def require_role(min_role: Role):
    """Minimal rol tekshiruvi (JWT bilan)."""

    def checker(user: User = Depends(get_current_user)) -> User:
        raw = (user.role or Role.VIEWER.value).lower()
        ur = ROLE_HIERARCHY.get(raw, 0)
        need = ROLE_HIERARCHY.get(min_role.value, 0)
        if ur < need:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Ruxsat yetarli emas: kerak {min_role.value}",
            )
        return user

    return checker
