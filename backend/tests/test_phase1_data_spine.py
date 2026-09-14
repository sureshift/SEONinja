"""
Phase 1 gate tests. Run against a real Postgres database (set via
DATABASE_URL / TEST_DATABASE_URL), not SQLite - Postgres-specific types
(UUID, JSON) are used in the models, so SQLite would hide real bugs.

Definition of Done being tested here:
  "Can create/read a business profile via API with auth; audit log
  records every write."
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.audit import AuditLog

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/searchos_db",
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def clean_database():
    """Wipe all tables before each test so tests don't leak state into
    each other - this is what makes it safe to re-run the suite repeatedly."""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
    yield


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _register_and_login(email: str, password: str = "testpass123") -> str:
    """Registers a user (first user in a clean DB becomes ADMIN per Phase 1
    bootstrap rule) and returns a bearer token."""
    resp = client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_health_check_reports_phase_1():
    """Named for the phase that introduced it, not the phase currently
    reported - checks the health check works and reports a phase field
    at all, not a specific number that'll go stale every phase."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "phase" in resp.json()


def test_first_registered_user_becomes_admin():
    token = _register_and_login("admin@sureshift.in")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_second_registered_user_is_viewer_by_default():
    _register_and_login("first@sureshift.in")
    token = _register_and_login("second@sureshift.in")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["role"] == "viewer"


def test_unauthenticated_request_is_rejected():
    resp = client.get("/api/v1/businesses")
    assert resp.status_code == 401


def test_admin_can_create_and_read_business():
    token = _register_and_login("admin2@sureshift.in")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post(
        "/api/v1/businesses",
        json={
            "name": "Sure Shift Relocation Services",
            "website_url": "https://sureshift.in",
            "industry": "relocation",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    business_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/businesses/{business_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Sure Shift Relocation Services"


def test_viewer_cannot_create_business():
    _register_and_login("adminx@sureshift.in")  # becomes admin, not used further
    viewer_token = _register_and_login("viewerx@sureshift.in")  # becomes viewer

    resp = client.post(
        "/api/v1/businesses",
        json={"name": "Should Fail", "website_url": "https://example.com"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


def test_creating_business_writes_audit_log_entry():
    token = _register_and_login("audituser@sureshift.in")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/businesses",
        json={"name": "Audit Test Co", "website_url": "https://audittest.example"},
        headers=headers,
    )
    assert resp.status_code == 201
    business_id = resp.json()["id"]

    db = TestingSessionLocal()
    try:
        entry = (
            db.query(AuditLog)
            .filter(AuditLog.entity_type == "business", AuditLog.entity_id == business_id)
            .first()
        )
        assert entry is not None
        assert entry.action == "create"
        assert entry.actor_label == "user:audituser@sureshift.in"
        assert entry.after["name"] == "Audit Test Co"
    finally:
        db.close()
