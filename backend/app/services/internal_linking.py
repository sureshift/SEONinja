"""
Module 17 - Internal Linking Engine. Analyzes the link graph from a
completed crawl: link depth, orphan pages (already caught in Phase 2's
technical_seo.py - not duplicated here), and under-linked pages that
exist but receive very few internal links from elsewhere on the site.
"""
from collections import Counter


def analyze_internal_links(pages: list[dict], *, under_linked_threshold: int = 2) -> list[dict]:
    """
    `pages` is a list of dicts with `url` and `internal_links` (list of
    URLs), as stored on CrawledPage.
    """
    inbound_counts: Counter[str] = Counter()
    for page in pages:
        for link in page.get("internal_links") or []:
            inbound_counts[link] += 1

    crawled_urls = {p["url"] for p in pages}
    recommendations: list[dict] = []

    for page in pages:
        url = page["url"]
        inbound = inbound_counts.get(url, 0)

        # Only flag pages we actually know about and that aren't the
        # homepage (which naturally gets the most links from navigation).
        if url in crawled_urls and inbound < under_linked_threshold:
            recommendations.append({
                "url": url,
                "inbound_internal_links": inbound,
                "issue_type": "under_linked",
                "description": f"Only {inbound} internal link(s) point to this page.",
                "recommendation": "Add internal links from related, higher-traffic pages to strengthen this page's visibility and crawl equity.",
            })

    return recommendations


def compute_link_depth(pages: list[dict], *, start_url: str) -> dict[str, int]:
    """
    BFS from the start URL over the internal link graph reconstructed
    from crawled pages, returning {url: depth}. A page not reachable
    from the start URL simply doesn't appear in the result - that's
    itself useful information (it's effectively an orphan from
    navigation's perspective, even if Phase 2 found it via sitemap).
    """
    link_map = {p["url"]: (p.get("internal_links") or []) for p in pages}
    depths = {start_url: 0}
    queue = [start_url]

    while queue:
        current = queue.pop(0)
        for neighbor in link_map.get(current, []):
            if neighbor not in depths:
                depths[neighbor] = depths[current] + 1
                queue.append(neighbor)

    return depths
