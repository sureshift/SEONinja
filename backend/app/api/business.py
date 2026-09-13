import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.api.schemas import BusinessCreate, BusinessOut
from app.core.database import get_db
from app.models.business import Business
from app.models.user import User, UserRole
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/v1/businesses", tags=["businesses"])


@router.post("", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def create_business(
    payload: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    business = Business(
        name=payload.name,
        website_url=payload.website_url,
        industry=payload.industry,
        description=payload.description,
        source="manual_entry",
        confidence=1.0,
    )
    db.add(business)
    db.flush()

    record_audit(
        db,
        actor_label=f"user:{current_user.email}",
        actor_user_id=current_user.id,
        action="create",
        entity_type="business",
        entity_id=business.id,
        after=payload.model_dump(),
        reason="Manual creation via API",
    )

    db.commit()
    db.refresh(business)
    return business


@router.get("/{business_id}", response_model=BusinessOut)
def get_business(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


@router.get("", response_model=list[BusinessOut])
def list_businesses(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return db.query(Business).all()
