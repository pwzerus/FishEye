"""LLM provider layer — see base.py for what a provider is and isn't."""
from __future__ import annotations

from app.core.config import get_settings
from app.services.llm.base import LLMProvider, LLMResponse, LLMUnavailable
from app.services.llm.mock import MockProvider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMUnavailable",
    "MockProvider",
    "get_provider",
    "reset_provider_cache",
]

_cached_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Resolve the configured provider.

    Falls back to the mock when a real provider is named but has no key,
    and says so in the logs rather than failing the request: a missing key
    is a deployment gap, and the honest response to it is a labelled mock
    answer (which the UI marks as such), not a 500 that takes the whole
    recommendation panel down with it.
    """
    global _cached_provider
    if _cached_provider is not None:
        return _cached_provider

    settings = get_settings()
    provider_name = (settings.llm_provider or "mock").strip().lower()

    if provider_name in {"", "mock"}:
        _cached_provider = MockProvider(failure_mode=_configured_failure_mode())
        return _cached_provider

    if not settings.llm_api_key:
        # Deliberately not raising: see docstring.
        print(
            f"LLM_PROVIDER={provider_name!r} but LLM_API_KEY is unset — "
            "using the mock provider. Responses will be labelled as mock."
        )
        _cached_provider = MockProvider(failure_mode=_configured_failure_mode())
        return _cached_provider

    if provider_name == "anthropic":
        from app.services.llm.anthropic import AnthropicProvider

        model = settings.llm_model
        if model and model.startswith("gpt-"):
            # An older .env copied from .env.example still says gpt-4o-mini;
            # sending that to Anthropic is a guaranteed 404 on every call.
            print(f"LLM_MODEL={model!r} is not an Anthropic model; using the default.")
            model = None
        _cached_provider = AnthropicProvider(settings.llm_api_key, model=model)
        return _cached_provider

    # Other vendors land here as they're added. Until then, an explicit
    # error beats silently pretending the key was used.
    raise NotImplementedError(
        f"LLM provider {provider_name!r} is configured but not implemented yet. "
        "Set LLM_PROVIDER=mock to run the advisor without a vendor."
    )


def _configured_failure_mode() -> str:
    """Demo/test hook — see mock.py. Read from the environment directly
    rather than Settings because it exists to be flipped mid-demo without
    touching committed config."""
    import os

    return os.environ.get("LLM_MOCK_FAILURE_MODE", "none").strip().lower()


def reset_provider_cache() -> None:
    """Test/ops hook: drop the memoized provider so a changed environment
    takes effect without a process restart."""
    global _cached_provider
    _cached_provider = None
