import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.api.schemas import FanOutRequest, KeywordCreate, KeywordOut, RankCheckOut
from app.core.config import get_settings
from app.core.database import get_db
from app.models.business import Business
from app.models.keyword import Keyword, RankRecord, SERPSnapshot
from app.models.user import User, UserRole
from app.providers.serp_provider import get_serp_provider
from app.services.audit_service import record_audit
from app.services.query_fanout import generate_fan_out
from app.services.rank_tracking import detect_rank_change, extract_own_rank

router = APIRouter(prefix="/api/v1/keywords", tags=["keywords"])


@router.post("", response_model=KeywordOut, status_code=status.HTTP_201_CREATED)
def create_keyword(
    payload: KeywordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    business = db.query(Business).filter(Business.id == payload.business_id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    keyword = Keyword(
        business_id=payload.business_id,
        term=payload.term,
        language=payload.language,
        location=payload.location,
        intent=payload.intent,
        is_seed=True,
        source="manual_entry",
        confidence=1.0,
    )
    db.add(keyword)
    db.flush()

    record_audit(
        db,
        actor_label=f"user:{current_user.email}",
        actor_user_id=current_user.id,
        action="create",
        entity_type="keyword",
        entity_id=keyword.id,
        after={"term": keyword.term},
    )

    db.commit()
    db.refresh(keyword)
    return keyword


@router.get("", response_model=list[KeywordOut])
def list_keywords(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return db.query(Keyword).filter(Keyword.business_id == business_id).all()


@router.post("/{keyword_id}/fanout", response_model=list[KeywordOut])
def fanout_keyword(
    keyword_id: uuid.UUID,
    payload: FanOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    seed = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not seed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")

    existing_terms = {
        k.term.lower()
        for k in db.query(Keyword).filter(Keyword.business_id == seed.business_id).all()
    }

    variants = generate_fan_out(seed.term, locations=payload.locations)
    created: list[Keyword] = []

    for variant in variants:
        if variant.term.lower() in existing_terms:
            continue
        new_keyword = Keyword(
            business_id=seed.business_id,
            term=variant.term,
            language=seed.language,
            location=seed.location,
            intent=variant.variant_type if variant.variant_type != "local" else "local",
            is_seed=False,
            parent_keyword_id=seed.id,
            source="query_fanout",
            confidence=0.8,  # generated, not human-confirmed - Module 48 source reliability
        )
        db.add(new_keyword)
        created.append(new_keyword)
        existing_terms.add(variant.term.lower())

    record_audit(
        db,
        actor_label=f"user:{current_user.email}",
        actor_user_id=current_user.id,
        action="create",
        entity_type="keyword_fanout",
        entity_id=seed.id,
        after={"generated_count": len(created)},
        reason=f"Fan-out from seed keyword '{seed.term}'",
    )

    db.commit()
    for k in created:
        db.refresh(k)
    return created


@router.post("/{keyword_id}/rank-check", response_model=RankCheckOut)
async def check_rank(
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")

    business = db.query(Business).filter(Business.id == keyword.business_id).first()
    our_domain = urlparse(business.website_url).netloc or business.website_url

    settings = get_settings()
    provider = get_serp_provider(settings.serp_provider)

    try:
        serp_result = await provider.get_serp(keyword.term, location=keyword.location)
    except (NotImplementedError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SERP provider unavailable: {exc}",
        )

    snapshot = SERPSnapshot(
        keyword_id=keyword.id,
        provider=serp_result.source,
        organic_results=serp_result.organic_results,
        local_pack=serp_result.local_pack,
        featured_snippet=serp_result.featured_snippet,
        people_also_ask=serp_result.people_also_ask,
        ai_overview=serp_result.ai_overview,
        source=serp_result.source,
        confidence=1.0,
    )
    db.add(snapshot)
    db.flush()

    own_rank = extract_own_rank(serp_result.organic_results, our_domain)

    previous_record = (
        db.query(RankRecord)
        .filter(RankRecord.keyword_id == keyword.id)
        .order_by(RankRecord.created_at.desc())
        .first()
    )
    change = detect_rank_change(
        previous_record.position if previous_record else None, own_rank["position"]
    )

    rank_record = RankRecord(
        keyword_id=keyword.id,
        snapshot_id=snapshot.id,
        url=own_rank["url"],
        position=own_rank["position"],
        source=serp_result.source,
        confidence=1.0,
    )
    db.add(rank_record)
    db.commit()
    db.refresh(rank_record)

    return RankCheckOut(
        keyword_id=keyword.id,
        snapshot_id=snapshot.id,
        position=rank_record.position,
        url=rank_record.url,
        change_type=change["change_type"],
        delta=change["delta"],
    )
