"""
Sure Shift Search Growth OS - API entrypoint.

Phase 0 scope: app boots, health check works, config loads from env.
No business logic lives here yet - that comes in later phases.
"""
from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Search Growth OS",
    description="Autonomous SEO + AEO + GEO Search Growth Operating System",
    version="0.0.1-phase0",
)


@app.get("/health")
def health_check() -> dict:
    """Basic liveness check. Used by Docker healthcheck and CI."""
    return {
        "status": "ok",
        "service": "search-growth-os-api",
        "phase": "0",
        "environment": settings.environment,
    }


@app.get("/")
def root() -> dict:
    return {"message": "Search Growth OS API - Phase 0 skeleton"}
