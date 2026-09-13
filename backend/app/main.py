"""
Sure Shift Search Growth OS - API entrypoint.

Phase 0: app boots, health check works, config loads from env.
Phase 1: adds auth, RBAC, business CRUD, audit logging.
"""
from fastapi import FastAPI

from app.api import auth, business
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Search Growth OS",
    description="Autonomous SEO + AEO + GEO Search Growth Operating System",
    version="0.1.0-phase1",
)

app.include_router(auth.router)
app.include_router(business.router)


@app.get("/health")
def health_check() -> dict:
    """Basic liveness check. Used by Docker healthcheck and CI."""
    return {
        "status": "ok",
        "service": "search-growth-os-api",
        "phase": "1",
        "environment": settings.environment,
    }


@app.get("/")
def root() -> dict:
    return {"message": "Search Growth OS API - Phase 1"}
