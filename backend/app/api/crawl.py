import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.deps import require_role
from app.api.schemas import (
    CrawledPageOut,
    CrawlJobCreate,
    CrawlJobOut,
    TechnicalIssueOut,
)
from app.core.database import get_db
from app.crawler.crawler import crawl_site
from app.models.business import Business
from app.models.crawl import CrawledPage, CrawlJob, TechnicalIssue
from app.models.user import User, UserRole
from app.services.audit_service import record_audit
from app.services.technical_seo import detect_issues

router = APIRouter(prefix="/api/v1/crawl-jobs", tags=["crawler"])


@router.post("", response_model=CrawlJobOut, status_code=status.HTTP_201_CREATED)
async def start_crawl_job(
    payload: CrawlJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    """
    Runs synchronously and returns once the crawl completes. Fine for the
    max_pages ceiling in Phase 2 (small/medium sites); a background worker
    (Celery, already scaffolded in the roadmap) is the right move once
    crawls need to run against much larger sites or on a schedule -
    deliberately not built until that's actually needed.
    """
    business = db.query(Business).filter(Business.id == payload.business_id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    job = CrawlJob(
        business_id=payload.business_id,
        start_url=payload.start_url,
        max_pages=payload.max_pages,
        max_depth=payload.max_depth,
        status="running",
    )
    db.add(job)
    db.flush()

    try:
        crawl_results = await crawl_site(
            payload.start_url, max_pages=payload.max_pages, max_depth=payload.max_depth
        )
    except Exception as exc:  # noqa: BLE001 - a failed crawl is a data outcome, not a 500
        job.status = "failed"
        job.error_message = str(exc)
        db.commit()
        db.refresh(job)
        return job

    page_dicts = []
    for result in crawl_results:
        page = CrawledPage(
            crawl_job_id=job.id,
            url=result.url,
            status_code=result.fetch.status_code,
            response_time_ms=result.fetch.response_time_ms,
            content_type=result.fetch.content_type,
            title=result.parsed.get("title"),
            meta_description=result.parsed.get("meta_description"),
            h1=result.parsed.get("h1"),
            h2=result.parsed.get("h2"),
            h3=result.parsed.get("h3"),
            word_count=result.parsed.get("word_count"),
            canonical_url=result.parsed.get("canonical_url"),
            robots_meta=result.parsed.get("robots_meta"),
            is_noindex=result.parsed.get("is_noindex", False),
            viewport=result.parsed.get("viewport"),
            internal_links=result.parsed.get("internal_links"),
            external_links=result.parsed.get("external_links"),
            images=result.parsed.get("images"),
            structured_data=result.parsed.get("structured_data"),
            open_graph=result.parsed.get("open_graph"),
            redirect_chain=result.fetch.redirect_chain,
            discovered_via=result.discovered_via,
            crawl_depth=result.depth,
            source="crawler",
            confidence=1.0,
        )
        db.add(page)
        page_dicts.append({
            "url": result.url,
            "status_code": result.fetch.status_code,
            "title": result.parsed.get("title"),
            "meta_description": result.parsed.get("meta_description"),
            "h1": result.parsed.get("h1"),
            "canonical_url": result.parsed.get("canonical_url"),
            "is_noindex": result.parsed.get("is_noindex", False),
            "word_count": result.parsed.get("word_count"),
            "redirect_chain": result.fetch.redirect_chain,
            "internal_links": result.parsed.get("internal_links"),
            "discovered_via": result.discovered_via,
        })

    for issue_dict in detect_issues(page_dicts):
        db.add(TechnicalIssue(crawl_job_id=job.id, source="crawler", confidence=1.0, **issue_dict))

    job.status = "completed"
    job.pages_crawled = len(crawl_results)

    record_audit(
        db,
        actor_label=f"user:{current_user.email}",
        actor_user_id=current_user.id,
        action="create",
        entity_type="crawl_job",
        entity_id=job.id,
        after={"start_url": job.start_url, "pages_crawled": job.pages_crawled},
        reason="Crawl job triggered via API",
    )

    db.commit()
    db.refresh(job)
    return job


@router.get("/{crawl_job_id}", response_model=CrawlJobOut)
def get_crawl_job(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    job = db.query(CrawlJob).filter(CrawlJob.id == crawl_job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl job not found")
    return job


@router.get("/{crawl_job_id}/pages", response_model=list[CrawledPageOut])
def list_crawled_pages(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job_id).all()


@router.get("/{crawl_job_id}/issues", response_model=list[TechnicalIssueOut])
def list_technical_issues(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return db.query(TechnicalIssue).filter(TechnicalIssue.crawl_job_id == crawl_job_id).all()
