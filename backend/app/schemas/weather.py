from datetime import datetime

from pydantic import BaseModel


class CurrentConditionsOut(BaseModel):
    """The most recent forecast period from NWS, treated as 'now' — the
    NWS API has no true instantaneous-observation endpoint that's reliable
    everywhere, so like most consumer weather UIs we use the first forecast
    period as current conditions (PRD §4.3)."""

    temperature: float | None
    temperature_unit: str
    wind_speed: str | None
    wind_direction: str | None
    short_forecast: str
    is_daytime: bool


class HourlyPeriodOut(BaseModel):
    start_time: datetime
    temperature: float | None
    temperature_unit: str
    wind_speed: str | None
    wind_direction: str | None
    short_forecast: str
    probability_of_precipitation: int | None


class WeatherAlertOut(BaseModel):
    event: str
    severity: str
    headline: str | None
    effective: datetime | None
    expires: datetime | None


class WeatherOut(BaseModel):
    """GET /api/weather?lat=&lng= response (PRD §6 API contract).

    `source` and `stale` let the frontend distinguish "live NWS data" from
    "we couldn't reach NWS so here's a safe fallback" (PRD §17: core pages
    must keep working when an external service is down). `source == "fallback"`
    means temperature/hourly/alerts are best-effort placeholders, not real
    readings — the frontend should show a "weather data unavailable" notice
    rather than presenting them as fact.
    """

    latitude: float
    longitude: float
    current: CurrentConditionsOut
    hourly: list[HourlyPeriodOut]
    alerts: list[WeatherAlertOut]
    source: str  # "nws" | "fallback"
    stale: bool
    fetched_at: datetime
