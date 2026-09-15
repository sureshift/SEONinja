"""
Module 13 - Content Decay Engine. Diffs two crawls of the same business
(Phase 2 keeps every crawl as history specifically so this is possible)
and flags pages that got meaningfully worse between them.
"""

WORD_COUNT_DROP_THRESHOLD_PCT = 0.25  # flag if word count dropped by 25%+


def detect_decay(previous_pages: list[dict], current_pages: list[dict]) -> list[dict]:
    """
    Both args are lists of dicts with url, word_count, h1, structured_data,
    title, as stored on CrawledPage, from two different CrawlJobs for the
    same business. Only URLs present in BOTH crawls are compared - a URL
    that disappeared entirely is a technical_seo 404/orphan concern, not
    decay.
    """
    previous_by_url = {p["url"]: p for p in previous_pages}
    alerts: list[dict] = []

    for current in current_pages:
        url = current["url"]
        previous = previous_by_url.get(url)
        if not previous:
            continue

        prev_words = previous.get("word_count") or 0
        curr_words = current.get("word_count") or 0
        if prev_words > 0:
            drop_pct = (prev_words - curr_words) / prev_words
            if drop_pct >= WORD_COUNT_DROP_THRESHOLD_PCT:
                alerts.append({
                    "url": url,
                    "decay_type": "word_count_drop",
                    "description": f"Word count dropped from {prev_words} to {curr_words} ({drop_pct:.0%} decrease).",
                    "severity": "high" if drop_pct >= 0.5 else "medium",
                })

        prev_structured = bool(previous.get("structured_data"))
        curr_structured = bool(current.get("structured_data"))
        if prev_structured and not curr_structured:
            alerts.append({
                "url": url,
                "decay_type": "lost_structured_data",
                "description": "Page previously had JSON-LD structured data; it's now missing.",
                "severity": "medium",
            })

        prev_h1 = previous.get("h1") or []
        curr_h1 = current.get("h1") or []
        if prev_h1 and not curr_h1:
            alerts.append({
                "url": url,
                "decay_type": "lost_h1",
                "description": f"Page previously had an H1 ('{prev_h1[0]}'); it's now missing.",
                "severity": "high",
            })

        prev_title = previous.get("title")
        curr_title = current.get("title")
        if prev_title and curr_title and prev_title != curr_title:
            alerts.append({
                "url": url,
                "decay_type": "title_changed",
                "description": f"Title changed from '{prev_title}' to '{curr_title}'.",
                "severity": "low",
            })

    return alerts
