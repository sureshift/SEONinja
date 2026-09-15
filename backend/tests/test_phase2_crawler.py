"""
Phase 2 gate tests. The crawler is tested against a REAL HTTP server
(uvicorn, real sockets on localhost) serving deliberately broken pages -
not mocked responses - so redirect-following, robots.txt fetching, and
timing all go through the actual code paths they'd hit against a real site.
"""
import socket
import threading
import time

import pytest
import uvicorn

from app.crawler.crawler import crawl_site
from app.services.technical_seo import detect_issues
from tests.fixtures.test_site import test_app


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


@pytest.fixture(scope="module")
def crawl_results(live_test_site):
    import asyncio

    return asyncio.run(crawl_site(live_test_site, max_pages=30, max_depth=3))


def _find(results, path: str):
    matches = [r for r in results if r.url.endswith(path)]
    return matches[0] if matches else None


def test_crawl_discovers_all_linked_and_sitemap_pages(crawl_results):
    urls_crawled = {r.url for r in crawl_results}
    # Linked from home page:
    assert any(u.endswith("/no-title") for u in urls_crawled)
    assert any(u.endswith("/multi-h1") for u in urls_crawled)
    assert any(u.endswith("/redirect-me") for u in urls_crawled)
    # Only in sitemap.xml, not linked - must still be discovered:
    assert any(u.endswith("/orphan") for u in urls_crawled)


def test_crawl_respects_robots_txt_disallow(crawl_results):
    """The /disallowed page is linked from home but blocked in robots.txt -
    the crawler must NOT have fetched it despite the link existing."""
    urls_crawled = {r.url for r in crawl_results}
    assert not any(u.endswith("/disallowed") for u in urls_crawled)


def test_crawl_excludes_cdn_cgi_infrastructure_paths(crawl_results):
    """Discovered via a real sureshift.in crawl: Cloudflare's automatic
    email-obfuscation rewrites mailto: links to /cdn-cgi/l/email-protection,
    which is linked like a normal page but isn't real content and
    shouldn't be crawled/analyzed."""
    urls_crawled = {r.url for r in crawl_results}
    assert not any("/cdn-cgi/" in u for u in urls_crawled)


def test_crawl_follows_redirect_and_records_chain(crawl_results):
    redirect_page = _find(crawl_results, "/redirect-me")
    assert redirect_page is not None
    assert redirect_page.fetch.status_code == 200  # httpx followed it
    assert len(redirect_page.fetch.redirect_chain) == 1
    assert redirect_page.fetch.redirect_chain[0].endswith("/redirect-me")


def test_crawl_detects_404(crawl_results):
    broken = _find(crawl_results, "/broken-link-target")
    assert broken is not None
    assert broken.fetch.status_code == 404


def test_crawl_extracts_metadata_correctly(crawl_results):
    home = _find(crawl_results, "http" ) or crawl_results[0]
    home = next(r for r in crawl_results if r.depth == 0)
    assert home.parsed["title"] == "Sure Shift Test Home"
    assert home.parsed["meta_description"] == "Home page description for testing."
    assert home.parsed["h1"] == ["Welcome"]
    assert len(home.parsed["structured_data"]) == 1
    assert home.parsed["structured_data"][0]["name"] == "Test Co"
    assert home.parsed["canonical_url"] is not None


def _pages_as_dicts(crawl_results):
    return [
        {
            "url": r.url,
            "status_code": r.fetch.status_code,
            "title": r.parsed.get("title"),
            "meta_description": r.parsed.get("meta_description"),
            "h1": r.parsed.get("h1"),
            "canonical_url": r.parsed.get("canonical_url"),
            "is_noindex": r.parsed.get("is_noindex", False),
            "word_count": r.parsed.get("word_count"),
            "redirect_chain": r.fetch.redirect_chain,
            "internal_links": r.parsed.get("internal_links"),
            "discovered_via": r.discovered_via,
        }
        for r in crawl_results
    ]


def test_technical_seo_detects_every_planted_issue(crawl_results):
    issues = detect_issues(_pages_as_dicts(crawl_results))
    issue_types_found = {i["issue_type"] for i in issues}

    expected = {
        "missing_title", "missing_meta_description", "multiple_h1", "missing_h1",
        "thin_content", "noindex", "4xx_error", "redirect_chain",
        "duplicate_title", "duplicate_meta_description", "orphan_page",
        "canonical_mismatch",
    }
    missing = expected - issue_types_found
    assert not missing, f"Detector failed to flag: {missing}"


def test_technical_seo_home_page_is_clean(crawl_results):
    """The home page was built with no deliberate issues - the detector
    must not flag it for anything, i.e. no false positives."""
    home_dict = next(d for d in _pages_as_dicts(crawl_results) if d["discovered_via"] == "seed")
    issues = detect_issues([home_dict])
    assert issues == [], f"False positive(s) on clean page: {issues}"
