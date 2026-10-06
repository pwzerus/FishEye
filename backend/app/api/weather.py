from fastapi import APIRouter, Depends, Query

from app.api import rate_limits
from app.schemas.weather import (
    CurrentConditionsOut,
    HourlyPeriodOut,
    WeatherAlertOut,
    WeatherOut,
)
from app.services.weather_adapter import WeatherSnapshot, get_weather

router = APIRouter(tags=["weather"], dependencies=[Depends(rate_limits.WEATHER)])


def _to_response(snapshot: WeatherSnapshot) -> WeatherOut:
    return WeatherOut(
        latitude=snapshot.latitude,
        longitude=snapshot.longitude,
        current=CurrentConditionsOut(
            temperature=snapshot.current.temperature,
            temperature_unit=snapshot.current.temperature_unit,
            wind_speed=snapshot.current.wind_speed,
            wind_direction=snapshot.current.wind_direction,
            short_forecast=snapshot.current.short_forecast,
            is_daytime=snapshot.current.is_daytime,
        ),
        hourly=[
            HourlyPeriodOut(
                start_time=p.start_time,
                temperature=p.temperature,
                temperature_unit=p.temperature_unit,
                wind_speed=p.wind_speed,
                wind_direction=p.wind_direction,
                short_forecast=p.short_forecast,
                probability_of_precipitation=p.probability_of_precipitation,
            )
            for p in snapshot.hourly
        ],
        alerts=[
            WeatherAlertOut(
                event=a.event,
                severity=a.severity,
                headline=a.headline,
                effective=a.effective,
                expires=a.expires,
            )
            for a in snapshot.alerts
        ],
        source=snapshot.source,
        stale=snapshot.stale,
        fetched_at=snapshot.fetched_at,
    )


@router.get("/weather", response_model=WeatherOut)
def get_weather_for_point(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
) -> WeatherOut:
    """Current conditions + hourly forecast + active alerts for a point
    (PRD §6 API contract). Always returns 200 — see weather_adapter.get_weather
    for why: a downed NWS API degrades to a marked fallback rather than a
    5xx, so the map page keeps working (PRD §17)."""
    snapshot = get_weather(lat, lng)
    return _to_response(snapshot)
