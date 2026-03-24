"""Foydalanuvchi AI kalitlari (credential_vault: ai_openai, ai_anthropic)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_encryption_service
from app.models import CredentialVault, User
from app.services.encryption_service import EncryptionService

AI_TYPES = frozenset({"ai_openai", "ai_anthropic"})

router = APIRouter(prefix="/ai-keys", tags=["ai-keys"])


class AiKeyMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    provider: Literal["openai", "anthropic"]
    created_at: datetime | None


class AiKeyCreate(BaseModel):
    name: str = Field(default="default", min_length=1, max_length=128)
    provider: Literal["openai", "anthropic"]
    api_key: str = Field(..., min_length=1, max_length=8192)
    base_url: str | None = Field(default=None, max_length=1024)
    model: str | None = Field(default=None, max_length=256)


def _type_for_provider(p: str) -> str:
    return "ai_openai" if p == "openai" else "ai_anthropic"


def _meta_from_row(row: CredentialVault) -> AiKeyMeta:
    prov = "openai" if row.credential_type == "ai_openai" else "anthropic"
    return AiKeyMeta(
        id=row.id,
        name=row.name,
        provider=prov,  # type: ignore[arg-type]
        created_at=row.created_at,
    )


@router.get("", response_model=list[AiKeyMeta])
def list_ai_keys(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AiKeyMeta]:
    rows = (
        db.query(CredentialVault)
        .filter(
            CredentialVault.user_id == user.id,
            CredentialVault.credential_type.in_(AI_TYPES),
        )
        .order_by(CredentialVault.created_at.desc())
        .all()
    )
    return [_meta_from_row(r) for r in rows]


@router.post("", response_model=AiKeyMeta, status_code=status.HTTP_201_CREATED)
def create_ai_key(
    payload: AiKeyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    enc: EncryptionService = Depends(get_encryption_service),
) -> AiKeyMeta:
    ctype = _type_for_provider(payload.provider)
    exists = (
        db.query(CredentialVault)
        .filter(
            CredentialVault.user_id == user.id,
            CredentialVault.credential_type == ctype,
            CredentialVault.name == payload.name,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Bu nom va provayder uchun yozuv allaqachon bor")
    secret_obj = {
        "api_key": payload.api_key.strip(),
        "base_url": payload.base_url.strip() if payload.base_url else None,
        "model": payload.model.strip() if payload.model else None,
    }
    secret = json.dumps(secret_obj, ensure_ascii=False)
    ctx = f"vault:{user.id}:{ctype}:{payload.name}"
    blob = enc.encrypt(secret, ctx)
    row = CredentialVault(
        user_id=user.id,
        name=payload.name,
        credential_type=ctype,
        cipher_text=blob.ciphertext,
        iv=blob.iv,
        tag=blob.tag,
        salt=blob.salt,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _meta_from_row(row)


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
def delete_ai_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    row = (
        db.query(CredentialVault)
        .filter(
            CredentialVault.id == key_id,
            CredentialVault.user_id == user.id,
            CredentialVault.credential_type.in_(AI_TYPES),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Kalit topilmadi")
    db.delete(row)
    db.commit()
    return {"ok": True}
