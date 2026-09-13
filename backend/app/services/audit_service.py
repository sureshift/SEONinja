"""
Central place that writes to audit_log. Every create/update/delete in the
API layer should call this rather than writing to AuditLog directly, so
the audit format stays consistent across all future modules.
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    actor_label: str,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    actor_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before=before,
        after=after,
        reason=reason,
    )
    db.add(entry)
    db.flush()
    return entry
