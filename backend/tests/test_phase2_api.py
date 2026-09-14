"""
Phase 2 API-level gate test: hits the actual /api/v1/crawl-jobs endpoint
(not just the crawler engine directly), against real Postgres and the
real local test HTTP server, and checks results persisted correctly.
"""
import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from tests.fixtures.test_site import test_app

TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/searchos_db"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_test_site():
    port = _get_free_port()
    config = uvicorn.Config(test_app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Test HTTP server did not start in time")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def clean_database():
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


def _admin_headers(email: str) -> dict:
    client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": "testpass123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_full_crawl_job_flow_via_api(live_test_site):
    headers = _admin_headers("crawladmin@sureshift.in")

    business_resp = client.post(
        "/api/v1/businesses",
        json={"name": "Test Business", "website_url": live_test_site},
        headers=headers,
    )
    assert business_resp.status_code == 201
    business_id = business_resp.json()["id"]

    crawl_resp = client.post(
        "/api/v1/crawl-jobs",
        json={"business_id": business_id, "start_url": live_test_site, "max_pages": 20, "max_depth": 3},
        headers=headers,
    )
    assert crawl_resp.status_code == 201, crawl_resp.text
    job = crawl_resp.json()
    assert job["status"] == "completed"
    assert job["pages_crawled"] > 5

    pages_resp = client.get(f"/api/v1/crawl-jobs/{job['id']}/pages", headers=headers)
    assert pages_resp.status_code == 200
    pages = pages_resp.json()
    assert len(pages) == job["pages_crawled"]
    assert any(p["title"] == "Sure Shift Test Home" for p in pages)

    issues_resp = client.get(f"/api/v1/crawl-jobs/{job['id']}/issues", headers=headers)
    assert issues_resp.status_code == 200
    issues = issues_resp.json()
    assert len(issues) > 5
    issue_types = {i["issue_type"] for i in issues}
    assert "missing_title" in issue_types
    assert "4xx_error" in issue_types


def test_viewer_cannot_start_crawl_job(live_test_site):
    _admin_headers("crawladmin2@sureshift.in")  # bootstrap admin, unused further
    viewer_headers = _admin_headers("crawlviewer@sureshift.in")  # becomes viewer

    resp = client.post(
        "/api/v1/crawl-jobs",
        json={"business_id": "00000000-0000-0000-0000-000000000000", "start_url": live_test_site},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_crawl_job_for_nonexistent_business_returns_404(live_test_site):
    headers = _admin_headers("crawladmin3@sureshift.in")
    resp = client.post(
        "/api/v1/crawl-jobs",
        json={"business_id": "00000000-0000-0000-0000-000000000000", "start_url": live_test_site},
        headers=headers,
    )
    assert resp.status_code == 404
