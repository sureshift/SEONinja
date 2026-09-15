"""
Module 26 - Image SEO. Analyzes images captured during a crawl. Pure
function, extends the same pattern as technical_seo.py.
"""

GENERIC_FILENAME_PATTERNS = ("img", "image", "photo", "dsc", "untitled", "screenshot")


def analyze_images(pages: list[dict]) -> list[dict]:
    """
    `pages` is a list of dicts with `url` and `images` (list of
    {src, alt, width, height}), as stored on CrawledPage.
    """
    issues: list[dict] = []

    for page in pages:
        url = page["url"]
        for image in page.get("images") or []:
            src = image.get("src") or ""

            if not image.get("alt"):
                issues.append(_issue("missing_alt_text", "medium", url, src,
                    "Image has no alt text.",
                    "Add descriptive alt text - improves accessibility and image search visibility."))

            filename = src.rsplit("/", 1)[-1].lower()
            if any(pattern in filename for pattern in GENERIC_FILENAME_PATTERNS):
                issues.append(_issue("generic_filename", "low", url, src,
                    f"Image filename '{filename}' is generic and not descriptive.",
                    "Rename to a descriptive, keyword-relevant filename before re-uploading."))

            if not image.get("width") or not image.get("height"):
                issues.append(_issue("missing_dimensions", "low", url, src,
                    "Image has no explicit width/height attributes.",
                    "Add explicit dimensions to prevent layout shift (helps Core Web Vitals)."))

    return issues


def _issue(issue_type: str, severity: str, page_url: str, image_src: str, description: str, fix: str) -> dict:
    return {
        "issue_type": issue_type,
        "severity": severity,
        "affected_url": page_url,
        "image_src": image_src,
        "description": description,
        "recommended_fix": fix,
    }
