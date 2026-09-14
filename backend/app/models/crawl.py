"""
Module 2 - Website Crawler.

CrawlJob is one run of the crawler against a business's site. CrawledPage
is a snapshot of one URL as seen during that run. We keep history (don't
overwrite previous crawls) because Module 13 (Content Decay) and Module 33
(Competitor Change Detection) later need to diff snapshots over time.
"""
import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import FullAuditableMixin


class CrawlJob(Base, FullAuditableMixin):
    __tablename__ = "crawl_jobs"

    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    start_url: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, running, completed, failed
    max_pages: Mapped[int] = mapped_column(Integer, default=50)
    max_depth: Mapped[int] = mapped_column(Integer, default=3)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    pages: Mapped[list["CrawledPage"]] = relationship(back_populates="crawl_job", cascade="all, delete-orphan")
    issues: Mapped[list["TechnicalIssue"]] = relationship(back_populates="crawl_job", cascade="all, delete-orphan")


class CrawledPage(Base, FullAuditableMixin):
    __tablename__ = "crawled_pages"

    crawl_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crawl_jobs.id"))
    url: Mapped[str] = mapped_column(String(1024))
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)

    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    h1: Mapped[list | None] = mapped_column(JSON, nullable=True)
    h2: Mapped[list | None] = mapped_column(JSON, nullable=True)
    h3: Mapped[list | None] = mapped_column(JSON, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    canonical_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    robots_meta: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_noindex: Mapped[bool] = mapped_column(default=False)
    viewport: Mapped[str | None] = mapped_column(String(255), nullable=True)

    internal_links: Mapped[list | None] = mapped_column(JSON, nullable=True)
    external_links: Mapped[list | None] = mapped_column(JSON, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{src, alt, width, height}]
    structured_data: Mapped[list | None] = mapped_column(JSON, nullable=True)  # parsed JSON-LD blocks
    open_graph: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    redirect_chain: Mapped[list | None] = mapped_column(JSON, nullable=True)  # list of URLs, empty if no redirect
    discovered_via: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "sitemap" | "link" | "seed"
    crawl_depth: Mapped[int] = mapped_column(Integer, default=0)

    crawl_job: Mapped["CrawlJob"] = relationship(back_populates="pages")


class TechnicalIssue(Base, FullAuditableMixin):
    __tablename__ = "technical_issues"

    crawl_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crawl_jobs.id"))
    issue_type: Mapped[str] = mapped_column(String(64))   # e.g. "missing_title", "broken_link", "multiple_h1"
    severity: Mapped[str] = mapped_column(String(16))     # "critical" | "high" | "medium" | "low"
    affected_url: Mapped[str] = mapped_column(String(1024))
    description: Mapped[str] = mapped_column(Text)
    recommended_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_fix_eligible: Mapped[bool] = mapped_column(default=False)

    crawl_job: Mapped["CrawlJob"] = relationship(back_populates="issues")
