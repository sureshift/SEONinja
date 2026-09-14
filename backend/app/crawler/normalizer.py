"""
URL normalization. Every URL that enters the crawl queue or gets stored
goes through here first - without this, http vs https, trailing slashes,
and tracking params would all be treated as different pages and blow up
the crawl budget with duplicates.
"""
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

# Query params that never change page content - strip them so
# ?utm_source=... doesn't create a fake duplicate of a page.
TRACKING_PARAM_PREFIXES = ("utm_", "fbclid", "gclid", "ref", "mc_")


def normalize_url(url: str, base_url: str | None = None) -> str:
    if base_url:
        url = urljoin(base_url, url)

    url, _ = urldefrag(url)  # drop #fragment
    parsed = urlparse(url)

    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()

    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = [
        pair
        for pair in parsed.query.split("&")
        if pair and not pair.split("=")[0].lower().startswith(TRACKING_PARAM_PREFIXES)
    ]
    query = "&".join(sorted(query_pairs))

    return urlunparse((scheme, netloc, path, "", query, ""))


def is_same_domain(url: str, root_domain: str) -> bool:
    return urlparse(url).netloc.lower().lstrip("www.") == root_domain.lower().lstrip("www.")
