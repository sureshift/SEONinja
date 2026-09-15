"""
Module 12 - Content Gap Engine, scoped for Phase 4 to what's actually
available: comparing tracked keywords (Phase 3) against our own crawled
pages (Phase 2). True competitor/SERP-based gap analysis (the roadmap's
full vision) needs working competitor crawls and SERP data, neither of
which exist yet - this is the honest subset: "do we even have a page
that could rank for this keyword?"

Classification:
  missing - no crawled page's title/H1/content meaningfully overlaps the keyword
  weak    - some overlap, but thin content or poor coverage
  covered - a page substantially covers this keyword
"""
import re

WORD_RE = re.compile(r"\b\w+\b")
WEAK_WORD_COUNT_THRESHOLD = 300


def _tokenize(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower()))


def _overlap_score(keyword_tokens: set[str], page_tokens: set[str]) -> float:
    if not keyword_tokens:
        return 0.0
    return len(keyword_tokens & page_tokens) / len(keyword_tokens)


def find_content_gaps(keywords: list[dict], pages: list[dict]) -> list[dict]:
    """
    `keywords` is a list of dicts with `id` and `term`.
    `pages` is a list of dicts with `url`, `title`, `h1`, `word_count`.
    Matches each keyword against its best-covering page.
    """
    gaps: list[dict] = []

    for keyword in keywords:
        keyword_tokens = _tokenize(keyword["term"])
        best_match: dict | None = None
        best_score = 0.0

        for page in pages:
            page_text = " ".join(filter(None, [
                page.get("title") or "",
                " ".join(page.get("h1") or []),
            ]))
            page_tokens = _tokenize(page_text)
            score = _overlap_score(keyword_tokens, page_tokens)

            if score > best_score:
                best_score = score
                best_match = page

        if best_score >= 0.8:
            word_count = (best_match or {}).get("word_count") or 0
            classification = "weak" if word_count < WEAK_WORD_COUNT_THRESHOLD else "covered"
        elif best_score >= 0.3:
            classification = "weak"
        else:
            classification = "missing"
            best_match = None

        gaps.append({
            "keyword_id": keyword["id"],
            "keyword_term": keyword["term"],
            "classification": classification,
            "matched_url": best_match["url"] if best_match else None,
            "match_score": round(best_score, 2),
        })

    return gaps
