"""
LLM provider abstraction. No module in this system should ever import
Ollama, LM Studio, or a cloud SDK directly - everything goes through this
interface so the underlying model is swappable via config, not code changes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    raw: dict | None = None


class LLMProvider(ABC):
    """Base interface every LLM backend must implement."""

    @abstractmethod
    async def generate(self, prompt: str, *, system: str | None = None,
                        temperature: float = 0.2) -> LLMResponse:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class OllamaProvider(LLMProvider):
    """Implemented in Phase 1+. Stub only for now."""

    async def generate(self, prompt: str, *, system: str | None = None,
                        temperature: float = 0.2) -> LLMResponse:
        raise NotImplementedError("OllamaProvider implemented in a later phase")

    async def health_check(self) -> bool:
        return False


class LMStudioProvider(LLMProvider):
    """Implemented in Phase 1+. Stub only for now."""

    async def generate(self, prompt: str, *, system: str | None = None,
                        temperature: float = 0.2) -> LLMResponse:
        raise NotImplementedError("LMStudioProvider implemented in a later phase")

    async def health_check(self) -> bool:
        return False


def get_llm_provider(provider_name: str) -> LLMProvider:
    """Factory - swap providers via config, never via code edits elsewhere."""
    providers = {
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
    }
    if provider_name not in providers:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    return providers[provider_name]()
