"""
SERP provider abstraction. The application must never call DataForSEO (or
any SERP source) directly - everything routes through this interface so we
can default to our own infrastructure and fall back only when necessary.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


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
    """Implemented in Phase 3. Stub only for now."""

    async def get_serp(self, query: str, *, location: str | None = None) -> SERPResult:
        raise NotImplementedError("OwnSERPProvider implemented in Phase 3")

    async def get_local_serp(self, query: str, *, lat: float, lng: float,
                              radius_km: float) -> SERPResult:
        raise NotImplementedError("OwnSERPProvider implemented in Phase 3")

    async def get_maps_results(self, query: str, *, lat: float, lng: float) -> list[dict]:
        raise NotImplementedError("OwnSERPProvider implemented in Phase 3")

    async def get_ai_results(self, query: str) -> dict | None:
        raise NotImplementedError("OwnSERPProvider implemented in Phase 3")


class DataForSEOProvider(SERPProvider):
    """Fallback provider - implemented in Phase 3 only if own infra can't
    reliably cover a given data need."""

    async def get_serp(self, query: str, *, location: str | None = None) -> SERPResult:
        raise NotImplementedError("DataForSEOProvider implemented in Phase 3")

    async def get_local_serp(self, query: str, *, lat: float, lng: float,
                              radius_km: float) -> SERPResult:
        raise NotImplementedError("DataForSEOProvider implemented in Phase 3")

    async def get_maps_results(self, query: str, *, lat: float, lng: float) -> list[dict]:
        raise NotImplementedError("DataForSEOProvider implemented in Phase 3")

    async def get_ai_results(self, query: str) -> dict | None:
        raise NotImplementedError("DataForSEOProvider implemented in Phase 3")


def get_serp_provider(provider_name: str) -> SERPProvider:
    providers = {
        "own": OwnSERPProvider,
        "dataforseo": DataForSEOProvider,
    }
    if provider_name not in providers:
        raise ValueError(f"Unknown SERP provider: {provider_name}")
    return providers[provider_name]()
