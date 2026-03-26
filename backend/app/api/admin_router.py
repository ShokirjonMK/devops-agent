"""Admin API: foydalanuvchilar, sozlamalar, statistika, audit."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.constants import SYSTEM_USER_ID
from app.database import get_db
from app.dependencies import Role, get_encryption_service, require_role
from app.models import (
    AdminSetting,
    AiTokenConfig,
    AICreditBalance,
    AICreditTransaction,
    CredentialVault,
    PaymentRecord,
    Plan,
    PlatformAuditLog,
    Server,
    Task,
    User,
    UserSubscription,
)
from app.services.encryption_service import EncryptedBlob, EncryptionService
from app.services.platform_audit import log_platform_audit

router = APIRouter(prefix="/admin", tags=["admin"])

SYSTEM_AI_TYPE = "system_ai"


class UserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    role: str
    is_active: bool
    last_seen_at: str | None
    tasks_count: int
    servers_count: int


class UserRoleBody(BaseModel):
    role: str = Field(..., min_length=3, max_length=16)


class UserActiveBody(BaseModel):
    is_active: bool


class SettingPatchBody(BaseModel):
    value: Any


class SystemAiBody(BaseModel):
    provider: str = Field(..., min_length=2, max_length=32)
    api_key: str = Field(..., min_length=8, max_length=16384)
    model: str = Field(..., min_length=1, max_length=128)


class SystemAiMasked(BaseModel):
    provider: str
    model: str
    key_hint: str


def _mask_key(k: str) -> str:
    k = k.strip()
    if len(k) <= 4:
        return "****"
    return "●●●●" + k[-4:]


def _user_servers_used_count(db: Session, user_uuid: uuid.UUID) -> int:
    return (
        int(
            db.query(func.count(func.distinct(Task.server_id)))
            .filter(Task.owner_user_id == user_uuid, Task.server_id.isnot(None))
            .scalar()
            or 0
        )
    )


@router.get("/users", response_model=list[UserListItem])
def admin_list_users(
    search: str = "",
    role: str = "",
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> list[UserListItem]:
    q = db.query(User)
    if search.strip():
        pat = f"%{search.strip().lower()}%"
        q = q.filter(
            or_(
                func.lower(User.username).like(pat),
                func.lower(User.first_name).like(pat),
            )
        )
    if role.strip():
        q = q.filter(User.role == role.strip().lower())
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    offset = (page - 1) * limit
    rows = q.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    out: list[UserListItem] = []
    for u in rows:
        tc = db.query(func.count(Task.id)).filter(Task.owner_user_id == u.id).scalar() or 0
        sc = (
            db.query(func.count(func.distinct(Task.server_id)))
            .filter(Task.owner_user_id == u.id, Task.server_id.isnot(None))
            .scalar()
            or 0
        )
        out.append(
            UserListItem(
                id=u.id,
                telegram_id=u.telegram_id,
                username=u.username,
                first_name=u.first_name,
                role=u.role,
                is_active=u.is_active,
                last_seen_at=u.last_seen_at.isoformat() if u.last_seen_at else None,
                tasks_count=int(tc),
                servers_count=int(sc),
            )
        )
    return out


@router.patch("/users/{user_id}/role", response_model=UserListItem)
def admin_set_role(
    user_id: uuid.UUID,
    body: UserRoleBody,
    db: Session = Depends(get_db),
    owner: User = Depends(require_role(Role.OWNER)),
) -> UserListItem:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User topilmadi")
    raw = body.role.strip().lower()
    if raw not in {Role.OWNER.value, Role.ADMIN.value, Role.OPERATOR.value, Role.VIEWER.value}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Noto‘g‘ri rol")
    u.role = raw
    db.commit()
    db.refresh(u)
    log_platform_audit(
        db,
        actor_user_id=owner.id,
        action_type="admin_set_role",
        resource_type="user",
        resource_id=str(u.id),
        details={"role": raw},
    )
    tc = db.query(func.count(Task.id)).filter(Task.owner_user_id == u.id).scalar() or 0
    return UserListItem(
        id=u.id,
        telegram_id=u.telegram_id,
        username=u.username,
        first_name=u.first_name,
        role=u.role,
        is_active=u.is_active,
        last_seen_at=u.last_seen_at.isoformat() if u.last_seen_at else None,
        tasks_count=int(tc),
        servers_count=_user_servers_used_count(db, u.id),
    )


@router.patch("/users/{user_id}/status", response_model=UserListItem)
def admin_set_active(
    user_id: uuid.UUID,
    body: UserActiveBody,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(Role.ADMIN)),
) -> UserListItem:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User topilmadi")
    u.is_active = body.is_active
    db.commit()
    db.refresh(u)
    log_platform_audit(
        db,
        actor_user_id=admin.id,
        action_type="admin_set_active",
        resource_type="user",
        resource_id=str(u.id),
        details={"is_active": body.is_active},
    )
    tc = db.query(func.count(Task.id)).filter(Task.owner_user_id == u.id).scalar() or 0
    return UserListItem(
        id=u.id,
        telegram_id=u.telegram_id,
        username=u.username,
        first_name=u.first_name,
        role=u.role,
        is_active=u.is_active,
        last_seen_at=u.last_seen_at.isoformat() if u.last_seen_at else None,
        tasks_count=int(tc),
        servers_count=_user_servers_used_count(db, u.id),
    )


@router.get("/users/{user_id}/stats")
def admin_user_stats(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User topilmadi")
    total = db.query(func.count(Task.id)).filter(Task.owner_user_id == u.id).scalar() or 0
    ok = (
        db.query(func.count(Task.id))
        .filter(Task.owner_user_id == u.id, Task.status == "done")
        .scalar()
        or 0
    )
    err = (
        db.query(func.count(Task.id))
        .filter(Task.owner_user_id == u.id, Task.status == "error")
        .scalar()
        or 0
    )
    ai_sum = db.query(func.coalesce(func.sum(AiTokenConfig.usage_this_month_usd), 0)).filter(
        AiTokenConfig.user_id == u.id
    ).scalar()
    try:
        ai_float = float(ai_sum or 0)
    except (TypeError, ValueError):
        ai_float = 0.0
    srv_used = (
        db.query(func.count(func.distinct(Task.server_id)))
        .filter(Task.owner_user_id == u.id, Task.server_id.isnot(None))
        .scalar()
        or 0
    )
    return {
        "user_id": str(u.id),
        "tasks_total": int(total),
        "tasks_success": int(ok),
        "tasks_error": int(err),
        "ai_cost_usd": ai_float,
        "servers_count": int(srv_used),
        "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
    }


@router.get("/settings", response_model=list[dict[str, Any]])
def admin_get_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> list[dict[str, Any]]:
    rows = db.query(AdminSetting).order_by(AdminSetting.key).all()
    return [
        {
            "key": r.key,
            "value": r.value,
            "description": r.description,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.patch("/settings/{key}")
def admin_patch_setting(
    key: str,
    body: SettingPatchBody,
    db: Session = Depends(get_db),
    me: User = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    row = db.get(AdminSetting, key)
    if not row:
        row = AdminSetting(key=key, value=body.value, description=None, updated_by=me.id)
        db.add(row)
    else:
        row.value = body.value
        row.updated_by = me.id
    row.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    log_platform_audit(
        db,
        actor_user_id=me.id,
        action_type="admin_setting_patch",
        resource_type="admin_setting",
        resource_id=key,
        details={},
    )
    return {"key": row.key, "value": row.value}


@router.get("/system-ai", response_model=list[SystemAiMasked])
def admin_list_system_ai(
    db: Session = Depends(get_db),
    enc: EncryptionService = Depends(get_encryption_service),
    _: User = Depends(require_role(Role.ADMIN)),
) -> list[SystemAiMasked]:
    rows = (
        db.query(CredentialVault)
        .filter(
            CredentialVault.user_id == SYSTEM_USER_ID,
            CredentialVault.credential_type == SYSTEM_AI_TYPE,
        )
        .all()
    )
    out: list[SystemAiMasked] = []
    for v in rows:
        try:
            blob = EncryptedBlob.from_storage(v.cipher_text, v.iv, v.salt, v.tag)
            plain = enc.decrypt(blob, f"{SYSTEM_USER_ID}:{SYSTEM_AI_TYPE}:{v.name}")
            data = json.loads(plain)
            key = str(data.get("api_key", ""))
            out.append(
                SystemAiMasked(provider=v.name, model=str(data.get("model", "")), key_hint=_mask_key(key))
            )
        except Exception:
            out.append(SystemAiMasked(provider=v.name, model="?", key_hint="****"))
    return out


@router.post("/system-ai", response_model=SystemAiMasked)
def admin_upsert_system_ai(
    body: SystemAiBody,
    db: Session = Depends(get_db),
    me: User = Depends(require_role(Role.ADMIN)),
    enc: EncryptionService = Depends(get_encryption_service),
) -> SystemAiMasked:
    prov = body.provider.strip().lower()
    payload = json.dumps(
        {"api_key": body.api_key.strip(), "model": body.model.strip()},
        ensure_ascii=False,
    )
    ctx = f"{SYSTEM_USER_ID}:{SYSTEM_AI_TYPE}:{prov}"
    blob = enc.encrypt(payload, ctx)
    row = (
        db.query(CredentialVault)
        .filter(
            CredentialVault.user_id == SYSTEM_USER_ID,
            CredentialVault.credential_type == SYSTEM_AI_TYPE,
            CredentialVault.name == prov,
        )
        .first()
    )
    if row:
        row.cipher_text = blob.ciphertext
        row.iv = blob.iv
        row.salt = blob.salt
        row.tag = blob.tag
    else:
        row = CredentialVault(
            user_id=SYSTEM_USER_ID,
            name=prov,
            credential_type=SYSTEM_AI_TYPE,
            cipher_text=blob.ciphertext,
            iv=blob.iv,
            salt=blob.salt,
            tag=blob.tag,
        )
        db.add(row)
    db.commit()
    log_platform_audit(
        db,
        actor_user_id=me.id,
        action_type="admin_system_ai_upsert",
        resource_type="system_ai",
        resource_id=prov,
        details={},
    )
    return SystemAiMasked(provider=prov, model=body.model.strip(), key_hint=_mask_key(body.api_key))


@router.get("/stats/overview")
def admin_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    total_users = int(db.query(func.count(User.id)).scalar() or 0)
    active_today = int(
        db.query(func.count(User.id)).filter(User.last_seen_at.isnot(None), User.last_seen_at >= day_ago).scalar()
        or 0
    )
    tasks_today = int(db.query(func.count(Task.id)).filter(Task.created_at >= day_ago).scalar() or 0)
    tasks_week = int(db.query(func.count(Task.id)).filter(Task.created_at >= week_ago).scalar() or 0)
    done = int(db.query(func.count(Task.id)).filter(Task.status == "done").scalar() or 0)
    all_t = int(db.query(func.count(Task.id)).scalar() or 0)
    rate = round(100.0 * done / all_t, 1) if all_t else 0.0
    servers = int(db.query(func.count(Server.id)).scalar() or 0)
    online = int(
        db.query(func.count(Server.id)).filter(Server.last_check_status == "online").scalar() or 0
    )
    cost_sum = db.query(func.coalesce(func.sum(AiTokenConfig.usage_this_month_usd), 0)).scalar()
    try:
        cost_f = float(cost_sum or 0)
    except (TypeError, ValueError):
        cost_f = 0.0
    return {
        "total_users": total_users,
        "active_users_today": active_today,
        "total_tasks_today": tasks_today,
        "total_tasks_week": tasks_week,
        "success_rate_percent": rate,
        "total_ai_cost_month_usd": cost_f,
        "total_servers": servers,
        "servers_online": online,
    }


@router.get("/audit-logs")
def admin_audit_logs(
    user_id: uuid.UUID | None = None,
    action: str = "",
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    export: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> Any:
    q = db.query(PlatformAuditLog)
    if user_id is not None:
        q = q.filter(PlatformAuditLog.actor_user_id == user_id)
    if action.strip():
        q = q.filter(PlatformAuditLog.action_type == action.strip())
    if from_dt is not None:
        q = q.filter(PlatformAuditLog.created_at >= from_dt)
    if to_dt is not None:
        q = q.filter(PlatformAuditLog.created_at <= to_dt)
    q = q.order_by(PlatformAuditLog.created_at.desc())
    offset = (page - 1) * limit
    rows = q.offset(offset).limit(limit).all()
    data = [
        {
            "id": str(r.id),
            "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
            "action_type": r.action_type,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    if export == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "actor_user_id", "action_type", "resource_type", "resource_id", "created_at"])
        for r in data:
            w.writerow(
                [
                    r["id"],
                    r["actor_user_id"],
                    r["action_type"],
                    r["resource_type"],
                    r["resource_id"],
                    r["created_at"],
                ]
            )
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="audit.csv"'},
        )
    return data


# ─── FINANCE ──────────────────────────────────────────────────────────────────

@router.get("/finance/mrr")
def admin_finance_mrr(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> dict:
    subs = db.query(UserSubscription).filter(UserSubscription.status == "active").all()
    plans = {p.id: float(p.price_usd) for p in db.query(Plan).all()}
    breakdown: dict[str, float] = {}
    total = 0.0
    for s in subs:
        price = plans.get(s.plan_id, 0.0)
        breakdown[s.plan_id] = breakdown.get(s.plan_id, 0.0) + price
        total += price
    return {"mrr_usd": round(total, 2), "arr_usd": round(total * 12, 2), "plans": breakdown}


@router.get("/finance/stats")
def admin_finance_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0
    paid_users = (
        db.query(func.count(UserSubscription.id))
        .filter(UserSubscription.plan_id != "free", UserSubscription.status == "active")
        .scalar()
        or 0
    )
    free_users = total_users - paid_users
    conversion = round((paid_users / total_users * 100) if total_users > 0 else 0, 1)
    total_revenue = db.query(func.coalesce(func.sum(PaymentRecord.amount_usd), 0)).filter(
        PaymentRecord.status == "paid"
    ).scalar() or 0
    ai_spent = db.query(func.coalesce(func.sum(AICreditTransaction.amount_usd), 0)).filter(
        AICreditTransaction.type == "spend"
    ).scalar() or 0
    return {
        "total_users": total_users,
        "paid_users": paid_users,
        "free_users": free_users,
        "conversion_percent": conversion,
        "total_revenue_usd": float(total_revenue),
        "ai_credit_spent_usd": float(abs(ai_spent)),
    }


@router.get("/finance/transactions")
def admin_finance_transactions(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> list[dict]:
    records = (
        db.query(PaymentRecord)
        .order_by(PaymentRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "plan_id": r.plan_id,
            "provider": r.provider,
            "amount_usd": float(r.amount_usd),
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "paid_at": r.paid_at.isoformat() if r.paid_at else None,
        }
        for r in records
    ]


@router.post("/users/{user_id}/plan")
def admin_set_user_plan(
    user_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
    me: User = Depends(require_role(Role.ADMIN)),
) -> dict:
    plan_id = body.get("plan_id", "free")
    if not db.get(Plan, plan_id):
        raise HTTPException(400, "Noto'g'ri tarif ID")
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if not sub:
        sub = UserSubscription(user_id=user_id)
        db.add(sub)
    sub.plan_id = plan_id
    sub.status = "active"
    db.commit()
    log_platform_audit(db, actor_user_id=me.id, action_type="admin_set_user_plan",
                       resource_type="user", resource_id=str(user_id), details={"plan_id": plan_id})
    return {"user_id": str(user_id), "plan_id": plan_id}


@router.post("/users/{user_id}/credit")
def admin_add_credit(
    user_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
    me: User = Depends(require_role(Role.ADMIN)),
) -> dict:
    from app.services.credit_service import credit_service
    amount = float(body.get("amount_usd", 0))
    if amount <= 0:
        raise HTTPException(400, "Summa musbat bo'lishi kerak")
    bal = credit_service.add_bonus_credit(user_id, amount, f"Admin qo'shdi: {me.username or str(me.id)[:8]}", db)
    return {"user_id": str(user_id), "amount_added": amount}


@router.get("/plans")
def admin_list_plans(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
) -> list[dict]:
    plans = db.query(Plan).order_by(Plan.sort_order).all()
    return [
        {"id": p.id, "name": p.name, "price_usd": float(p.price_usd),
         "price_uzs": p.price_uzs, "is_active": p.is_active, "limits": p.limits}
        for p in plans
    ]


@router.patch("/plans/{plan_id}")
def admin_update_plan(
    plan_id: str,
    body: dict,
    db: Session = Depends(get_db),
    me: User = Depends(require_role(Role.ADMIN)),
) -> dict:
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Tarif topilmadi")
    allowed = {"name", "price_usd", "price_uzs", "limits", "features_list", "is_active"}
    for k, v in body.items():
        if k in allowed:
            setattr(plan, k, v)
    db.commit()
    return {"id": plan.id, "name": plan.name, "price_usd": float(plan.price_usd)}
