"""
Module 4 - Page Quality Engine. Explicitly explainable: every score comes
with the component breakdown and human-readable reasons, per the
roadmap's "Do NOT use simplistic arbitrary 'SEO scores'" instruction.

Pure function over a CrawledPage-shaped dict in, score dict out.
"""

# Component weights - sum to 100. Documented here so the weighting is a
# visible, adjustable decision, not buried in the math.
WEIGHTS = {
    "content_depth": 25,
    "structure": 20,
    "metadata": 20,
    "structured_data": 15,
    "internal_linking": 10,
    "media": 10,
}

WORD_COUNT_GOOD_THRESHOLD = 600
WORD_COUNT_OK_THRESHOLD = 300


def score_page(page: dict) -> dict:
    """
    `page` is a dict shaped like CrawledPage columns: title,
    meta_description, h1, h2, word_count, structured_data, open_graph,
    internal_links, images, canonical_url.
    """
    scores: dict[str, float] = {}
    reasons: list[str] = []

    # Content depth
    word_count = page.get("word_count") or 0
    if word_count >= WORD_COUNT_GOOD_THRESHOLD:
        scores["content_depth"] = 100.0
    elif word_count >= WORD_COUNT_OK_THRESHOLD:
        scores["content_depth"] = 60.0
        reasons.append(f"Content depth is moderate ({word_count} words) - consider expanding toward {WORD_COUNT_GOOD_THRESHOLD}+.")
    else:
        scores["content_depth"] = 20.0
        reasons.append(f"Content is thin ({word_count} words) - well below the {WORD_COUNT_OK_THRESHOLD}-word baseline for meaningful topic coverage.")

    # Structure (headings)
    h1 = page.get("h1") or []
    h2 = page.get("h2") or []
    structure_score = 100.0
    if len(h1) == 0:
        structure_score -= 50
        reasons.append("No H1 heading - page lacks a clear primary topic signal.")
    elif len(h1) > 1:
        structure_score -= 20
        reasons.append(f"{len(h1)} H1 headings found - should be exactly one.")
    if len(h2) == 0 and word_count > WORD_COUNT_OK_THRESHOLD:
        structure_score -= 20
        reasons.append("No H2 subheadings on a substantial page - content may be hard to scan.")
    scores["structure"] = max(structure_score, 0.0)

    # Metadata
    metadata_score = 100.0
    if not page.get("title"):
        metadata_score -= 50
        reasons.append("Missing title tag.")
    if not page.get("meta_description"):
        metadata_score -= 30
        reasons.append("Missing meta description.")
    if not page.get("canonical_url"):
        metadata_score -= 20
        reasons.append("Missing canonical tag.")
    scores["metadata"] = max(metadata_score, 0.0)

    # Structured data
    structured_data = page.get("structured_data") or []
    open_graph = page.get("open_graph") or {}
    if structured_data:
        scores["structured_data"] = 70.0 if not open_graph else 100.0
        if not open_graph:
            reasons.append("Has JSON-LD structured data but no Open Graph tags - social sharing previews will be generic.")
    else:
        scores["structured_data"] = 0.0
        reasons.append("No structured data (JSON-LD) found - missed opportunity for rich results.")

    # Internal linking
    internal_links = page.get("internal_links") or []
    if len(internal_links) >= 5:
        scores["internal_linking"] = 100.0
    elif len(internal_links) >= 1:
        scores["internal_linking"] = 50.0
        reasons.append(f"Only {len(internal_links)} internal link(s) - consider linking to more related pages.")
    else:
        scores["internal_linking"] = 0.0
        reasons.append("No internal links found on this page - a dead end for both users and crawl equity.")

    # Media
    images = page.get("images") or []
    if not images:
        scores["media"] = 50.0  # neutral, not every page needs images
    else:
        images_with_alt = sum(1 for img in images if img.get("alt"))
        alt_ratio = images_with_alt / len(images)
        scores["media"] = alt_ratio * 100.0
        if alt_ratio < 1.0:
            missing = len(images) - images_with_alt
            reasons.append(f"{missing} of {len(images)} image(s) missing alt text.")

    overall = sum(scores[k] * (WEIGHTS[k] / 100.0) for k in WEIGHTS)

    return {
        "overall_score": round(overall, 1),
        "component_scores": {k: round(v, 1) for k, v in scores.items()},
        "explanation": reasons,
    }
