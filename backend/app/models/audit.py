"""
Module 46/49 - Central audit trail. Every write to a business-data table
should produce one of these. Kept schema-agnostic (entity_type + entity_id
as strings, not foreign keys) so it can log against ANY table without a
migration every time a new module adds one.
"""
import uuid

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_log"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_label: Mapped[str] = mapped_column(String(128))  # e.g. "user:jane@sureshift.in" or "system:crawler"
    action: Mapped[str] = mapped_column(String(64))         # "create", "update", "delete"
    entity_type: Mapped[str] = mapped_column(String(64))    # e.g. "business", "service"
    entity_id: Mapped[str] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
