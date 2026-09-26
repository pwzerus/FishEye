"""API contract for guide Q&A (services/rag/ask.py).

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


class AskCitationOut(BaseModel):
    id: str
    species_slug: str
    species_name: str
    section: str
    title: str
    excerpt: str
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
    # "ok" | "no_match" | "invalid_json" | "ungrounded_citation"
    #   | "ungrounded_species" | "ungrounded_number" | "url_in_answer"
    #   | "provider_unavailable"
    outcome: str
    cache_hit: bool


class AskResponse(BaseModel):
    question: str
    answer: str
    answer_source: str  # "llm" | "fallback" | "no_match"
    citations: list[AskCitationOut]
    trace: AskTraceOut
