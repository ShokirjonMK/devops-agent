from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Role, require_role
from app.models import Server, ServerMetric
from app.schemas import ServerCreate, ServerRead, ServerUpdate

router = APIRouter()


@router.get("", response_model=list[ServerRead])
def list_servers(
    db: Session = Depends(get_db),
    _: object = Depends(require_role(Role.VIEWER)),
) -> list[Server]:
    return db.query(Server).order_by(Server.name).all()


@router.get("/{server_id}/metrics/recent")
def server_metrics_recent(
    server_id: int,
    hours: int = Query(24, ge=1, le=24 * 30),
    db: Session = Depends(get_db),
    _: object = Depends(require_role(Role.VIEWER)),
):
    row = db.get(Server, server_id)
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    since = datetime.now(UTC) - timedelta(hours=hours)
    q = (
        db.query(ServerMetric)
        .filter(ServerMetric.server_id == server_id, ServerMetric.collected_at >= since)
        .order_by(ServerMetric.collected_at.asc())
    )
    rows = q.all()
    return {
        "server_id": server_id,
        "points": [
            {
                "t": m.collected_at.isoformat() if m.collected_at else None,
                "cpu": m.cpu_percent,
                "ram": m.ram_percent,
                "disk": m.disk_percent,
                "load_1": m.load_1,
            }
            for m in rows
        ],
    }


@router.post("", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
def create_server(
    payload: ServerCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(Role.ADMIN)),
) -> Server:
    existing = db.query(Server).filter(Server.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server name already exists")
    row = Server(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{server_id}", response_model=ServerRead)
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(Role.VIEWER)),
) -> Server:
    row = db.get(Server, server_id)
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    return row


@router.put("/{server_id}", response_model=ServerRead)
def update_server(
    server_id: int,
    payload: ServerUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(Role.ADMIN)),
) -> Server:
    row = db.get(Server, server_id)
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != row.name:
        clash = db.query(Server).filter(Server.name == data["name"]).first()
        if clash:
            raise HTTPException(status_code=400, detail="Server name already exists")
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{server_id}", response_model=ServerRead)
def patch_server(
    server_id: int,
    payload: ServerUpdate,
    db: Session = Depends(get_db),
    admin: object = Depends(require_role(Role.ADMIN)),
) -> Server:
    return update_server(server_id, payload, db, admin)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(Role.ADMIN)),
) -> Response:
    row = db.get(Server, server_id)
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    db.delete(row)
    db.commit()
