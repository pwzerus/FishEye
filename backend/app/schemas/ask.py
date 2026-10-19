"""API contract for guide Q&A (services/rag/ask.py).

Two steps (docs/adr/0023): POST /api/ask searches the guides and returns
the passages, free and open to everyone; POST /api/ask/summary has the
model write an answer from those passages, for signed-in accounts within a
daily allowance. Both return this same shape.

As with the advisor, the model authors exactly one field — `answer` — and
everything around it is the server's: which passages were cited (validated
ids, expanded here into titles, excerpts and source links the model never
wrote), whether the answer came from the model, the fallback, or a "not
covered" short-circuit, and the trace.
"""
from pydantic import BaseModel, Field

from app.schemas.species_guide import GuideSourceOut


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    # The fish page the question was asked from, if any. Fish named in the
    # question itself take precedence (see retriever.py).
    species_slug: str | None = None
    # Two-letter code of the state the person is fishing in. Rule passages of
    # other states are left out of the answer (docs/adr/0027); without it,
    # nothing is left out.
    state: str | None = Field(default=None, min_length=2, max_length=2)


class AskCitationOut(BaseModel):
    id: str
    species_slug: str
    species_name: str
    section: str
    title: str
    excerpt: str
    region: str  # a state code for a passage stating that state's rules, else "all"
    sources: list[GuideSourceOut]


class AskRetrievedOut(BaseModel):
    id: str
    score: float


class AskTraceOut(BaseModel):
    trace_id: str
    retriever: str
    routed_species: list[str]
    retrieved: list[AskRetrievedOut]
    provider: str
    model: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    validation_attempts: int
    # "ok" | "no_match" | "off_topic" | "unguided_fish" | "other_state"
    #   | "invalid_json" | "ungrounded_citation"
    #   | "ungrounded_species" | "ungrounded_number" | "url_in_answer"
    #   | "provider_unavailable"
    outcome: str
    cache_hit: bool


class AiAllowanceOut(BaseModel):
    """Today's AI summaries for whoever is asking (services/ai_quota.py)."""

    signed_in: bool
    limit: int | None  # None when signed out, or unlimited (admins)
    remaining: int | None


class AskResponse(BaseModel):
    question: str
    answer: str
    # "passages" (search only) | "llm" | "fallback" | "no_match"
    answer_source: str
    citations: list[AskCitationOut]
    trace: AskTraceOut
    ai: AiAllowanceOut
