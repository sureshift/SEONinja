"""
Module 3 - Technical SEO Engine. Takes a completed crawl's pages and
produces TechnicalIssue records. Pure function over a list of dicts in,
list of issue dicts out - no DB access here, so it's trivially testable
and reusable from both the API layer and (later) the crawl worker.
"""
from collections import Counter

from app.crawler.normalizer import normalize_url

THIN_CONTENT_WORD_THRESHOLD = 200


def detect_issues(pages: list[dict]) -> list[dict]:
    """
    `pages` is a list of dicts shaped like CrawledPage columns (status_code,
    title, meta_description, h1, canonical_url, is_noindex, word_count,
    redirect_chain, url). Returns a list of issue dicts ready to become
    TechnicalIssue rows.
    """
    issues: list[dict] = []

    titles = Counter()
    descriptions = Counter()

    for page in pages:
        url = page["url"]
        status_code = page.get("status_code")

        if status_code is not None and 400 <= status_code < 500:
            issues.append(_issue("4xx_error", "high", url,
                f"Page returned {status_code}.",
                "Fix or remove the broken link/page; add a 301 redirect if the content moved."))
            continue

        if status_code is not None and status_code >= 500:
            issues.append(_issue("5xx_error", "critical", url,
                f"Page returned server error {status_code}.",
                "Investigate server logs - this affects both users and crawlers."))
            continue

        if page.get("redirect_chain"):
            chain_length = len(page["redirect_chain"])
            severity = "high" if chain_length > 2 else "medium"
            issues.append(_issue("redirect_chain", severity, url,
                f"Page went through {chain_length} redirect(s) before resolving.",
                "Point internal links directly at the final URL to avoid wasting crawl budget."))

        title = page.get("title")
        if not title:
            issues.append(_issue("missing_title", "high", url,
                "Page has no <title> tag.",
                "Add a unique, descriptive title tag (50-60 characters)."))
        else:
            titles[title] += 1

        meta_description = page.get("meta_description")
        if not meta_description:
            issues.append(_issue("missing_meta_description", "medium", url,
                "Page has no meta description.",
                "Add a unique meta description (~150-160 characters) summarizing the page."))
        else:
            descriptions[meta_description] += 1

        h1_list = page.get("h1") or []
        if len(h1_list) == 0:
            issues.append(_issue("missing_h1", "high", url,
                "Page has no H1 heading.",
                "Add exactly one H1 that reflects the page's main topic."))
        elif len(h1_list) > 1:
            issues.append(_issue("multiple_h1", "medium", url,
                f"Page has {len(h1_list)} H1 headings.",
                "Use a single H1; demote the others to H2/H3."))

        if not page.get("canonical_url"):
            issues.append(_issue("missing_canonical", "medium", url,
                "Page has no canonical tag.",
                "Add a self-referencing canonical tag unless intentionally canonicalizing elsewhere."))
        else:
            own_normalized = normalize_url(url)
            canonical_normalized = normalize_url(page["canonical_url"])
            if canonical_normalized != own_normalized:
                issues.append(_issue("canonical_mismatch", "critical", url,
                    f"Canonical tag points to a different URL ({page['canonical_url']}) "
                    "instead of this page itself.",
                    "If unintentional, fix immediately - this tells search engines this "
                    "page is NOT the canonical version, which can remove it from search "
                    "results entirely under its real URL. Only point elsewhere if "
                    "deliberately consolidating true duplicate content."))

        if page.get("is_noindex"):
            issues.append(_issue("noindex", "medium", url,
                "Page is marked noindex.",
                "Confirm this is intentional - noindex pages are excluded from search results."))

        word_count = page.get("word_count") or 0
        if 0 < word_count < THIN_CONTENT_WORD_THRESHOLD:
            issues.append(_issue("thin_content", "low", url,
                f"Page has only {word_count} words.",
                "Expand content to meaningfully cover the topic, or consolidate with a related page."))

    for title, count in titles.items():
        if count > 1:
            affected = [p["url"] for p in pages if p.get("title") == title]
            for url in affected:
                issues.append(_issue("duplicate_title", "medium", url,
                    f"Title '{title}' is used on {count} pages.",
                    "Write a unique title for each page."))

    for description, count in descriptions.items():
        if count > 1:
            affected = [p["url"] for p in pages if p.get("meta_description") == description]
            for url in affected:
                issues.append(_issue("duplicate_meta_description", "low", url,
                    f"This meta description is duplicated across {count} pages.",
                    "Write a unique meta description for each page."))

    issues.extend(_detect_orphan_pages(pages))

    return issues


def _detect_orphan_pages(pages: list[dict]) -> list[dict]:
    """A page discovered only via the sitemap, never linked internally
    from any crawled page, is orphaned - real visitors and crawl equity
    can't reach it through navigation."""
    all_internal_links: set[str] = set()
    for page in pages:
        all_internal_links.update(page.get("internal_links") or [])

    issues = []
    for page in pages:
        if page.get("discovered_via") == "sitemap" and page["url"] not in all_internal_links:
            issues.append(_issue("orphan_page", "medium", page["url"],
                "Page is in the sitemap but not linked from any other crawled page.",
                "Add at least one internal link to this page from relevant content."))
    return issues


def _issue(issue_type: str, severity: str, url: str, description: str, fix: str) -> dict:
    return {
        "issue_type": issue_type,
        "severity": severity,
        "affected_url": url,
        "description": description,
        "recommended_fix": fix,
        "auto_fix_eligible": issue_type in ("missing_meta_description",),
    }
