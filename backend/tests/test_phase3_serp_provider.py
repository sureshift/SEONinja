"""
DataForSEOProvider tested against a REAL local HTTP server standing in
for api.dataforseo.com - real sockets, real basic auth header, real JSON
parsing. Confirms the client's request/response handling actually works,
even though the exact live-API field mapping still needs verification
against a real DataForSEO account (see provider docstring).
"""
import socket
import threading
import time

import pytest
import uvicorn

from app.providers.serp_provider import DataForSEOProvider, OwnSERPProvider
from tests.fixtures.mock_dataforseo import mock_dataforseo_app


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def mock_dataforseo_server():
    port = _get_free_port()
    config = uvicorn.Config(mock_dataforseo_app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Mock DataForSEO server did not start in time")
    yield f"http://127.0.0.1:{port}/v3"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def provider(mock_dataforseo_server):
    return DataForSEOProvider(login="testuser", password="testpass", base_url=mock_dataforseo_server)


@pytest.mark.anyio
async def test_get_serp_parses_organic_results(provider):
    result = await provider.get_serp("packers and movers delhi")
    assert len(result.organic_results) == 3
    assert result.organic_results[1]["domain"] == "sureshift.in"
    assert result.source == "dataforseo"


@pytest.mark.anyio
async def test_get_serp_parses_people_also_ask(provider):
    result = await provider.get_serp("packers and movers delhi")
    assert "How much do movers cost?" in result.people_also_ask
    assert len(result.people_also_ask) == 2


@pytest.mark.anyio
async def test_get_serp_parses_featured_snippet_and_local_pack(provider):
    result = await provider.get_serp("packers and movers delhi")
    assert result.featured_snippet["url"] == "https://competitor-a.com/movers"
    assert result.local_pack[0]["title"] == "Sure Shift Relocation"


@pytest.mark.anyio
async def test_wrong_credentials_raise_http_error(mock_dataforseo_server):
    bad_provider = DataForSEOProvider(login="wrong", password="wrong", base_url=mock_dataforseo_server)
    with pytest.raises(Exception):  # httpx.HTTPStatusError from raise_for_status()
        await bad_provider.get_serp("packers and movers delhi")


@pytest.mark.anyio
async def test_missing_credentials_raises_before_network_call():
    provider_no_creds = DataForSEOProvider(login="", password="", base_url="http://unreachable.invalid")
    with pytest.raises(RuntimeError, match="credentials not configured"):
        await provider_no_creds.get_serp("test")


@pytest.mark.anyio
async def test_upstream_5xx_propagates_as_error(provider):
    with pytest.raises(Exception):
        await provider.get_serp("trigger-error")


@pytest.mark.anyio
async def test_get_maps_results(provider):
    results = await provider.get_maps_results("packers and movers", lat=28.6, lng=77.0)
    assert len(results) == 2
    assert results[0]["title"] == "Sure Shift Relocation"


@pytest.mark.anyio
async def test_own_serp_provider_is_not_a_scraper_stub():
    """Confirms OwnSERPProvider deliberately raises rather than silently
    doing nothing or (worse) actually scraping Google."""
    own = OwnSERPProvider()
    with pytest.raises(NotImplementedError, match="not a Google scraper"):
        await own.get_serp("test query")
