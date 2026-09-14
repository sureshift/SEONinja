"""
Main crawl orchestrator. BFS over internal links, seeded from the sitemap
when available, bounded by max_pages and max_depth, respecting robots.txt,
with bounded concurrency so we don't hammer the target site.
"""
import asyncio
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from app.crawler.fetcher import FetchResult, fetch_url
from app.crawler.normalizer import is_same_domain, normalize_url
from app.crawler.parser import parse_page
from app.crawler.robots import is_allowed, load_robots_txt
from app.crawler.sitemap import discover_sitemap_urls

USER_AGENT = "SearchGrowthOS-Crawler/0.1 (+https://sureshift.in)"


@dataclass
class CrawledPageResult:
    url: str
    depth: int
    discovered_via: str
    fetch: FetchResult
    parsed: dict = field(default_factory=dict)


async def crawl_site(
    start_url: str,
    *,
    max_pages: int = 50,
    max_depth: int = 3,
    concurrency: int = 5,
) -> list[CrawledPageResult]:
    root_domain = urlparse(start_url).netloc.lstrip("www.")
    start_url = normalize_url(start_url)

    results: list[CrawledPageResult] = []
    visited: set[str] = set()
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        robots_parser = await load_robots_txt(client, start_url, USER_AGENT)

        # Seed the queue: sitemap URLs first (if any), then the start URL.
        queue: list[tuple[str, int, str]] = [(start_url, 0, "seed")]
        sitemap_urls = await discover_sitemap_urls(client, start_url)
        for sitemap_url in sitemap_urls:
            normalized = normalize_url(sitemap_url)
            if is_same_domain(normalized, root_domain):
                queue.append((normalized, 1, "sitemap"))

        async def fetch_one(url: str, depth: int, via: str) -> CrawledPageResult | None:
            async with semaphore:
                fetch_result = await fetch_url(client, url)
            parsed: dict = {}
            if fetch_result.html:
                parsed = parse_page(fetch_result.html, fetch_result.final_url, root_domain)
            return CrawledPageResult(url=url, depth=depth, discovered_via=via, fetch=fetch_result, parsed=parsed)

        while queue and len(visited) < max_pages:
            batch = []
            while queue and len(batch) < concurrency and len(visited) + len(batch) < max_pages:
                url, depth, via = queue.pop(0)
                if url in visited or depth > max_depth:
                    continue
                if not is_allowed(robots_parser, url, USER_AGENT):
                    continue
                visited.add(url)
                batch.append((url, depth, via))

            if not batch:
                break

            batch_results = await asyncio.gather(
                *(fetch_one(url, depth, via) for url, depth, via in batch)
            )

            for result in batch_results:
                if result is None:
                    continue
                results.append(result)

                for link in result.parsed.get("internal_links", []):
                    if link not in visited and len(visited) < max_pages:
                        queue.append((link, result.depth + 1, "link"))

    return results
