"""
Module 9 - Rank Tracking. Given a SERP result and our own site's domain,
finds our position (if we're in the captured results at all) and returns
enough to build a RankRecord row. Pure function - no DB access.
"""
from urllib.parse import urlparse


def extract_own_rank(organic_results: list[dict], our_domain: str) -> dict:
    """
    organic_results: list of {"position": int, "url": str, ...} as stored
    on a SERPSnapshot. Returns {"position": int|None, "url": str|None} -
    position is None if our domain doesn't appear in the captured results
    at all (doesn't mean we're not ranked - just not in what was captured).
    """
    our_domain = our_domain.lower().lstrip("www.")

    for result in organic_results:
        url = result.get("url") or result.get("link") or ""
        domain = urlparse(url).netloc.lower().lstrip("www.")
        if domain == our_domain:
            return {"position": result.get("position"), "url": url}

    return {"position": None, "url": None}


def detect_rank_change(previous_position: int | None, current_position: int | None) -> dict:
    """
    Classifies a rank change between two RankRecords for the same keyword.
    Both None (never ranked, still not ranked) -> "unranked".
    """
    if previous_position is None and current_position is None:
        return {"change_type": "unranked", "delta": None}
    if previous_position is None and current_position is not None:
        return {"change_type": "newly_ranked", "delta": None}
    if previous_position is not None and current_position is None:
        return {"change_type": "dropped_out", "delta": None}

    delta = previous_position - current_position  # positive = improved (moved up)
    if delta > 0:
        return {"change_type": "gained", "delta": delta}
    if delta < 0:
        return {"change_type": "lost", "delta": delta}
    return {"change_type": "unchanged", "delta": 0}
