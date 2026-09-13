"""
Auth + RBAC. Roles are deliberately a fixed enum, not a free-for-all
permissions table - Module 44 (Autonomy/Permission System) builds action-
level permissions on top of this later, but user-level roles stay simple.
"""
import enum
import uuid

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    ADMIN = "admin"       # full access, can approve Level 2+ actions
    EDITOR = "editor"     # can create/edit content, cannot approve autonomous actions
    VIEWER = "viewer"     # read-only access to dashboards and reports


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
