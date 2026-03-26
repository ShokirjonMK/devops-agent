"""Ko‘p provayderli AI tokenlar: `ai_token_configs` + `credential_vault`. Token javobda qaytmaydi."""

from __future__ import annotations

import json
import time
import uuid
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Role, get_current_user, get_encryption_service, require_role
from app.models import AiTokenConfig, CredentialVault, User
from app.services.encryption_service import EncryptionService
from app.services.llm_router import LLMRouter, PROVIDER_LIST
from app.services.platform_audit import log_platform_audit

log = structlog.get_logger()
router = APIRouter(prefix="/ai-tokens", tags=["ai-tokens"])

CREDENTIAL_TYPE = "ai_token"


class TokenListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    name: str
    model_override: str | None
    base_url: str | None
    is_active: bool
    is_default: bool
    monthly_budget_usd: Decimal | None
    usage_this_month_usd: Decimal
    last_used_at: str | None
    masked_hint: str = Field(default="●●●●")


class TokenCreateRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=32)
    name: str = Field(..., min_length=1, max_length=128)
    token_value: str = Field(..., min_length=1, max_length=16384)
    base_url: str | None = None
    model_override: str | None = None
    monthly_budget_usd: Decimal | None = None
    is_default: bool = False


class TokenPatchRequest(BaseModel):
    is_active: bool | None = None
    is_default: bool | None = None
    monthly_budget_usd: Decimal | None = None
    model_override: str | None = None
    base_url: str | None = None


class TestResult(BaseModel):
    success: bool
    latency_ms: int
    model_used: str
    detail: str | None = None


def _secret_payload(req: TokenCreateRequest) -> str:
    return json.dumps(
        {
            "token": req.token_value.strip(),
            "base_url": (req.base_url or "").strip() or None,
            "model": (req.model_override or "").strip() or None,
        },
        ensure_ascii=False,
    )


@router.get("/providers", response_model=dict[str, Any])
def list_providers_public() -> dict[str, Any]:
    return PROVIDER_LIST


@router.get("", response_model=list[TokenListItem])
def list_tokens(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TokenListItem]:
    rows = (
        db.query(AiTokenConfig)
        .filter(AiTokenConfig.user_id == user.id)
        .order_by(AiTokenConfig.created_at.desc())
        .all()
    )
    return [
        TokenListItem(
            id=r.id,
            provider=r.provider,
            name=r.name,
            model_override=r.model_override,
            base_url=r.base_url,
            is_active=r.is_active,
            is_default=r.is_default,
            monthly_budget_usd=r.monthly_budget_usd,
            usage_this_month_usd=r.usage_this_month_usd,
            last_used_at=r.last_used_at.isoformat() if r.last_used_at else None,
        )
        for r in rows
    ]


@router.post("", response_model=TokenListItem, status_code=status.HTTP_201_CREATED)
def create_token(
    payload: TokenCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.OPERATOR)),
    enc: EncryptionService = Depends(get_encryption_service),
) -> TokenListItem:
    prov = payload.provider.strip().lower()
    if prov not in PROVIDER_LIST:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Noma’lum provayder")
    exists = (
        db.query(CredentialVault)
        .filter(
            CredentialVault.user_id == user.id,
            CredentialVault.credential_type == CREDENTIAL_TYPE,
            CredentialVault.name == payload.name,
        )
        .first()
    )
    if exists:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Bu nom allaqachon bor")
    row_enc = enc.to_db_row(_secret_payload(payload), str(user.id), "ai_token")
    vault = CredentialVault(
        user_id=user.id,
        name=payload.name,
        credential_type=CREDENTIAL_TYPE,
        cipher_text=row_enc["cipher_text"],
        iv=row_enc["iv"],
        tag=row_enc["tag"],
        salt=row_enc["salt"],
    )
    db.add(vault)
    db.flush()
    meta = PROVIDER_LIST[prov]
    default_url = meta.get("base_url")
    cfg = AiTokenConfig(
        user_id=user.id,
        secret_id=vault.id,
        provider=prov,
        name=payload.name,
        model_override=payload.model_override,
        base_url=payload.base_url or (default_url if isinstance(default_url, str) else None),
        monthly_budget_usd=payload.monthly_budget_usd,
        is_default=payload.is_default,
    )
    if payload.is_default:
        db.query(AiTokenConfig).filter(AiTokenConfig.user_id == user.id).update({AiTokenConfig.is_default: False})
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    log_platform_audit(
        db,
        actor_user_id=user.id,
        action_type="ai_token_create",
        resource_type="ai_token_config",
        resource_id=str(cfg.id),
        details={"provider": prov, "name": payload.name},
    )
    return TokenListItem(
        id=cfg.id,
        provider=cfg.provider,
        name=cfg.name,
        model_override=cfg.model_override,
        base_url=cfg.base_url,
        is_active=cfg.is_active,
        is_default=cfg.is_default,
        monthly_budget_usd=cfg.monthly_budget_usd,
        usage_this_month_usd=cfg.usage_this_month_usd,
        last_used_at=cfg.last_used_at.isoformat() if cfg.last_used_at else None,
    )


@router.patch("/{config_id}", response_model=TokenListItem)
def patch_token(
    config_id: uuid.UUID,
    body: TokenPatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.OPERATOR)),
) -> TokenListItem:
    cfg = (
        db.query(AiTokenConfig)
        .filter(AiTokenConfig.id == config_id, AiTokenConfig.user_id == user.id)
        .first()
    )
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Topilmadi")
    data = body.model_dump(exclude_unset=True)
    allowed = frozenset({"is_active", "is_default", "monthly_budget_usd", "model_override", "base_url"})
    data = {k: v for k, v in data.items() if k in allowed}
    if data.get("is_default") is True:
        db.query(AiTokenConfig).filter(AiTokenConfig.user_id == user.id).update({AiTokenConfig.is_default: False})
    for k, v in data.items():
        setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    return TokenListItem(
        id=cfg.id,
        provider=cfg.provider,
        name=cfg.name,
        model_override=cfg.model_override,
        base_url=cfg.base_url,
        is_active=cfg.is_active,
        is_default=cfg.is_default,
        monthly_budget_usd=cfg.monthly_budget_usd,
        usage_this_month_usd=cfg.usage_this_month_usd,
        last_used_at=cfg.last_used_at.isoformat() if cfg.last_used_at else None,
    )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_token(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.OPERATOR)),
) -> Response:
    cfg = (
        db.query(AiTokenConfig)
        .filter(AiTokenConfig.id == config_id, AiTokenConfig.user_id == user.id)
        .first()
    )
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Topilmadi")
    secret_id = cfg.secret_id
    db.delete(cfg)
    db.flush()
    v = db.get(CredentialVault, secret_id)
    if v:
        db.delete(v)
    db.commit()


@router.post("/{config_id}/test", response_model=TestResult)
def test_token(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.OPERATOR)),
    enc: EncryptionService = Depends(get_encryption_service),
) -> TestResult:
    cfg = (
        db.query(AiTokenConfig)
        .filter(AiTokenConfig.id == config_id, AiTokenConfig.user_id == user.id)
        .first()
    )
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Topilmadi")
    vault = db.get(CredentialVault, cfg.secret_id)
    if not vault:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Secret yo‘q")
    router_llm = LLMRouter(enc)
    t0 = time.perf_counter()
    try:
        text, tokens, model = router_llm.test_completion_sync(db, user.id, cfg, vault)
        ms = int((time.perf_counter() - t0) * 1000)
        return TestResult(success=True, latency_ms=ms, model_used=model, detail=text[:200])
    except Exception as e:
        ms = int((time.perf_counter() - t0) * 1000)
        log.warning("ai_token_test_failed", error=str(e))
        return TestResult(success=False, latency_ms=ms, model_used=cfg.model_override or "", detail=str(e)[:500])
