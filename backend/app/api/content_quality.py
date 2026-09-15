import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.api.schemas import (
    ContentDecayAlertOut,
    ContentGapOut,
    ImageIssueOut,
    InternalLinkingRecommendationOut,
    PageQualityOut,
    SchemaRecommendationOut,
)
from app.core.database import get_db
from app.models.business import Business
from app.models.content_quality import ContentDecayAlert, ContentGap, PageQualityScore, SchemaRecommendation
from app.models.crawl import CrawledPage, CrawlJob
from app.models.keyword import Keyword
from app.models.user import User, UserRole
from app.services.content_decay import detect_decay
from app.services.content_gap import find_content_gaps
from app.services.image_seo import analyze_images
from app.services.internal_linking import analyze_internal_links
from app.services.page_quality import score_page
from app.services.schema_engine import detect_schema_types, recommend_missing_schema

router = APIRouter(prefix="/api/v1", tags=["content-quality"])


def _page_to_dict(page: CrawledPage) -> dict:
    return {
        "url": page.url,
        "title": page.title,
        "meta_description": page.meta_description,
        "h1": page.h1,
        "h2": page.h2,
        "word_count": page.word_count,
        "canonical_url": page.canonical_url,
        "structured_data": page.structured_data,
        "open_graph": page.open_graph,
        "internal_links": page.internal_links,
        "images": page.images,
    }


def _get_crawl_job_or_404(db: Session, crawl_job_id: uuid.UUID) -> CrawlJob:
    job = db.query(CrawlJob).filter(CrawlJob.id == crawl_job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl job not found")
    return job


# ---- Page Quality (Module 4) ----

@router.post("/crawl-jobs/{crawl_job_id}/analyze/quality", response_model=list[PageQualityOut])
def analyze_page_quality(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    job = _get_crawl_job_or_404(db, crawl_job_id)
    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == job.id).all()

    results = []
    for page in pages:
        score_result = score_page(_page_to_dict(page))
        record = PageQualityScore(
            crawled_page_id=page.id,
            url=page.url,
            overall_score=score_result["overall_score"],
            component_scores=score_result["component_scores"],
            explanation=score_result["explanation"],
            source="page_quality_engine",
            confidence=1.0,
        )
        db.add(record)
        results.append(record)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/crawl-jobs/{crawl_job_id}/quality", response_model=list[PageQualityOut])
def get_page_quality(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    page_ids = [p.id for p in db.query(CrawledPage.id).filter(CrawledPage.crawl_job_id == crawl_job_id).all()]
    return db.query(PageQualityScore).filter(PageQualityScore.crawled_page_id.in_(page_ids)).all()


# ---- Schema Engine (Module 16) ----

@router.post("/crawl-jobs/{crawl_job_id}/analyze/schema", response_model=list[SchemaRecommendationOut])
def analyze_schema(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    job = _get_crawl_job_or_404(db, crawl_job_id)
    business = db.query(Business).filter(Business.id == job.business_id).first()
    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == job.id).all()

    results = []
    for page in pages:
        existing_types = detect_schema_types(page.structured_data or [])
        recommendations = recommend_missing_schema(
            page={"url": page.url},
            business_name=business.name,
            business_website=business.website_url,
            existing_types=existing_types,
        )
        for rec in recommendations:
            record = SchemaRecommendation(
                crawled_page_id=page.id,
                url=page.url,
                recommended_type=rec["recommended_type"],
                reason=rec["reason"],
                suggested_jsonld=rec["suggested_jsonld"],
                source="schema_engine",
                confidence=1.0,
            )
            db.add(record)
            results.append(record)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/crawl-jobs/{crawl_job_id}/schema-recommendations", response_model=list[SchemaRecommendationOut])
def get_schema_recommendations(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    page_ids = [p.id for p in db.query(CrawledPage.id).filter(CrawledPage.crawl_job_id == crawl_job_id).all()]
    return db.query(SchemaRecommendation).filter(SchemaRecommendation.crawled_page_id.in_(page_ids)).all()


# ---- Image SEO (Module 26) - computed on demand, not persisted ----

@router.get("/crawl-jobs/{crawl_job_id}/image-issues", response_model=list[ImageIssueOut])
def get_image_issues(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    _get_crawl_job_or_404(db, crawl_job_id)
    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job_id).all()
    return analyze_images([_page_to_dict(p) for p in pages])


# ---- Internal Linking (Module 17) - computed on demand, not persisted ----

@router.get("/crawl-jobs/{crawl_job_id}/internal-linking", response_model=list[InternalLinkingRecommendationOut])
def get_internal_linking_recommendations(
    crawl_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    _get_crawl_job_or_404(db, crawl_job_id)
    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job_id).all()
    return analyze_internal_links([_page_to_dict(p) for p in pages])


# ---- Content Gap (Module 12) ----

@router.post("/businesses/{business_id}/content-gaps", response_model=list[ContentGapOut])
def analyze_content_gaps(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    latest_job = (
        db.query(CrawlJob)
        .filter(CrawlJob.business_id == business_id, CrawlJob.status == "completed")
        .order_by(CrawlJob.created_at.desc())
        .first()
    )
    if not latest_job:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No completed crawl found for this business yet")

    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == latest_job.id).all()
    keywords = db.query(Keyword).filter(Keyword.business_id == business_id).all()

    gaps = find_content_gaps(
        [{"id": k.id, "term": k.term} for k in keywords],
        [_page_to_dict(p) for p in pages],
    )

    # Current-state table, not a history log - replace previous analysis.
    db.query(ContentGap).filter(ContentGap.business_id == business_id).delete()

    results = []
    for gap in gaps:
        record = ContentGap(
            business_id=business_id,
            keyword_id=gap["keyword_id"],
            keyword_term=gap["keyword_term"],
            classification=gap["classification"],
            matched_url=gap["matched_url"],
            match_score=gap["match_score"],
            source="content_gap_engine",
            confidence=0.7,  # heuristic keyword/page text overlap, not a certainty
        )
        db.add(record)
        results.append(record)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/businesses/{business_id}/content-gaps", response_model=list[ContentGapOut])
def get_content_gaps(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return db.query(ContentGap).filter(ContentGap.business_id == business_id).all()


# ---- Content Decay (Module 13) ----

@router.post("/businesses/{business_id}/content-decay", response_model=list[ContentDecayAlertOut])
def analyze_content_decay(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    recent_jobs = (
        db.query(CrawlJob)
        .filter(CrawlJob.business_id == business_id, CrawlJob.status == "completed")
        .order_by(CrawlJob.created_at.desc())
        .limit(2)
        .all()
    )
    if len(recent_jobs) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 2 completed crawls of this business to detect decay",
        )

    current_job, previous_job = recent_jobs[0], recent_jobs[1]
    current_pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == current_job.id).all()
    previous_pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == previous_job.id).all()

    alerts = detect_decay(
        [_page_to_dict(p) for p in previous_pages],
        [_page_to_dict(p) for p in current_pages],
    )

    results = []
    for alert in alerts:
        record = ContentDecayAlert(
            business_id=business_id,
            url=alert["url"],
            previous_crawl_job_id=previous_job.id,
            current_crawl_job_id=current_job.id,
            decay_type=alert["decay_type"],
            description=alert["description"],
            severity=alert["severity"],
            source="content_decay_engine",
            confidence=1.0,
        )
        db.add(record)
        results.append(record)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/businesses/{business_id}/content-decay", response_model=list[ContentDecayAlertOut])
def get_content_decay(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return db.query(ContentDecayAlert).filter(ContentDecayAlert.business_id == business_id).all()
