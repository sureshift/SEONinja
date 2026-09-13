"""
Shared mixins for every model in the system.

Per the roadmap's Module 47/48 (Data Quality Engine / Source Reliability):
every data point must carry source, timestamp, and confidence from the
start - retrofitting this later onto tables that already have data is
painful, so it's built into the base mixin instead of added per-table.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class SourceConfidenceMixin:
    """
    Every data point declares where it came from and how much to trust it.
    Confidence is a 0.0-1.0 float; source is a short free-text label
    (e.g. 'manual_entry', 'gsc_api', 'crawler', 'competitor_public_page').
    The strategy engine (later phases) reads these before weighting any
    recommendation - this is what Module 48 (Source Reliability) depends on.
    """
    source: Mapped[str] = mapped_column(String(64), default="manual_entry")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)


class FullAuditableMixin(UUIDPrimaryKeyMixin, TimestampMixin, SourceConfidenceMixin):
    """Standard mixin for business-data tables. Auth/RBAC tables use
    UUIDPrimaryKeyMixin + TimestampMixin only - source/confidence doesn't
    make sense for a user account."""
    pass
