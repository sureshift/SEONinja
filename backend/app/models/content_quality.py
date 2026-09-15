"""
Modules 4, 12, 13, 16 - Page Quality, Content Gap, Content Decay, Schema.

All of these are analysis OUTPUTS derived from data Phase 2 (crawls) and
Phase 3 (keywords) already collected - no new crawling happens here,
just deeper analysis of what's already stored.
"""
import uuid

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import FullAuditableMixin


class PageQualityScore(Base, FullAuditableMixin):
    __tablename__ = "page_quality_scores"

    crawled_page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crawled_pages.id"))
    url: Mapped[str] = mapped_column(String(1024))
    overall_score: Mapped[float] = mapped_column(Float)  # 0-100
    component_scores: Mapped[dict] = mapped_column(JSON)  # {"content_depth": 80, "structure": 60, ...} - explainable, not a black box
    explanation: Mapped[list] = mapped_column(JSON)  # list of human-readable reasons behind the score


class SchemaRecommendation(Base, FullAuditableMixin):
    __tablename__ = "schema_recommendations"

    crawled_page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crawled_pages.id"))
    url: Mapped[str] = mapped_column(String(1024))
    recommended_type: Mapped[str] = mapped_column(String(64))  # e.g. "LocalBusiness", "BreadcrumbList"
    reason: Mapped[str] = mapped_column(Text)
    suggested_jsonld: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="suggested")  # suggested | applied | dismissed


class ContentGap(Base, FullAuditableMixin):
    __tablename__ = "content_gaps"

    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    keyword_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("keywords.id"))
    keyword_term: Mapped[str] = mapped_column(String(512))
    classification: Mapped[str] = mapped_column(String(32))  # missing | weak | covered
    matched_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1, how well the matched page covers it


class ContentDecayAlert(Base, FullAuditableMixin):
    __tablename__ = "content_decay_alerts"

    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    url: Mapped[str] = mapped_column(String(1024))
    previous_crawl_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crawl_jobs.id"))
    current_crawl_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crawl_jobs.id"))
    decay_type: Mapped[str] = mapped_column(String(64))  # word_count_drop | lost_structured_data | lost_h1 | title_changed
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16))
