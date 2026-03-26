"""Umumiy provayder ro‘yxati (kalitsiz meta)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.services.llm_router import PROVIDER_LIST

router = APIRouter(prefix="/ai-providers", tags=["ai-providers"])


@router.get("", response_model=dict[str, Any])
def list_ai_providers() -> dict[str, Any]:
    return PROVIDER_LIST
