"""Anthropic Messages API provider.

Plain httpx rather than the vendor SDK: the provider's whole job is one
POST (base.py), and the same timeout / retry / circuit-breaker envelope
every other external call in this backend uses is easier to see — and to
test with a faked transport — when it's written out here rather than
configured inside a client library.

The key comes from LLM_API_KEY in the backend's own .env (gitignored). It
is never sent to, or needed by, the frontend.
"""
from __future__ import annotations

import threading
import time

import httpx

from app.services.llm.base import LLMProvider, LLMResponse, LLMUnavailable

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
# The cheapest Claude model (the product owner, 2026-11-12): the answer is
# the passages' content in plain words, which needs no bigger model.
DEFAULT_MODEL = "claude-haiku-5-5"
REQUEST_TIMEOUT_SECONDS = 20.0
RETRY_DELAY_SECONDS = 1.0
# Room for the model's thinking as well as the answer: both count here.
MAX_OUTPUT_TOKENS = 2000
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_SECONDS = 60

# USD per million tokens, (input, output). An *estimate* for the trace, per
# base.LLMResponse — list prices at the time of writing, not a bill.
# Haiku 5.5's price is for prompts up to 100K tokens; these are far shorter.
_PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5-5": (2.0, 10.0),
}
_FALLBACK_PRICE = (3.0, 15.0)

_RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


class _CircuitBreaker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None

    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            if time.monotonic() - self._opened_at >= CIRCUIT_COOLDOWN_SECONDS:
                self._opened_at, self._failures = None, 0
                return False
            return True

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self._failures, self._opened_at = 0, None
                return
            self._failures += 1
            if self._failures >= CIRCUIT_FAILURE_THRESHOLD:
                self._opened_at = time.monotonic()


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self.model = model or DEFAULT_MODEL
        self._circuit = _CircuitBreaker()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if self._circuit.is_open():
            raise LLMUnavailable("anthropic: circuit open after repeated failures")

        started = time.perf_counter()
        body = {
            "model": self.model,
            "max_tokens": MAX_OUTPUT_TOKENS,
            # No temperature: Haiku 5.5 refuses any but the default. The
            # prompt keeps the answer to the passages' content instead. Low
            # effort: little thinking, which is billed as output.
            "output_config": {"effort": "low"},
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }

        payload: dict | None = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    resp = client.post(API_URL, json=body, headers=headers)
                if resp.status_code in _RETRYABLE_STATUS and attempt == 0:
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                resp.raise_for_status()
                payload = resp.json()
                break
            except httpx.TimeoutException:
                if attempt == 0:
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                self._circuit.record(ok=False)
                raise LLMUnavailable("anthropic: timed out") from None
            except (httpx.HTTPError, ValueError) as exc:
                self._circuit.record(ok=False)
                # Status only — the response body can echo request details.
                status = getattr(getattr(exc, "response", None), "status_code", "n/a")
                raise LLMUnavailable(f"anthropic: request failed (status {status})") from None

        if payload is None:
            self._circuit.record(ok=False)
            raise LLMUnavailable("anthropic: no usable response after retry")

        text = "".join(
            block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"
        )
        usage = payload.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))
        price_in, price_out = _PRICES.get(self.model, _FALLBACK_PRICE)
        self._circuit.record(ok=True)
        return LLMResponse(
            text=text,
            provider=self.name,
            model=payload.get("model", self.model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=(prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
