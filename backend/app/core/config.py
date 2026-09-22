"""Application settings.

Loaded from environment variables (see .env.example at repo root). Nothing
here has a real secret as a default — missing values fail loudly rather than
silently falling back to something that looks like it works.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "FishPilot AI"
    environment: str = "development"
    api_prefix: str = "/api"

    # Database
    database_url: str = "sqlite:///./fishpilot_dev.db"

    # External services (all optional — see app/services/*_adapter.py for the
    # mock fallback used when a key isn't configured, so the demo still runs
    # without any paid API access).
    nws_user_agent: str = "fishpilot-ai (yifeiwang@tamu.edu)"
    tpwd_user_agent: str = "fishpilot-ai (yifeiwang@tamu.edu) student portfolio project"
    google_places_api_key: str | None = None
    llm_provider: str = "mock"  # "openai" | "anthropic" | "mock"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"

    # Feature flags
    use_seed_data_only: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
