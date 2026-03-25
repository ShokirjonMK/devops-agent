"""Foydalanuvchi AI kalitlarini credential_vault dan olish (shifrdan chiqarish)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import case
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CredentialVault
from app.services.encryption_service import EncryptedBlob, EncryptionService, build_encryption_service


def _encryption_or_none() -> EncryptionService | None:
    s = get_settings()
    try:
        return build_encryption_service(
            master_encryption_key_hex=s.master_encryption_key,
            encryption_master_key_b64=s.encryption_master_key_b64,
        )
    except ValueError:
        return None


def _parse_payload(plaintext: str) -> dict[str, Any]:
    try:
        data = json.loads(plaintext)
        if isinstance(data, dict) and "api_key" in data:
            return data
    except json.JSONDecodeError:
        pass
    return {"api_key": plaintext.strip(), "base_url": None, "model": None}


def load_user_ai_credential(
    db: Session,
    owner_user_id: uuid.UUID,
    credential_type: str,
) -> dict[str, Any] | None:
    """
    credential_type: ai_openai | ai_anthropic
    Avvalo name=='default', keyin eng yangi yozuv.
    """
    enc = _encryption_or_none()
    if enc is None:
        return None
    q = (
        db.query(CredentialVault)
        .filter(
            CredentialVault.user_id == owner_user_id,
            CredentialVault.credential_type == credential_type,
        )
        .order_by(
            case((CredentialVault.name == "default", 0), else_=1),
            CredentialVault.created_at.desc(),
        )
    )
    row = q.first()
    if not row:
        return None
    blob = EncryptedBlob.from_storage(row.cipher_text, row.iv, row.salt, row.tag)
    ctx = f"vault:{owner_user_id}:{row.credential_type}:{row.name}"
    try:
        plain = enc.decrypt(blob, ctx)
    except Exception:
        return None
    return _parse_payload(plain)


def user_openai_config(db: Session, owner_user_id: uuid.UUID) -> dict[str, Any] | None:
    return load_user_ai_credential(db, owner_user_id, "ai_openai")


def user_anthropic_config(db: Session, owner_user_id: uuid.UUID) -> dict[str, Any] | None:
    return load_user_ai_credential(db, owner_user_id, "ai_anthropic")
