from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    waterbody_id: int
    target_species: str | None = Field(
        default=None,
        description="common_name, e.g. 'Largemouth Bass'. Omitted means "
        "'anything biting' — the species-match factor then drops out of the "
        "score instead of penalizing every spot equally.",
    )
    limit: int = Field(default=5, ge=1, le=20)


class FactorOut(BaseModel):
    """One scoring signal, exposed so the ranking is auditable in the UI
    rather than an opaque number (PRD §5.2)."""

    name: str
    weight: float
    value: float | None
    reason: str


class SpotCandidateOut(BaseModel):
    access_point_id: int
    name: str
    latitude: float
    longitude: float
    access_type: str
    public_access_status: str
    score: float
    confidence: float
    factors: list[FactorOut]
    missing_signals: list[str]


class TimeWindowOut(BaseModel):
    # Serialized with the forecast's own UTC offset, i.e. in the lake's
    # local time — the UI shows clock times from it as-is.
    start_time: datetime
    end_time: datetime
    reason: str
    label: str | None = None  # "morning" | "evening" for bite windows
    score: float | None = None


class WeatherWarningOut(BaseModel):
    event: str
    severity: str
    headline: str | None


class PlanPickOut(BaseModel):
    name: str
    why: str


class PlanWhereOut(BaseModel):
    shore: str | None  # compass point of the bank to fish, when one stands out
    text: str


class PlanWindowOut(BaseModel):
    start_time: datetime
    end_time: datetime
    label: str | None = None


class FishingPlanOut(BaseModel):
    """Where, when and what to fish with today (app/services/fishing_plan.py)."""

    species: str | None
    species_slug: str | None = None
    species_options: list[str]
    species_on_record: bool | None
    where: PlanWhereOut | None
    when: PlanWindowOut | None
    also: PlanWindowOut | None
    conditions: str | None
    lures: list[PlanPickOut]
    baits: list[PlanPickOut]
    lure_note: str | None
    heads_up: list[str]


class RecommendationResponse(BaseModel):
    """POST /api/recommendations response (PRD §9).

    `safety_warnings` is deliberately a top-level field rather than a
    per-candidate note: PRD §17 requires severe-weather warnings to take
    priority over normal recommendations, so a client cannot render the
    candidate list without also having the warnings in hand.
    """

    waterbody_id: int
    waterbody_name: str
    target_species: str | None
    candidates: list[SpotCandidateOut]
    best_time_window: TimeWindowOut | None
    bite_windows: list[TimeWindowOut] = []
    safety_warnings: list[WeatherWarningOut]
    weather_source: str  # "nws" | "fallback"
    generated_at: datetime
    plan: FishingPlanOut | None = None
