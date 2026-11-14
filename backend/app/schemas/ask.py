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
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.species_guide import GuideSourceOut


class AskRequest(BaseModel):
    # Two characters is a question in Chinese, Korean and Japanese (钓鱼).
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=300)]
    # The fish page the question was asked from, if any. Fish named in the
    # question itself take precedence (see retriever.py).
    species_slug: str | None = None
    # Two-letter code of the state the person is fishing in. Rule passages of
    # other states are left out of the answer (docs/adr/0027); without it,
    # nothing is left out.
    state: str | None = Field(default=None, min_length=2, max_length=2)
    # The site's language (en, zh, es, ko, ja): FishEye's own sentences in the
    # answer come back in it, or in the question's (services/rag/replies.py).
    lang: str | None = Field(default=None, max_length=8)


class AskCitationOut(BaseModel):
    id: str
    species_slug: str
    species_name: str
    section: str
    title: str
    excerpt: str
    region: str  # a state code for a passage stating that state's rules, else "all"
    sources: list[GuideSourceOut]
    # The question library only (docs/adr/0051): what the answer rests on, and
    # the language of title and excerpt when it isn't the guides' English.
    basis: str = ""
    lang: str = "en"


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


class AskPhotoOut(BaseModel):
    """POST /api/ask/photo: the AI's answer about a photo (services/rag/photo.py)."""

    answer: str | None
    # "llm", or "off_topic" / "fallback" with no answer (given back)
    answer_source: str
    provider: str = "none"
    ai: "AiAllowanceOut"


class AiAllowanceOut(BaseModel):
    """Today's AI summaries for whoever is asking (services/ai_quota.py)."""

    signed_in: bool
    limit: int | None  # None when signed out, or unlimited (Plus, admins)
    remaining: int | None
    enabled: bool  # False: no paid model is set up, so summaries aren't offered
    plus: bool = False  # a FishEye Plus account


class AskLakeFishOut(BaseModel):
    name: str
    slug: str | None = None  # its guide, if it has one
    confidence: str | None = None


class AskAskedFishOut(BaseModel):
    """A fish the question named, against what is on record at the lake."""

    slug: str
    name: str
    status: str  # "on_record" | "reported" | "no_record", never "not there"


class AskLakeOut(BaseModel):
    id: int
    name: str
    state_code: str
    county: str | None = None
    data_tier: str
    public_access_status: str
    species: list[AskLakeFishOut] = []
    reported: list[str] = []
    asked: list[AskAskedFishOut] = []
    access_points: int = 0
    fish_attractors: int = 0
    agency_url: str | None = None
    credit: str | None = None


class AskLakesOut(BaseModel):
    """What the lake data says to a question (services/rag/lake_facts.py)."""

    kind: str  # "lake": one named lake | "list": where to go
    lakes: list[AskLakeOut]
    same_name: list[AskLakeOut] = []  # other lakes called the same
    place: str | None = None  # "near <place>", as asked
    state: str | None = None
    fish: list[str] = []
    fish_slugs: list[str] = []
    # The card is the whole answer: guide passages wouldn't add to it.
    answers_it: bool = False


class AskResponse(BaseModel):
    question: str
    answer: str
    # "passages" (search only) | "llm" | "fallback" | "no_match"
    answer_source: str
    citations: list[AskCitationOut]
    trace: AskTraceOut
    ai: AiAllowanceOut
    # Whose rules the answer is for: a state named in the question, else the
    # one picked on the page, else None (services/rag/ask.answer_state).
    state: str | None = None
    # A lake named or "where to go": from the lake data, not the guides.
    lakes: AskLakesOut | None = None
    # The search's answer can be followed by an AI answer: the guides'
    # passages, or a fishing question they don't cover (api/ask.py).
    ai_can_answer: bool = False
