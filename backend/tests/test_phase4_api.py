"""
Phase 4 API-level gate test: crawls the real local test site (reusing
Phase 2's fixture), then runs every Phase 4 analysis endpoint against the
resulting real crawl data in real Postgres - the full pipeline, not
isolated units.
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


def _setup_business_and_crawl(headers: dict, live_test_site: str) -> tuple[str, str]:
    business_resp = client.post(
        "/api/v1/businesses",
        json={"name": "Test Business", "website_url": live_test_site},
        headers=headers,
    )
    business_id = business_resp.json()["id"]

    crawl_resp = client.post(
        "/api/v1/crawl-jobs",
        json={"business_id": business_id, "start_url": live_test_site, "max_pages": 20, "max_depth": 3},
        headers=headers,
    )
    return business_id, crawl_resp.json()["id"]


def test_page_quality_analysis_end_to_end(live_test_site):
    headers = _admin_headers("p4user1@sureshift.in")
    _, crawl_job_id = _setup_business_and_crawl(headers, live_test_site)

    analyze_resp = client.post(f"/api/v1/crawl-jobs/{crawl_job_id}/analyze/quality", headers=headers)
    assert analyze_resp.status_code == 200
    scores = analyze_resp.json()
    assert len(scores) > 5
    assert all(0 <= s["overall_score"] <= 100 for s in scores)

    # Persisted, not just returned
    get_resp = client.get(f"/api/v1/crawl-jobs/{crawl_job_id}/quality", headers=headers)
    assert len(get_resp.json()) == len(scores)

    # The deliberately clean home page should score meaningfully higher
    # than the deliberately broken thin/no-title pages
    home_score = next(s for s in scores if s["url"].rstrip("/") == live_test_site)
    thin_score = next(s for s in scores if s["url"].endswith("/thin"))
    assert home_score["overall_score"] > thin_score["overall_score"]


def test_schema_recommendations_end_to_end(live_test_site):
    headers = _admin_headers("p4user2@sureshift.in")
    _, crawl_job_id = _setup_business_and_crawl(headers, live_test_site)

    analyze_resp = client.post(f"/api/v1/crawl-jobs/{crawl_job_id}/analyze/schema", headers=headers)
    assert analyze_resp.status_code == 200
    recs = analyze_resp.json()
    # Home page has no LocalBusiness/Organization schema in the test fixture
    home_recs = [r for r in recs if r["url"].rstrip("/") == live_test_site]
    assert any(r["recommended_type"] == "LocalBusiness" for r in home_recs)
    # Never fabricates address/phone
    local_biz = next(r for r in home_recs if r["recommended_type"] == "LocalBusiness")
    assert "address" not in local_biz["suggested_jsonld"]


def test_image_issues_end_to_end(live_test_site):
    headers = _admin_headers("p4user3@sureshift.in")
    _, crawl_job_id = _setup_business_and_crawl(headers, live_test_site)

    resp = client.get(f"/api/v1/crawl-jobs/{crawl_job_id}/image-issues", headers=headers)
    assert resp.status_code == 200
    issues = resp.json()
    # Home page has an <img src="/no-alt.png"> with no alt attribute
    assert any(i["issue_type"] == "missing_alt_text" for i in issues)


def test_internal_linking_end_to_end(live_test_site):
    headers = _admin_headers("p4user4@sureshift.in")
    _, crawl_job_id = _setup_business_and_crawl(headers, live_test_site)

    resp = client.get(f"/api/v1/crawl-jobs/{crawl_job_id}/internal-linking", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_content_gap_end_to_end(live_test_site):
    headers = _admin_headers("p4user5@sureshift.in")
    business_id, crawl_job_id = _setup_business_and_crawl(headers, live_test_site)

    # Wait for crawl to be completed (it's synchronous, but confirm)
    job = client.get(f"/api/v1/crawl-jobs/{crawl_job_id}", headers=headers).json()
    assert job["status"] == "completed"

    client.post(
        "/api/v1/keywords",
        json={"business_id": business_id, "term": "sure shift test home"},
        headers=headers,
    )
    client.post(
        "/api/v1/keywords",
        json={"business_id": business_id, "term": "completely unrelated topic xyz"},
        headers=headers,
    )

    analyze_resp = client.post(f"/api/v1/businesses/{business_id}/content-gaps", headers=headers)
    assert analyze_resp.status_code == 200
    gaps = analyze_resp.json()

    home_gap = next(g for g in gaps if g["keyword_term"] == "sure shift test home")
    unrelated_gap = next(g for g in gaps if g["keyword_term"] == "completely unrelated topic xyz")
    assert home_gap["classification"] in ("covered", "weak")
    assert unrelated_gap["classification"] == "missing"

    # Persisted and replaces on re-run
    get_resp = client.get(f"/api/v1/businesses/{business_id}/content-gaps", headers=headers)
    assert len(get_resp.json()) == 2


def test_content_decay_requires_two_crawls(live_test_site):
    headers = _admin_headers("p4user6@sureshift.in")
    business_id, _ = _setup_business_and_crawl(headers, live_test_site)

    # Only one crawl exists yet
    resp = client.post(f"/api/v1/businesses/{business_id}/content-decay", headers=headers)
    assert resp.status_code == 400

    # Second crawl of the same (unchanged) site
    client.post(
        "/api/v1/crawl-jobs",
        json={"business_id": business_id, "start_url": live_test_site, "max_pages": 20, "max_depth": 3},
        headers=headers,
    )

    resp2 = client.post(f"/api/v1/businesses/{business_id}/content-decay", headers=headers)
    assert resp2.status_code == 200
    # Site didn't change between crawls, so no decay alerts expected
    assert resp2.json() == []


def test_viewer_cannot_trigger_analysis(live_test_site):
    _admin_headers("p4user7a@sureshift.in")
    viewer_headers = _admin_headers("p4user7b@sureshift.in")

    resp = client.post(
        "/api/v1/crawl-jobs/00000000-0000-0000-0000-000000000000/analyze/quality",
        headers=viewer_headers,
    )
    assert resp.status_code == 403
