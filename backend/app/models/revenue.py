"""
Module 1 continued - the revenue chain. This is deliberately minimal in
Phase 1 (just enough structure to link a keyword/page to real money later
in Module 38 - Revenue Intelligence). Phase 10 will extend this, not
replace it.
"""
import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import FullAuditableMixin


class Customer(Base, FullAuditableMixin):
    __tablename__ = "customers"

    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    leads: Mapped[list["Lead"]] = relationship(back_populates="customer")


class Lead(Base, FullAuditableMixin):
    __tablename__ = "leads"

    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    lead_source: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. "organic_search"
    landing_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="new")  # new, qualified, quoted, booked, lost
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped["Customer | None"] = relationship(back_populates="leads")
    quotations: Mapped[list["Quotation"]] = relationship(back_populates="lead")


class Quotation(Base, FullAuditableMixin):
    __tablename__ = "quotations"

    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"))
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[str] = mapped_column(String(64), default="sent")  # sent, accepted, rejected, expired

    lead: Mapped["Lead"] = relationship(back_populates="quotations")
    booking: Mapped["Booking | None"] = relationship(back_populates="quotation", uselist=False)


class Booking(Base, FullAuditableMixin):
    __tablename__ = "bookings"

    quotation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotations.id"))
    scheduled_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="confirmed")

    quotation: Mapped["Quotation"] = relationship(back_populates="booking")
    revenue_entries: Mapped[list["Revenue"]] = relationship(back_populates="booking")


class Revenue(Base, FullAuditableMixin):
    __tablename__ = "revenue"

    booking_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")

    booking: Mapped["Booking"] = relationship(back_populates="revenue_entries")
