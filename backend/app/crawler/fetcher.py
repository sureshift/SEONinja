"""
Fetches a single URL, tracking timing and redirect chains explicitly
(httpx follows redirects automatically, but we want to know the chain,
not just the final destination - Module 3 needs to flag redirect chains
as an issue in their own right).
"""
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int | None
    content_type: str | None
    html: str | None
    response_time_ms: int | None
    redirect_chain: list[str] = field(default_factory=list)
    error: str | None = None


async def fetch_url(
    client: httpx.AsyncClient, url: str, *, timeout_seconds: float = 10.0, max_retries: int = 2
) -> FetchResult:
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        start = time.monotonic()
        try:
            response = await client.get(
                url, timeout=timeout_seconds, follow_redirects=True
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)

            redirect_chain = [str(r.url) for r in response.history]
            content_type = response.headers.get("content-type", "").split(";")[0].strip()

            html = None
            if content_type in ("text/html", "application/xhtml+xml"):
                html = response.text

            return FetchResult(
                url=url,
                final_url=str(response.url),
                status_code=response.status_code,
                content_type=content_type or None,
                html=html,
                response_time_ms=elapsed_ms,
                redirect_chain=redirect_chain,
            )
        except httpx.RequestError as exc:
            last_error = str(exc)
            continue

    return FetchResult(
        url=url,
        final_url=url,
        status_code=None,
        content_type=None,
        html=None,
        response_time_ms=None,
        error=last_error,
    )
