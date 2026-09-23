"""API contract for the AI advisor (PRD §5.1).

The shape here encodes the PRD's hard constraints, so they can't be lost in
a later refactor of the prompt:

* Everything the model wrote lives inside `explanation`, and nowhere else.
  A reader of this file can see exactly how much of the response is
  model-authored: one field.
* `safety_warnings` and `confidence` sit OUTSIDE it, at the top level,
  because they are computed by the backend and never routed through the
  model. Constraint 5 ("weather warnings outrank fishing advice") and
  constraint 3 ("lower the confidence when data is missing") are
  guarantees, and a guarantee that depends on a model choosing to repeat
  something isn't one. The scoring engine already computes confidence from
  which signals were actually available; asking a model to restate that
  number could only make it wrong.
* `answer_source` tells the caller whether they're reading model output or
  the fixed template, the same way the weather API distinguishes live NWS
  data from its fallback. A UI that can't tell the difference will
  eventually present one as the other.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.recommendation import SpotCandidateOut, TimeWindowOut, WeatherWarningOut


class AdvisorRequest(BaseModel):
    waterbody_id: int
    target_species: str | None = None
    limit: int = Field(default=3, ge=1, le=10)


class AdvisorSourceOut(BaseModel):
    """A citation. `url` is always one the backend supplied — the validator
    rejects any the model invented (see ai_advisor.py)."""

    url: str
    label: str


class AdvisorExplanationOut(BaseModel):
    """The model-authored part, after server-side validation.

    Note what is absent: no coordinates, no species determination, no
    regulation claims, no confidence score. Those are the four things
    PRD constraint 1 says an LLM must not decide, so there is no field
    here for the model to put them in.
    """

    summary: str
    gear: list[str] = []
    bait: list[str] = []
    steps: list[str] = []
    risks: list[str] = []
    sources: list[AdvisorSourceOut] = []


class AdvisorTraceOut(BaseModel):
    """PRD constraint 14's per-request trace, minus anything sensitive.

    Deliberately returned to the caller and not just logged: for a portfolio
    demo the trace *is* the feature — being able to point at token counts,
    validation attempts and which path the answer took is the difference
    between "it calls an LLM" and "it operates an LLM".
    """

    trace_id: str
    provider: str
    model: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    # How many times the model's output was parsed/validated before we
    # either accepted it or gave up. 0 means the provider never answered.
    validation_attempts: int
    # "ok" | "invalid_json" | "ungrounded_source" | "ungrounded_species"
    #   | "provider_unavailable"
    outcome: str
    retrieved_source_count: int
    cache_hit: bool


class AdvisorResponse(BaseModel):
    waterbody_id: int
    waterbody_name: str
    target_species: str | None
    explanation: AdvisorExplanationOut
    # "llm" when the model's output passed validation, "fallback" when the
    # fixed template was used instead.
    answer_source: str
    # Server-computed (see module docstring) — never model output.
    confidence: float
    safety_warnings: list[WeatherWarningOut]
    best_time_window: TimeWindowOut | None
    candidates: list[SpotCandidateOut]
    weather_source: str
    trace: AdvisorTraceOut
    generated_at: datetime
