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
    app_name: str = "FishMate"
    environment: str = "development"
    api_prefix: str = "/api"

    # Database
    database_url: str = "sqlite:///./fishpilot_dev.db"

    # External services (all optional — see app/services/*_adapter.py for the
    # mock fallback used when a key isn't configured, so the demo still runs
    # without any paid API access).
    # No personal email hardcoded here — this repo is public, and a
    # User-Agent string is purely a courtesy identifier for the target
    # server's admin, not something that needs a real contact baked into
    # git history forever. Override via .env (gitignored) with a real
    # address if you actually want one used for live requests.
    nws_user_agent: str = "fishmate (github.com/pwzerus/FishEye)"
    tpwd_user_agent: str = "fishmate (github.com/pwzerus/FishEye) student portfolio project"
    # Nominatim's usage policy requires an identifying User-Agent (same
    # courtesy-not-secret shape as the other two above) — see
    # docs/adr/0009-geocoding.md for why this app never calls Nominatim
    # from the browser.
    nominatim_user_agent: str = "fishmate (github.com/pwzerus/FishEye)"
    google_places_api_key: str | None = None
    llm_provider: str = "mock"  # "openai" | "anthropic" | "mock"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"

    # Admin-only endpoints (e.g. manual data-refresh triggers). None means
    # "not configured" — routes gated on this must refuse all requests
    # rather than fall back to an open/unauthenticated endpoint. Set via
    # .env (gitignored), never hardcode a real token here.
    admin_api_token: str | None = None

    # Feature flags
    use_seed_data_only: bool = True
    # GBIF species records carry their own licences; about 12% of Texas's are
    # CC BY-NC (non-commercial), mostly iNaturalist. Fine for a portfolio
    # project; set true before any commercial use and only CC0 / CC BY
    # records are shown. See docs/commercialization.md.
    gbif_exclude_noncommercial: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
