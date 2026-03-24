from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_encryption_service
from app.models import CredentialVault, User
from app.services.encryption_service import EncryptionService

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    credential_type: str
    created_at: datetime | None


class CredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    credential_type: str = Field(..., min_length=1, max_length=32)
    secret: str = Field(..., min_length=1, max_length=100_000)


@router.get("", response_model=list[CredentialMeta])
def list_credentials(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CredentialVault]:
    return (
        db.query(CredentialVault)
        .filter(CredentialVault.user_id == user.id)
        .order_by(CredentialVault.created_at.desc())
        .all()
    )


@router.post("", response_model=CredentialMeta, status_code=status.HTTP_201_CREATED)
def create_credential(
    payload: CredentialCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    enc: EncryptionService = Depends(get_encryption_service),
) -> CredentialVault:
    exists = (
        db.query(CredentialVault)
        .filter(
            CredentialVault.user_id == user.id,
            CredentialVault.credential_type == payload.credential_type,
            CredentialVault.name == payload.name,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Bu nom allaqachon mavjud")
    ctx = f"vault:{user.id}:{payload.credential_type}:{payload.name}"
    blob = enc.encrypt(payload.secret, ctx)
    row = CredentialVault(
        user_id=user.id,
        name=payload.name,
        credential_type=payload.credential_type,
        cipher_text=blob.ciphertext,
        iv=blob.iv,
        tag=blob.tag,
        salt=blob.salt,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
