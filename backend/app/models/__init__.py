"""
Import every model here so Base.metadata is fully populated for Alembic's
autogenerate. If a model isn't imported somewhere before autogenerate runs,
Alembic won't know it exists and will silently omit it from the migration.
"""
from app.models.audit import AuditLog  # noqa: F401
from app.models.business import Business, BusinessGoal, Location, Service  # noqa: F401
from app.models.revenue import Booking, Customer, Lead, Quotation, Revenue  # noqa: F401
from app.models.user import User  # noqa: F401
