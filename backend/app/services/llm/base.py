"""The LLM provider boundary.

PRD §10 asks for a replaceable LLM provider so the project isn't bolted to
one vendor, and constraint 17 asks for the same reliability envelope every
other external service here gets (timeout, retry, circuit breaker, cache,
fallback). This module is the seam: everything above it (ai_advisor.py)
talks to `LLMProvider`, and knows nothing about which vendor — or whether
a vendor is involved at all.

What a provider is responsible for
----------------------------------
Exactly one thing: turn a prompt into raw text, and report what that cost.
It does NOT parse JSON, validate a schema, decide on retries, or fall back
— those are policy decisions that must behave identically no matter which
provider is plugged in, so they live in ai_advisor.py instead. A provider
that "helpfully" repaired malformed JSON would make the validation layer
untestable and hide exactly the failure mode the fallback path exists for.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """One completion, plus the accounting PRD §14's trace record needs.

    `estimated_cost_usd` is explicitly an *estimate*: token prices are not
    knowable from inside the process and change without notice, so this is
    a per-provider constant multiplied by token counts, not a billing
    figure. It's named accordingly so nobody mistakes it for one.
    """

    text: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    latency_ms: float


class LLMUnavailable(Exception):
    """Raised when a provider can't produce anything at all (timeout, auth
    failure, circuit open). Callers fall back to a fixed template — see
    ai_advisor.py. Deliberately distinct from "the model replied with
    something unusable", which is a validation failure, not an outage:
    those two get different trace outcomes and different retry policies.
    """


class LLMProvider(ABC):
    """Text in, text out, with cost accounting."""

    name: str = "abstract"

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return the model's raw text. Raise LLMUnavailable if the provider
        itself failed; never return a placeholder string, because a caller
        can't tell that apart from a real (bad) answer."""
        raise NotImplementedError
