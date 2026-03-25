"""Platform darajasidagi audit (admin panel va muhim amallar)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import PlatformAuditLog


def log_platform_audit(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action_type: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        PlatformAuditLog(
            actor_user_id=actor_user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
    )
    db.commit()
