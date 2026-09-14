"""
SERP provider abstraction. The application must never call DataForSEO (or
any SERP source) directly - everything routes through this interface so we
can default to our own infrastructure and fall back only when necessary.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings


@dataclass
class SERPResult:
    query: str
    location: str | None
    organic_results: list[dict]
    local_pack: list[dict] | None
    featured_snippet: dict | None
    people_also_ask: list[str]
    ai_overview: dict | None
    fetched_at: str
    source: str  # which provider actually served this


class SERPProvider(ABC):
    @abstractmethod
    async def get_serp(self, query: str, *, location: str | None = None) -> SERPResult:
        ...

    @abstractmethod
    async def get_local_serp(self, query: str, *, lat: float, lng: float,
                              radius_km: float) -> SERPResult:
        ...

    @abstractmethod
    async def get_maps_results(self, query: str, *, lat: float, lng: float) -> list[dict]:
        ...

    @abstractmethod
    async def get_ai_results(self, query: str) -> dict | None:
        ...


class OwnSERPProvider(SERPProvider):
    """
    Deliberately NOT a Google SERP scraper. Scraping Google's search
    results pages directly violates Google's Terms of Service regardless
    of whether it's framed as "our own infrastructure" - that's exactly
    why the roadmap carves out DataForSEO as the sanctioned path for this
    category of data.

    This class exists for genuinely own-infrastructure-obtainable SERP
    data: Google's officially licensed Custom Search JSON API (organic
    results only, no local pack/PAA/AI Overview - Google doesn't expose
    those via any authorized API), or Bing's Web Search API. Not
    implemented in Phase 3 because no such credentials exist yet - add
    a real implementation here if/when that's needed, but full SERP
    feature parity (local pack, AI Overviews) will always route through
    DataForSEOProvider, not this class.
    """

    async def get_serp(self, query: str, *, location: str | None = None) -> SERPResult:
        raise NotImplementedError(
            "OwnSERPProvider is not a Google scraper - see class docstring. "
            "Use DataForSEOProvider for full SERP data."
        )

    async def get_local_serp(self, query: str, *, lat: float, lng: float,
                              radius_km: float) -> SERPResult:
        raise NotImplementedError("See OwnSERPProvider docstring.")

    async def get_maps_results(self, query: str, *, lat: float, lng: float) -> list[dict]:
        raise NotImplementedError("See OwnSERPProvider docstring.")

    async def get_ai_results(self, query: str) -> dict | None:
        raise NotImplementedError("See OwnSERPProvider docstring.")


class DataForSEOProvider(SERPProvider):
    """
    Real implementation against DataForSEO's SERP API (v3, "live/regular"
    endpoint - synchronous, single request/response, no task polling).

    IMPORTANT: this is built against DataForSEO's publicly documented API
    contract, but has NOT been smoke-tested against a live account (no
    credentials were available while building this). Field names below
    are the documented ones as of this build, but DataForSEO's API
    surface can change - verify the actual response shape against a
    real call before trusting this in production, and adjust the
    _parse_* methods if anything doesn't match.
    """

    BASE_URL = "https://api.dataforseo.com/v3"  # overridden by settings.dataforseo_base_url unless explicitly passed

    def __init__(self, login: str | None = None, password: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.login = login or settings.dataforseo_login
        self.password = password or settings.dataforseo_password
        self.base_url = base_url or settings.dataforseo_base_url or self.BASE_URL

    async def _post(self, path: str, payload: list[dict]) -> dict:
        if not self.login or not self.password:
            raise RuntimeError(
                "DataForSEO credentials not configured (dataforseo_login / "
                "dataforseo_password). Set them before using this provider."
            )
        async with httpx.AsyncClient(auth=(self.login, self.password), timeout=30.0) as client:
            response = await client.post(f"{self.base_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()

    async def get_serp(self, query: str, *, location: str | None = None) -> SERPResult:
        payload = [{
            "keyword": query,
            "language_code": "en",
            "location_name": location or "India",
            "device": "desktop",
        }]
        response = await self._post("/serp/google/organic/live/regular", payload)
        return self._parse_organic_response(query, location, response)

    async def get_local_serp(self, query: str, *, lat: float, lng: float,
                              radius_km: float) -> SERPResult:
        payload = [{
            "keyword": query,
            "language_code": "en",
            "location_coordinate": f"{lat},{lng},{int(radius_km)}",
            "device": "desktop",
        }]
        response = await self._post("/serp/google/organic/live/regular", payload)
        return self._parse_organic_response(query, f"{lat},{lng}", response)

    async def get_maps_results(self, query: str, *, lat: float, lng: float) -> list[dict]:
        payload = [{
            "keyword": query,
            "language_code": "en",
            "location_coordinate": f"{lat},{lng},10",
        }]
        response = await self._post("/serp/google/maps/live/regular", payload)
        try:
            return response["tasks"][0]["result"][0]["items"] or []
        except (KeyError, IndexError, TypeError):
            return []

    async def get_ai_results(self, query: str) -> dict | None:
        """AI Overview data, when DataForSEO's response includes it as an
        item type within the standard organic SERP response."""
        payload = [{"keyword": query, "language_code": "en", "location_name": "India"}]
        response = await self._post("/serp/google/organic/live/regular", payload)
        return self._extract_item_type(response, "ai_overview")

    def _parse_organic_response(self, query: str, location: str | None, response: dict) -> SERPResult:
        items = self._get_items(response)
        return SERPResult(
            query=query,
            location=location,
            organic_results=[i for i in items if i.get("type") == "organic"],
            local_pack=[i for i in items if i.get("type") == "local_pack"] or None,
            featured_snippet=self._extract_item_type(response, "featured_snippet"),
            people_also_ask=[
                q.get("title", "") for i in items if i.get("type") == "people_also_ask"
                for q in i.get("items", [])
            ],
            ai_overview=self._extract_item_type(response, "ai_overview"),
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="dataforseo",
        )

    @staticmethod
    def _get_items(response: dict) -> list[dict]:
        try:
            return response["tasks"][0]["result"][0]["items"] or []
        except (KeyError, IndexError, TypeError):
            return []

    def _extract_item_type(self, response: dict, item_type: str) -> dict | None:
        for item in self._get_items(response):
            if item.get("type") == item_type:
                return item
        return None


def get_serp_provider(provider_name: str) -> SERPProvider:
    providers = {
        "own": OwnSERPProvider,
        "dataforseo": DataForSEOProvider,
    }
    if provider_name not in providers:
        raise ValueError(f"Unknown SERP provider: {provider_name}")
    return providers[provider_name]()
