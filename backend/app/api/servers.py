from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Role, get_encryption_service, require_role
from app.models import Server, ServerMetric
from app.schemas import ServerCreate, ServerRead, ServerUpdate
from app.services.encryption_service import EncryptedBlob, EncryptionService

router = APIRouter()


def _store_ssh_password(server: Server, password: str, enc: EncryptionService) -> None:
    ctx = f"server:{server.id}:ssh_password"
    blob = enc.encrypt(password, ctx)
    meta = dict(server.server_metadata or {})
    meta["ssh_auth"] = {
        "cipher": blob.ciphertext.hex(),
        "iv": blob.iv.hex(),
        "tag": blob.tag.hex(),
        "salt": blob.salt.hex(),
    }
    server.server_metadata = meta


def decrypt_ssh_password(server: Server) -> str | None:
    """Used by agent to get SSH password for password-auth servers."""
    ssh_auth = (server.server_metadata or {}).get("ssh_auth")
    if not ssh_auth:
        return None
    from app.config import get_settings
    from app.services.encryption_service import build_encryption_service
    s = get_settings()
    try:
        enc = build_encryption_service(s.master_encryption_key, s.encryption_master_key_b64)
        blob = EncryptedBlob.from_storage(
            bytes.fromhex(ssh_auth["cipher"]),
            bytes.fromhex(ssh_auth["iv"]),
            bytes.fromhex(ssh_auth["salt"]),
            bytes.fromhex(ssh_auth["tag"]),
        )
        return enc.decrypt(blob, f"server:{server.id}:ssh_password")
    except Exception:
        return None


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
    enc: EncryptionService = Depends(get_encryption_service),
) -> Server:
    existing = db.query(Server).filter(Server.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server name already exists")
    data = payload.model_dump(exclude={"ssh_password"})
    row = Server(**data)
    db.add(row)
    db.flush()  # get ID before storing password
    if payload.ssh_password and payload.auth_type == "password":
        _store_ssh_password(row, payload.ssh_password, enc)
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
    enc: EncryptionService = Depends(get_encryption_service),
) -> Server:
    row = db.get(Server, server_id)
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    data = payload.model_dump(exclude_unset=True, exclude={"ssh_password"})
    if "name" in data and data["name"] != row.name:
        clash = db.query(Server).filter(Server.name == data["name"]).first()
        if clash:
            raise HTTPException(status_code=400, detail="Server name already exists")
    for k, v in data.items():
        setattr(row, k, v)
    if payload.ssh_password is not None:
        _store_ssh_password(row, payload.ssh_password, enc)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{server_id}", response_model=ServerRead)
def patch_server(
    server_id: int,
    payload: ServerUpdate,
    db: Session = Depends(get_db),
    admin: object = Depends(require_role(Role.ADMIN)),
    enc: EncryptionService = Depends(get_encryption_service),
) -> Server:
    return update_server(server_id, payload, db, admin, enc)


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
