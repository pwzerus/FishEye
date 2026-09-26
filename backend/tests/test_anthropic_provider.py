"""AnthropicProvider against a faked HTTP layer — never the real API."""
from __future__ import annotations

import httpx
import pytest

from app.services import llm
from app.services.llm import LLMUnavailable
from app.services.llm import anthropic as anth

_REAL_POST = httpx.Client.post


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(anth, "RETRY_DELAY_SECONDS", 0.0)


def _install(monkeypatch, responses):
    """Serve `responses` (status, json) in order to calls to the Anthropic URL."""
    calls = []

    def fake_post(self, url, *args, **kwargs):
        if "api.anthropic.com" not in str(url):
            return _REAL_POST(self, url, *args, **kwargs)
        calls.append(kwargs)
        status, payload = responses.pop(0)
        return httpx.Response(status, json=payload, request=httpx.Request("POST", str(url)))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    return calls


OK = (
    200,
    {
        "model": "claude-haiku-4-5",
        "content": [{"type": "text", "text": '{"answer": "hi", "citations": ["a#b"]}'}],
        "usage": {"input_tokens": 1000, "output_tokens": 200},
    },
)


def test_a_reply_becomes_text_tokens_and_an_estimated_cost(monkeypatch):
    calls = _install(monkeypatch, [OK])
    resp = anth.AnthropicProvider("k").complete("sys", "user")
    assert resp.text.startswith('{"answer"')
    assert (resp.prompt_tokens, resp.completion_tokens) == (1000, 200)
    assert resp.estimated_cost_usd == pytest.approx((1000 * 1.0 + 200 * 5.0) / 1_000_000)
    sent = calls[0]
    assert sent["headers"]["x-api-key"] == "k"
    assert sent["json"]["system"] == "sys"
    assert sent["json"]["messages"] == [{"role": "user", "content": "user"}]


def test_rate_limits_are_retried_once(monkeypatch):
    calls = _install(monkeypatch, [(429, {}), OK])
    assert anth.AnthropicProvider("k").complete("s", "u").text
    assert len(calls) == 2


def test_auth_errors_raise_unavailable_without_leaking_the_body(monkeypatch):
    _install(monkeypatch, [(401, {"error": {"message": "invalid x-api-key k"}})])
    with pytest.raises(LLMUnavailable) as exc:
        anth.AnthropicProvider("k").complete("s", "u")
    assert "401" in str(exc.value) and "invalid" not in str(exc.value)


def test_the_circuit_opens_after_repeated_failures(monkeypatch):
    calls = _install(monkeypatch, [(401, {})] * 3)
    provider = anth.AnthropicProvider("k")
    for _ in range(3):
        with pytest.raises(LLMUnavailable):
            provider.complete("s", "u")
    with pytest.raises(LLMUnavailable, match="circuit open"):
        provider.complete("s", "u")
    assert len(calls) == 3  # the fourth never reached the network


def test_get_provider_builds_anthropic_when_configured(monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "llm_model", "gpt-4o-mini")  # stale value from an old .env
    llm.reset_provider_cache()
    try:
        provider = llm.get_provider()
        assert isinstance(provider, anth.AnthropicProvider)
        assert provider.model == anth.DEFAULT_MODEL
    finally:
        llm.reset_provider_cache()


def test_anthropic_without_a_key_falls_back_to_the_mock(monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", None)
    llm.reset_provider_cache()
    try:
        assert llm.get_provider().name == "mock"
    finally:
        llm.reset_provider_cache()
