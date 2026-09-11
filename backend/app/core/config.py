"""
Centralized configuration. Every setting comes from environment variables -
nothing is hard-coded, so this same codebase can later serve any business,
not just Sure Shift.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # Database
    database_url: str = "postgresql+psycopg://searchos:searchos@postgres:5432/searchos"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # LLM providers (configurable, never hard-coded to one model)
    llm_provider: str = "ollama"  # ollama | lmstudio | cloud
    ollama_base_url: str = "http://ollama:11434"
    lmstudio_base_url: str = "http://lmstudio:1234"

    # SERP provider
    serp_provider: str = "own"  # own | dataforseo
    dataforseo_login: str = ""
    dataforseo_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
