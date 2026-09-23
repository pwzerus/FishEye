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
    start_time: datetime
    end_time: datetime
    reason: str


class WeatherWarningOut(BaseModel):
    event: str
    severity: str
    headline: str | None


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
    safety_warnings: list[WeatherWarningOut]
    weather_source: str  # "nws" | "fallback"
    generated_at: datetime
