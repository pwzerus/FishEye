"""Append-only record of moderation and account-management actions."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.community import AuditLog, User


def record(
    db: Session,
    actor: User | None,
    action: str,
    target_type: str,
    target_id: int,
    **detail: Any,
) -> AuditLog:
    """Adds (doesn't commit) an entry; it lands in the same transaction as
    the change it describes, so the log can't claim an action that was
    rolled back or miss one that wasn't."""
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_label=f"{actor.display_name} <{actor.email}>" if actor else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=json.dumps(detail, default=str) if detail else None,
    )
    db.add(entry)
    return entry
