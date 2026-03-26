"""Telegram bot uchun ichki endpointlar (faqat `X-Internal-Secret`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Server
from app.schemas import ServerCreate, ServerRead

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_internal(request: Request) -> None:
    s = get_settings()
    sec = (s.api_internal_secret or "").strip()
    if not sec or request.headers.get("X-Internal-Secret") != sec:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="X-Internal-Secret noto‘g‘ri")


@router.get("/servers", response_model=list[ServerRead])
def internal_list_servers(
    request: Request,
    db: Session = Depends(get_db),
) -> list[Server]:
    _require_internal(request)
    return db.query(Server).order_by(Server.name).all()


@router.post("/servers", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
def internal_create_server(
    payload: ServerCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> Server:
    _require_internal(request)
    existing = db.query(Server).filter(Server.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server name already exists")
    row = Server(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
