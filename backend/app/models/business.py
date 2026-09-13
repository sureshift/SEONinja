"""
Module 1 - Business Intelligence.

Stores the business itself, its services, locations, and goals. Everything
else in the system (crawler findings, keyword tracking, opportunities,
revenue) ultimately links back to a Business record, so this is the root
of the schema.
"""
import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import FullAuditableMixin


class Business(Base, FullAuditableMixin):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255))
    website_url: Mapped[str] = mapped_column(String(512))
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    services: Mapped[list["Service"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    locations: Mapped[list["Location"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    goals: Mapped[list["BusinessGoal"]] = relationship(back_populates="business", cascade="all, delete-orphan")


class Service(Base, FullAuditableMixin):
    __tablename__ = "services"

    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    business: Mapped["Business"] = relationship(back_populates="services")


class Location(Base, FullAuditableMixin):
    __tablename__ = "locations"

    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    label: Mapped[str] = mapped_column(String(255))  # e.g. "Najafgarh service area"
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    business: Mapped["Business"] = relationship(back_populates="locations")


class BusinessGoal(Base, FullAuditableMixin):
    __tablename__ = "business_goals"

    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    goal_type: Mapped[str] = mapped_column(String(64))  # e.g. "leads", "bookings", "revenue"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    business: Mapped["Business"] = relationship(back_populates="goals")
