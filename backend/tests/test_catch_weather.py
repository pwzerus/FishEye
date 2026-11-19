"""Weather on catches (services/catch_weather.py): the nearest airport
station's report, found here so the spot never leaves FishEye. No network:
every report is made up below."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.community import WEATHER_ANGLER, WEATHER_NWS, CatchPin, CatchWeather
from app.services import catch_weather as cw
from tests.conftest import TestingSessionLocal, signup
from tests.test_pins_api import create

STATIONS = (
    cw.Station("KFAR", 33.5, -95.5),  # ~80 km from the spot below: beyond reach
    cw.Station("KNEA", 32.85, -95.6),  # ~5 km
    cw.Station("KMID", 32.95, -95.4),  # ~24 km
    cw.Station("KOFF", 32.6, -96.0),  # ~44 km
)
SPOT = (32.8065, -95.5931)


@pytest.fixture(autouse=True)
def _stations(monkeypatch):
    monkeypatch.setattr(cw, "stations", lambda: STATIONS)


def report(at: datetime, *, temp_c=22.0, wind_kmh=16.0, pa=101500.0, clouds=("BKN",), falling=(), text="Mostly Cloudy"):
    return {
        "properties": {
            "timestamp": at.isoformat(),
            "textDescription": text,
            "temperature": {"value": temp_c, "unitCode": "wmoUnit:degC"},
            "windSpeed": {"value": wind_kmh, "unitCode": "wmoUnit:km_h-1"},
            "barometricPressure": {"value": pa, "unitCode": "wmoUnit:Pa"},
            "cloudLayers": [{"amount": c, "base": {"value": 900}} for c in clouds],
            "presentWeather": [{"weather": w, "rawString": w} for w in falling],
        }
    }


# --------------------------------------------------------------- reports


@pytest.mark.parametrize(
    ("props", "sky"),
    [
        ({"presentWeather": [{"weather": "rain"}], "cloudLayers": [{"amount": "FEW"}]}, "rain"),
        ({"presentWeather": [{"weather": "thunderstorms"}]}, "rain"),
        ({"presentWeather": [{"weather": "snow"}, {"weather": "rain"}]}, "snow"),
        ({"cloudLayers": [{"amount": "CLR"}]}, "clear"),
        ({"cloudLayers": [{"amount": "FEW"}]}, "clear"),
        ({"cloudLayers": [{"amount": "FEW"}, {"amount": "SCT"}]}, "partly"),
        ({"cloudLayers": [{"amount": "SCT"}, {"amount": "OVC"}]}, "cloudy"),
        ({"cloudLayers": [{"amount": "BKN"}]}, "cloudy"),
        ({"presentWeather": [{"weather": "fog_mist"}]}, "cloudy"),
        # No layers: the report's own words.
        ({"textDescription": "Partly Cloudy"}, "partly"),
        ({"textDescription": "Partly Sunny"}, "partly"),
        ({"textDescription": "Mostly Cloudy"}, "cloudy"),
        ({"textDescription": "Mostly Clear"}, "clear"),
        ({"textDescription": "Light Rain and Fog/Mist"}, "rain"),
        ({"textDescription": "Haze"}, None),
        ({}, None),
    ],
)
def test_the_sky_from_a_station_report(props, sky):
    assert cw.sky_of(props) == sky


def test_a_report_in_fahrenheit_mph_and_hectopascals():
    at = datetime(2026, 11, 18, 12, 53, tzinfo=timezone.utc)
    r = cw.reading(report(at, temp_c=20.0, wind_kmh=16.09344, pa=101325.0)["properties"])
    assert r == cw.Reading(at=at, sky="cloudy", temp_f=68.0, wind_mph=10.0, pressure_hpa=1013.2)
    # Missing readings stay missing; a report without a time is skipped.
    bare = cw.reading({"timestamp": at.isoformat(), "temperature": {"value": None}})
    assert bare.temp_f is None and bare.wind_mph is None and bare.pressure_hpa is None
    assert cw.reading({"textDescription": "Clear"}) is None


def test_the_report_nearest_the_catch_and_the_pressure_three_hours_before():
    when = datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc)
    hourly = [when + timedelta(minutes=-7 + 60 * h) for h in range(-4, 2)]  # :53 past each hour
    readings = [cw.reading(report(t, pa=101000 + 100 * i)["properties"]) for i, t in enumerate(hourly)]
    w = cw.pick(readings, when, "KNEA")
    assert w.observed_at == hourly[4] and w.station == "KNEA"
    assert w.pressure_hpa == 1014.0 and w.trend == "rising"  # 1011 three hours before
    falling = [cw.reading(report(t, pa=102000 - 50 * i)["properties"]) for i, t in enumerate(hourly)]
    assert cw.pick(falling, when, "KNEA").trend == "falling"  # down 1.5 hPa
    steady = [cw.reading(report(t, pa=101500 + 20 * i)["properties"]) for i, t in enumerate(hourly)]
    assert cw.pick(steady, when, "KNEA").trend == "steady"
    # Nothing within 75 minutes: no reading for that time.
    assert cw.pick(readings, when + timedelta(hours=4), "KNEA") is None
    # A report that says nothing is passed over.
    empty = [cw.reading({"timestamp": hourly[4].isoformat()})]
    assert cw.pick(empty, when, "KNEA") is None


# ---------------------------------------------------------- the stations


def test_the_nearest_stations_are_found_here_within_reach():
    assert [s.id for s in cw.nearest_stations(*SPOT)] == ["KNEA", "KMID", "KOFF"]
    assert cw.nearest_stations(40.0, -100.0) == []


def test_only_the_station_and_a_time_window_go_to_the_weather_service():
    when = datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc)
    asked = []

    def fetch(url, params):
        asked.append((url, params))
        if "KNEA" in url:
            raise OSError("down")
        return {"features": [report(when - timedelta(minutes=7))]}

    w = cw.look_up(*SPOT, when, fetch)
    assert w.station == "KMID" and w.sky == "cloudy" and w.temp_f == 71.6
    assert [u for u, _ in asked] == [
        "https://api.weather.gov/stations/KNEA/observations",
        "https://api.weather.gov/stations/KMID/observations",
    ]
    assert asked[0][1] == {"start": "2026-11-18T09:10:00Z", "end": "2026-11-18T14:15:00Z"}
    # Nothing in either the URL or the window says where the spot is.
    assert "32.8" not in str(asked) and "95.5" not in str(asked)


def test_stations_without_a_report_then_and_stations_that_dont_answer():
    when = datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc)
    assert cw.look_up(*SPOT, when, lambda url, params: {"features": []}) is cw.NO_REPORT

    def down(url, params):
        raise OSError("down")

    assert cw.look_up(*SPOT, when, down) is None
    assert cw.look_up(40.0, -100.0, when, down) is None  # no station near


# ------------------------------------------------------------- when


def _pin(day: date, at: time | None, offset: int | None) -> CatchPin:
    return CatchPin(latitude=SPOT[0], longitude=SPOT[1], title="t", caught_on=day, caught_time=at, caught_utc_offset=offset)


def test_the_catch_time_by_the_anglers_clock_in_utc():
    assert cw.caught_at(_pin(date(2026, 11, 18), time(6, 40), -360)) == datetime(2026, 11, 18, 12, 40, tzinfo=timezone.utc)
    assert cw.caught_at(_pin(date(2026, 11, 18), time(21, 30), -300)) == datetime(2026, 11, 19, 2, 30, tzinfo=timezone.utc)
    assert cw.caught_at(_pin(date(2026, 11, 18), None, -360)) is None
    assert cw.caught_at(_pin(date(2026, 11, 18), time(6, 40), None)) is None


def test_only_the_last_days_can_be_looked_up():
    now = datetime(2026, 11, 19, 18, 0, tzinfo=timezone.utc)
    assert cw.can_look_up(_pin(date(2026, 11, 19), time(6, 0), -360), now)
    assert cw.can_look_up(_pin(date(2026, 11, 13), time(12, 0), -360), now)
    assert not cw.can_look_up(_pin(date(2026, 11, 12), time(12, 0), -360), now)  # past 6.5 days
    assert not cw.can_look_up(_pin(date(2026, 11, 19), time(23, 0), -360), now)  # hours ahead
    assert not cw.can_look_up(_pin(date(2026, 11, 19), None, None), now)


# ----------------------------------------------------- stored with the catch


def _recent_catch(c, hours_ago=2, **fields):
    at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return create(c, caught_on=at.date().isoformat(), caught_time=at.strftime("%H:%M"), utc_offset=0, **fields), at


def test_a_recent_catch_gets_the_weather_once(make_client, db_session):
    c = make_client()
    signup(c)
    resp, at = _recent_catch(c)
    assert resp.status_code == 201, resp.text
    pin = resp.json()
    assert pin["caught_time"] == at.strftime("%H:%M") and pin["weather"] is None
    calls = []

    def fetch(url, params):
        calls.append(url)
        return {"features": [report(at.replace(second=0, microsecond=0) - timedelta(minutes=5), clouds=("SCT",))]}

    cw.fill(pin["id"], TestingSessionLocal, fetch)
    cw.fill(pin["id"], TestingSessionLocal, fetch)  # already there: not asked again
    assert len(calls) == 1
    row = db_session.scalar(select(CatchWeather).where(CatchWeather.pin_id == pin["id"]))
    assert (row.source, row.station, row.sky, row.temp_f) == (WEATHER_NWS, "KNEA", "partly", 71.6)
    shown = c.get(f"/api/pins/{pin['id']}").json()["weather"]
    assert shown == {"source": "nws", "sky": "partly", "temp_f": 71.6, "wind_mph": 9.9, "trend": None}


def test_a_station_without_a_report_is_not_asked_again_but_a_failure_is(make_client, db_session):
    c = make_client()
    signup(c)
    first = _recent_catch(c)[0].json()
    second = _recent_catch(c, hours_ago=3)[0].json()
    cw.fill(first["id"], TestingSessionLocal, lambda url, params: {"features": []})
    row = db_session.scalar(select(CatchWeather).where(CatchWeather.pin_id == first["id"]))
    assert row is not None and row.sky is None and row.temp_f is None
    assert c.get(f"/api/pins/{first['id']}").json()["weather"] is None

    def down(url, params):
        raise OSError("down")

    cw.fill(second["id"], TestingSessionLocal, down)
    assert db_session.scalar(select(CatchWeather).where(CatchWeather.pin_id == second["id"])) is None
    user_id = db_session.get(CatchPin, second["id"]).user_id
    assert cw.pending(db_session, user_id) == [second["id"]]


def test_an_old_catch_isnt_looked_up_and_the_angler_can_pick_its_sky(make_client, db_session):
    c = make_client()
    signup(c)
    pin = create(c, caught_on="2026-06-01", caught_time="06:40", utc_offset=-300, weather_sky="cloudy").json()
    assert pin["weather"] == {"source": "angler", "sky": "cloudy", "temp_f": None, "wind_mph": None, "trend": None}
    cw.fill(pin["id"], TestingSessionLocal, lambda url, params: pytest.fail("an old catch was looked up"))
    url = f"/api/pins/{pin['id']}"
    assert c.patch(url, json={"title": "Dam bank at dawn"}).json()["weather"]["sky"] == "cloudy"  # kept
    assert c.patch(url, json={"weather_sky": "rain"}).json()["weather"]["sky"] == "rain"
    assert c.patch(url, json={"weather_sky": ""}).json()["weather"] is None
    assert create(c, weather_sky="hail").json()["detail"] == "Pick the weather from the list."


def test_a_new_time_or_spot_drops_the_looked_up_weather(make_client, db_session):
    c = make_client()
    signup(c)
    resp, at = _recent_catch(c)
    pin = resp.json()
    db_session.add(CatchWeather(pin_id=pin["id"], source=WEATHER_NWS, station="KNEA", sky="clear", temp_f=60.0))
    db_session.commit()
    url = f"/api/pins/{pin['id']}"
    assert c.patch(url, json={"note": "Windy"}).json()["weather"]["sky"] == "clear"  # kept
    earlier = (at - timedelta(hours=1)).strftime("%H:%M")
    moved = c.patch(url, json={"caught_time": earlier, "utc_offset": 0}).json()
    assert moved["caught_time"] == earlier and moved["weather"] is None
    db_session.expire_all()
    assert db_session.scalar(select(CatchWeather).where(CatchWeather.pin_id == pin["id"])) is None


def test_the_time_is_checked_and_can_be_cleared(make_client):
    c = make_client()
    signup(c)
    assert create(c, caught_time="25:10", caught_on="2026-11-18").json()["detail"] == "That time doesn't look right."
    assert create(c, caught_time="06:40").json()["detail"] == "Add the date as well as the time."
    pin = create(c, caught_on="2026-11-18", caught_time="6:05", utc_offset=-360).json()
    assert pin["caught_time"] == "06:05"
    url = f"/api/pins/{pin['id']}"
    assert c.patch(url, json={"title": "Still dawn"}).json()["caught_time"] == "06:05"
    assert c.patch(url, json={"caught_time": ""}).json()["caught_time"] is None
    # A clock offset that no clock has is dropped, not refused.
    odd = create(c, caught_on="2026-11-18", caught_time="07:00", utc_offset=-301)
    assert odd.status_code == 201


def test_new_catches_are_looked_up_after_the_answer_only_when_switched_on(make_client, monkeypatch):
    queued = []
    monkeypatch.setattr(cw, "fill", lambda pin_id, *a, **k: queued.append(pin_id))
    c = make_client()
    signup(c)
    _recent_catch(c)
    assert queued == []  # CATCH_WEATHER=off in the test suite
    monkeypatch.setattr(cw, "enabled", lambda: True)
    pin = _recent_catch(c)[0].json()
    old = create(c, caught_on="2026-06-01", caught_time="06:40", utc_offset=-300).json()
    assert queued == [pin["id"]] and old["id"] not in queued
    # The analysis page tries again for recent catches still without it.
    queued.clear()
    assert c.get("/api/pins/analysis").status_code == 200
    assert sorted(queued) == sorted([pin["id"], pin["id"] - 1])
