"""
Parses a page's HTML into the structured fields CrawledPage stores.
Deliberately pure/synchronous and side-effect free - takes HTML text in,
returns a dict out - so it's trivially testable without any network.
"""
import json
import re

from bs4 import BeautifulSoup

from app.crawler.normalizer import is_same_domain, normalize_url

WORD_RE = re.compile(r"\b\w+\b")


def parse_page(html: str, page_url: str, root_domain: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    meta_description = None
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    if meta_desc_tag and meta_desc_tag.get("content"):
        meta_description = meta_desc_tag["content"].strip()

    robots_meta = None
    robots_tag = soup.find("meta", attrs={"name": "robots"})
    if robots_tag and robots_tag.get("content"):
        robots_meta = robots_tag["content"].strip()
    is_noindex = bool(robots_meta and "noindex" in robots_meta.lower())

    viewport = None
    viewport_tag = soup.find("meta", attrs={"name": "viewport"})
    if viewport_tag and viewport_tag.get("content"):
        viewport = viewport_tag["content"].strip()

    canonical_url = None
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    if canonical_tag and canonical_tag.get("href"):
        canonical_url = normalize_url(canonical_tag["href"], base_url=page_url)

    h1 = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2 = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3 = [h.get_text(strip=True) for h in soup.find_all("h3")]

    body_text = soup.get_text(separator=" ", strip=True)
    word_count = len(WORD_RE.findall(body_text))

    internal_links: list[str] = []
    external_links: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = normalize_url(href, base_url=page_url)
        if is_same_domain(absolute, root_domain):
            internal_links.append(absolute)
        else:
            external_links.append(absolute)

    images = []
    for img_tag in soup.find_all("img"):
        images.append({
            "src": img_tag.get("src"),
            "alt": img_tag.get("alt"),
            "width": img_tag.get("width"),
            "height": img_tag.get("height"),
        })

    structured_data = []
    for script_tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            structured_data.append(json.loads(script_tag.string or "{}"))
        except (json.JSONDecodeError, TypeError):
            # Malformed JSON-LD is itself a technical issue to flag later,
            # not a reason to crash the crawl.
            continue

    open_graph = {}
    for og_tag in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
        prop = og_tag.get("property", "").replace("og:", "")
        if prop and og_tag.get("content"):
            open_graph[prop] = og_tag["content"]

    return {
        "title": title,
        "meta_description": meta_description,
        "robots_meta": robots_meta,
        "is_noindex": is_noindex,
        "viewport": viewport,
        "canonical_url": canonical_url,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "word_count": word_count,
        "internal_links": sorted(set(internal_links)),
        "external_links": sorted(set(external_links)),
        "images": images,
        "structured_data": structured_data,
        "open_graph": open_graph or None,
    }
