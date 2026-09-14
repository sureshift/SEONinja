import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: UserRole = UserRole.VIEWER


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BusinessCreate(BaseModel):
    name: str
    website_url: str
    industry: str | None = None
    description: str | None = None


class BusinessOut(BaseModel):
    id: uuid.UUID
    name: str
    website_url: str
    industry: str | None
    description: str | None

    class Config:
        from_attributes = True


class CrawlJobCreate(BaseModel):
    business_id: uuid.UUID
    start_url: str
    max_pages: int = 50
    max_depth: int = 3


class CrawlJobOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    start_url: str
    status: str
    max_pages: int
    max_depth: int
    pages_crawled: int
    error_message: str | None

    class Config:
        from_attributes = True


class CrawledPageOut(BaseModel):
    id: uuid.UUID
    url: str
    status_code: int | None
    title: str | None
    meta_description: str | None
    word_count: int | None
    canonical_url: str | None
    is_noindex: bool

    class Config:
        from_attributes = True


class TechnicalIssueOut(BaseModel):
    id: uuid.UUID
    issue_type: str
    severity: str
    affected_url: str
    description: str
    recommended_fix: str | None
    auto_fix_eligible: bool

    class Config:
        from_attributes = True


class KeywordCreate(BaseModel):
    business_id: uuid.UUID
    term: str
    language: str = "en"
    location: str | None = None
    intent: str | None = None


class KeywordOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    term: str
    language: str
    location: str | None
    intent: str | None
    search_volume: int | None
    is_seed: bool
    parent_keyword_id: uuid.UUID | None

    class Config:
        from_attributes = True


class FanOutRequest(BaseModel):
    locations: list[str] = []


class RankCheckOut(BaseModel):
    keyword_id: uuid.UUID
    snapshot_id: uuid.UUID
    position: int | None
    url: str | None
    change_type: str | None = None
    delta: int | None = None
