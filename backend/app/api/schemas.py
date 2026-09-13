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
