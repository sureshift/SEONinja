"""
XML sitemap parsing, including sitemap indexes (a sitemap of sitemaps).
"""
from urllib.parse import urljoin

import httpx
from lxml import etree

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


async def discover_sitemap_urls(
    client: httpx.AsyncClient, root_url: str, *, max_sitemaps: int = 20
) -> list[str]:
    """Returns every page URL found across the sitemap(s), following one
    level of sitemap-index nesting. Returns an empty list on any failure -
    the crawler falls back to link-following in that case, it doesn't error out.

    Sitemap <loc> entries are supposed to be absolute per spec, but we
    resolve them against root_url via urljoin anyway - it's a no-op for
    already-absolute URLs and makes the parser robust to malformed
    sitemaps that use relative paths."""
    sitemap_url = urljoin(root_url, "/sitemap.xml")
    try:
        response = await client.get(sitemap_url, timeout=10.0)
        if response.status_code != 200:
            return []
        root = etree.fromstring(response.content)
    except (httpx.RequestError, etree.XMLSyntaxError):
        return []

    tag = etree.QName(root.tag).localname

    if tag == "sitemapindex":
        page_urls: list[str] = []
        sub_sitemap_urls = [
            urljoin(root_url, loc.text.strip())
            for loc in root.findall(".//sm:sitemap/sm:loc", SITEMAP_NS)
            if loc.text
        ][:max_sitemaps]
        for sub_url in sub_sitemap_urls:
            try:
                sub_response = await client.get(sub_url, timeout=10.0)
                if sub_response.status_code != 200:
                    continue
                sub_root = etree.fromstring(sub_response.content)
                page_urls.extend(
                    urljoin(root_url, loc.text.strip())
                    for loc in sub_root.findall(".//sm:url/sm:loc", SITEMAP_NS)
                    if loc.text
                )
            except (httpx.RequestError, etree.XMLSyntaxError):
                continue
        return page_urls

    # Plain urlset
    return [
        urljoin(root_url, loc.text.strip())
        for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS)
        if loc.text
    ]
