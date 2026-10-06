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
    app_name: str = "FishEye"
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
    nws_user_agent: str = "fisheye (github.com/pwzerus/FishEye)"
    tpwd_user_agent: str = "fisheye (github.com/pwzerus/FishEye) student portfolio project"
    # Nominatim's usage policy requires an identifying User-Agent (same
    # courtesy-not-secret shape as the other two above) — see
    # docs/adr/0009-geocoding.md for why this app never calls Nominatim
    # from the browser.
    nominatim_user_agent: str = "fisheye (github.com/pwzerus/FishEye)"
    # Wikimedia's API policy asks for an identifying User-Agent too.
    wikimedia_user_agent: str = "fisheye/0.1 (github.com/pwzerus/FishEye)"
    # Real fish photos on the guide pages (services/species_photos.py).
    # False = illustrations only, and no calls to Wikipedia.
    species_photos_enabled: bool = True
    google_places_api_key: str | None = None
    llm_provider: str = "mock"  # "mock" | "anthropic" ("openai" not implemented)
    llm_api_key: str | None = None
    # Empty means the provider's own default (anthropic: claude-haiku-4-5).
    llm_model: str | None = None

    # Admin-only endpoints (e.g. manual data-refresh triggers). None means
    # "not configured" — routes gated on this must refuse all requests
    # rather than fall back to an open/unauthenticated endpoint. Set via
    # .env (gitignored), never hardcode a real token here.
    admin_api_token: str | None = None

    # Accounts and community pins (docs/adr/0016-accounts-and-community-pins.md)
    # The browser origin of the frontend: CORS, the CSRF origin check, and
    # where OAuth sends people back to.
    frontend_origin: str = "http://localhost:3000"
    # This API as the browser reaches it; Google's redirect URI is built on it.
    api_public_url: str = "http://localhost:8000"
    session_cookie_name: str = "fm_session"
    session_ttl_days: int = 30
    # True whenever the site is served over HTTPS (any real deployment).
    cookie_secure: bool = False
    # Optional "Sign in with Google". Both unset = the button isn't shown.
    google_client_id: str | None = None
    google_client_secret: str | None = None
    # Uploaded photos. A local folder for the demo; media.py is the seam for
    # object storage later.
    media_root: str = "./media"
    max_photo_bytes: int = 10 * 1024 * 1024
    max_photos_per_pin: int = 4
    # Distinct open reports that hide a pin until an admin looks at it.
    report_auto_hide_threshold: int = 3

    # Per-client request limits on the endpoints anyone can call
    # (app/api/rate_limits.py). Only for turning them off in a pinch.
    rate_limits_enabled: bool = True

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
