"""Integration tests for POST /api/recommendations. Weather is injected via
a monkeypatched adapter — no live HTTP, same as the rest of the suite."""
from datetime import datetime, timezone

import pytest

from app.models.waterbody import AccessPoint
from app.services import recommendations as rec_module
from app.services.weather_adapter import (
    CurrentConditions,
    HourlyPeriod,
    WeatherAlert,
    WeatherSnapshot,
)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def _snapshot(*, source: str = "nws", alerts: list[WeatherAlert] | None = None) -> WeatherSnapshot:
    return WeatherSnapshot(
        latitude=32.8,
        longitude=-95.6,
        current=CurrentConditions(
            temperature=78,
            temperature_unit="F",
            wind_speed="10 mph",
            wind_direction="SE",
            short_forecast="Partly Sunny",
            is_daytime=True,
        ),
        # A real fallback snapshot carries no hourly data at all — see
        # weather_adapter._fallback_snapshot.
        hourly=[]
        if source == "fallback"
        else [
            HourlyPeriod(
                start_time=NOW,
                temperature=78,
                temperature_unit="F",
                wind_speed="10 mph",
                wind_direction="SE",
                short_forecast="Partly Sunny",
                probability_of_precipitation=10,
            )
        ],
        alerts=alerts or [],
        source=source,
        stale=source == "fallback",
        fetched_at=NOW,
    )


@pytest.fixture()
def stub_weather(monkeypatch):
    """Replaces the adapter call inside the recommendations service."""

    def _install(snapshot: WeatherSnapshot):
        monkeypatch.setattr(rec_module, "get_weather", lambda lat, lng: snapshot)

    return _install


def test_recommendations_rank_access_points(client, seeded_lake, stub_weather):
    stub_weather(_snapshot())
    wb = seeded_lake["waterbody"]

    resp = client.post(
        "/api/recommendations",
        json={"waterbody_id": wb.id, "target_species": "Largemouth Bass"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["waterbody_name"] == "Lake Fork"
    assert body["target_species"] == "Largemouth Bass"
    assert len(body["candidates"]) == 1

    candidate = body["candidates"][0]
    assert candidate["name"] == "Lake Fork Dam Bank Access"
    assert candidate["public_access_status"] == "confirmed_public"
    assert 0 < candidate["score"] <= 1
    assert candidate["missing_signals"] == []

    # Confidence is the share of intended signal that was actually informed:
    #   access 0.40 + species 0.20 + freshness 0.15  = 0.75 fully informed
    #   weather 0.25 x 0.85 availability              = 0.2125
    # Weather is only 85% informed here (wind 0.60 + precipitation 0.25 of
    # its 1.0 sub-weight) because this fixture's single forecast hour is too
    # short to detect a front (0.15 of the sub-weight).
    assert candidate["confidence"] == 0.9625

    weather = next(f for f in candidate["factors"] if f["name"] == "weather")
    assert "not enough forecast data" in weather["reason"]


def test_every_factor_reports_its_own_reason(client, seeded_lake, stub_weather):
    """The ranking has to be explainable without the LLM (PRD §5.2)."""
    stub_weather(_snapshot())
    resp = client.post(
        "/api/recommendations",
        json={"waterbody_id": seeded_lake["waterbody"].id, "target_species": "Largemouth Bass"},
    )
    factors = resp.json()["candidates"][0]["factors"]

    assert {f["name"] for f in factors} == {
        "access",
        "weather",
        "species_match",
        "freshness",
    }
    assert all(f["reason"] for f in factors)


def test_private_access_points_never_appear(client, db_session, seeded_lake, stub_weather):
    """PRD §12 acceptance criterion — an unconfirmed area must not be
    presented as a public access point under any ranking."""
    stub_weather(_snapshot())
    wb = seeded_lake["waterbody"]
    db_session.add(
        AccessPoint(
            waterbody_id=wb.id,
            name="Private Boat Dock",
            latitude=32.80,
            longitude=-95.60,
            access_type="bank",
            public_status="private",
            parking=True,
        )
    )
    db_session.commit()

    resp = client.post("/api/recommendations", json={"waterbody_id": wb.id})
    names = {c["name"] for c in resp.json()["candidates"]}
    assert "Private Boat Dock" not in names


def test_weather_outage_lowers_confidence_but_still_returns_candidates(
    client, seeded_lake, stub_weather
):
    """PRD §17: core features keep working when an external service is down —
    but the response must not pretend it had weather data."""
    stub_weather(_snapshot(source="fallback"))

    resp = client.post(
        "/api/recommendations",
        json={"waterbody_id": seeded_lake["waterbody"].id, "target_species": "Largemouth Bass"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["weather_source"] == "fallback"
    assert body["best_time_window"] is None
    candidate = body["candidates"][0]
    assert set(candidate["missing_signals"]) == {"weather"}
    assert candidate["confidence"] == 0.75  # 1.0 - 0.25 weather


def test_severe_weather_alerts_surface_at_top_level(client, seeded_lake, stub_weather):
    """Warnings outrank recommendations (PRD §17), so they can't be buried
    inside an individual candidate the client might not render."""
    stub_weather(
        _snapshot(
            alerts=[
                WeatherAlert(
                    event="Severe Thunderstorm Warning",
                    severity="Severe",
                    headline="Severe Thunderstorm Warning until 8 PM",
                    effective=NOW,
                    expires=NOW,
                )
            ]
        )
    )

    resp = client.post("/api/recommendations", json={"waterbody_id": seeded_lake["waterbody"].id})
    warnings = resp.json()["safety_warnings"]
    assert len(warnings) == 1
    assert warnings[0]["event"] == "Severe Thunderstorm Warning"


def test_species_not_in_lake_scores_lower_than_a_confirmed_one(
    client, seeded_lake, stub_weather
):
    stub_weather(_snapshot())
    wb_id = seeded_lake["waterbody"].id

    confirmed = client.post(
        "/api/recommendations", json={"waterbody_id": wb_id, "target_species": "Largemouth Bass"}
    ).json()
    absent = client.post(
        "/api/recommendations", json={"waterbody_id": wb_id, "target_species": "Northern Pike"}
    ).json()

    assert confirmed["candidates"][0]["score"] > absent["candidates"][0]["score"]
    # Both had the same *signals*, just different values — confidence is equal.
    assert confirmed["candidates"][0]["confidence"] == absent["candidates"][0]["confidence"]


def test_omitting_target_species_drops_the_factor(client, seeded_lake, stub_weather):
    stub_weather(_snapshot())
    resp = client.post("/api/recommendations", json={"waterbody_id": seeded_lake["waterbody"].id})
    candidate = resp.json()["candidates"][0]
    assert set(candidate["missing_signals"]) == {"species_match"}


def test_unknown_waterbody_returns_404(client, stub_weather):
    stub_weather(_snapshot())
    resp = client.post("/api/recommendations", json={"waterbody_id": 99999})
    assert resp.status_code == 404
