"""
Phase 0 gate test: the app must import cleanly and the health endpoint
must respond correctly. This is the Definition of Done check for Phase 0.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["phase"] == "0"


def test_root_returns_message():
    response = client.get("/")
    assert response.status_code == 200
    assert "Phase 0" in response.json()["message"]


def test_llm_provider_factory_raises_on_unknown():
    from app.providers.llm_provider import get_llm_provider

    try:
        get_llm_provider("nonexistent")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_serp_provider_factory_raises_on_unknown():
    from app.providers.serp_provider import get_serp_provider

    try:
        get_serp_provider("nonexistent")
        assert False, "should have raised ValueError"
    except ValueError:
        pass
