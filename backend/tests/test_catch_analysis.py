"""The angler's own catches, counted (services/catch_analysis.py)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.community import PIN_REMOVED, WEATHER_ANGLER, WEATHER_NWS, CatchPin, CatchWeather, User
from app.services import catch_analysis as ca
from tests.conftest import signup
from tests.test_pins_api import create

AUSTIN = (30.2672, -97.7431)


def _near(actual: datetime, expected: datetime, minutes: float = 4) -> bool:
    return abs(actual - expected) <= timedelta(minutes=minutes)


def test_sunrise_and_sunset_in_utc():
    # Austin's almanac: 6:29 and 8:36 pm CDT on the longest day, 7:24 am and
    # 5:35 pm CST on the shortest.
    rise, noon, set_ = ca.sun_times(*AUSTIN, date(2026, 6, 21))
    assert _near(rise, datetime(2026, 6, 21, 11, 29, tzinfo=timezone.utc))
    assert _near(set_, datetime(2026, 6, 22, 1, 36, tzinfo=timezone.utc))
    assert _near(noon, datetime(2026, 6, 21, 18, 33, tzinfo=timezone.utc))
    rise, _, set_ = ca.sun_times(*AUSTIN, date(2026, 12, 21))
    assert _near(rise, datetime(2026, 12, 21, 13, 24, tzinfo=timezone.utc))
    assert _near(set_, datetime(2026, 12, 21, 23, 35, tzinfo=timezone.utc))
    # Utqiagvik, Alaska: the sun doesn't set in June or rise in December.
    assert ca.sun_times(71.29, -156.79, date(2026, 6, 21))[0] is None
    assert ca.sun_times(71.29, -156.79, date(2026, 12, 21))[2] is None


def _pin(day: date, at: time | None, offset: int | None = -300, where=AUSTIN) -> CatchPin:
    return CatchPin(latitude=where[0], longitude=where[1], title="t", caught_on=day, caught_time=at, caught_utc_offset=offset)


@pytest.mark.parametrize(
    ("day", "at", "offset", "slot"),
    [
        # June, Central daylight time: sunrise 6:29, solar noon 1:33 pm, sunset 8:36 pm.
        (date(2026, 6, 21), time(5, 45), -300, "dawn"),
        (date(2026, 6, 21), time(8, 20), -300, "dawn"),
        (date(2026, 6, 21), time(10, 0), -300, "morning"),
        (date(2026, 6, 21), time(12, 30), -300, "midday"),
        (date(2026, 6, 21), time(16, 0), -300, "afternoon"),
        (date(2026, 6, 21), time(19, 30), -300, "dusk"),
        (date(2026, 6, 21), time(22, 0), -300, "night"),
        (date(2026, 6, 21), time(4, 0), -300, "night"),
        # December, Central standard time: sunrise 7:24, sunset 5:35 pm. The
        # same 8:20 is still dawn, and 5 pm is dusk, not afternoon.
        (date(2026, 12, 21), time(8, 20), -360, "dawn"),
        (date(2026, 12, 21), time(9, 40), -360, "morning"),
        (date(2026, 12, 21), time(17, 0), -360, "dusk"),
        (date(2026, 12, 21), time(19, 0), -360, "night"),
        # No time, or no clock to place it by: no slot.
        (date(2026, 6, 21), None, -300, None),
        (date(2026, 6, 21), time(10, 0), None, None),
    ],
)
def test_the_time_of_day_goes_by_that_days_sun(day, at, offset, slot):
    assert ca.time_of_day(_pin(day, at, offset)) == slot


def test_without_a_sunrise_or_sunset_the_clock_decides():
    north = (71.29, -156.79)
    assert ca.time_of_day(_pin(date(2026, 6, 21), time(23, 30), -480, north)) == "night"
    assert ca.time_of_day(_pin(date(2026, 6, 21), time(6, 30), -480, north)) == "dawn"
    assert ca.time_of_day(_pin(date(2026, 12, 21), time(12, 0), -540, north)) == "midday"


# ------------------------------------------------------------- the counts


def _catch(c, **fields):
    resp = create(c, **fields)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seasoned(db_session, c, email="angler@example.com", name="Angler"):
    """An account past its first days, when it may share only a few
    catches a day."""
    signup(c, email=email, name=name)
    user = db_session.scalar(select(User).where(User.email == email))
    user.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    db_session.commit()


def test_an_anglers_catches_counted_by_fish_bait_time_weather_month_and_water(make_client, db_session, seeded_lake):
    c = make_client()
    _seasoned(db_session, c)
    june = {"caught_on": "2026-06-21", "utc_offset": -300}
    a = _catch(c, species_slug="largemouth-bass", gear=["lure-soft-worm", "rod-spinning"], caught_time="06:10", **june)
    b = _catch(c, species_slug="largemouth-bass", gear=["lure-soft-worm", "lure-crankbait"], caught_time="19:45", **june)
    d = _catch(c, species_slug="bluegill", gear=["bait-nightcrawler", "bobber"], caught_time="12:30", **june)
    _catch(c, species_other="Sauger", caught_on="2026-03-02")
    _catch(c, species_other="sauger ", caught_on="2026-03-09")
    _catch(c, title="Nothing biting", caught_on="2026-03-09")
    for pin_id, source, sky, temp, wind, trend in (
        (a["id"], WEATHER_NWS, "cloudy", 74.0, 3.0, "falling"),
        (b["id"], WEATHER_NWS, "cloudy", 88.0, 12.0, "steady"),
        (d["id"], WEATHER_ANGLER, "clear", None, None, None),
    ):
        db_session.add(CatchWeather(pin_id=pin_id, source=source, sky=sky, temp_f=temp, wind_mph=wind, trend=trend))
    db_session.commit()
    # Someone else's catch and a removed one of ours count for nothing.
    other = make_client()
    signup(other, email="other@example.com", name="Other")
    _catch(other, species_slug="bluegill", gear=["lure-soft-worm"])
    removed = _catch(c, species_slug="bluegill", gear=["lure-spinnerbait"], caught_on="2026-06-22")
    db_session.get(CatchPin, removed["id"]).status = PIN_REMOVED
    db_session.commit()

    body = c.get("/api/pins/analysis").json()
    assert body["total"] == 6 and body["species"] is None
    assert body["first_on"] == "2026-03-02" and body["last_on"] == "2026-06-21"
    assert [(f["key"], f["count"]) for f in body["fish"]] == [
        ("largemouth-bass", 2),
        ("~sauger", 2),
        ("bluegill", 1),
    ]
    assert body["fish"][0]["label"] == "Largemouth Bass" and body["fish"][1]["slug"] is None
    assert body["all_species"] == body["fish"]
    # Lures and baits only: the rod and the bobber aren't bait.
    assert [(b["key"], b["count"]) for b in body["baits"]] == [
        ("lure-soft-worm", 2),
        ("bait-nightcrawler", 1),
        ("lure-crankbait", 1),
    ]
    assert body["baits"][0]["label"] == "Soft plastic worms"
    assert body["baits_logged"] == 3
    times = {t["key"]: t["count"] for t in body["times"]}
    assert times == {"dawn": 1, "morning": 0, "midday": 1, "afternoon": 0, "dusk": 1, "night": 0}
    assert body["times_logged"] == 3
    assert {s["key"]: s["count"] for s in body["skies"]} == {"clear": 1, "partly": 0, "cloudy": 2, "rain": 0, "snow": 0}
    assert {s["key"]: s["count"] for s in body["trends"]} == {"rising": 0, "steady": 1, "falling": 1}
    assert {s["key"]: s["count"] for s in body["temps"]} == {"cold": 0, "cool": 0, "warm": 1, "hot": 1}
    assert {s["key"]: s["count"] for s in body["winds"]} == {"calm": 1, "breeze": 1, "windy": 0}
    assert body["weather_logged"] == 3
    assert body["months"][2] == 3 and body["months"][5] == 3 and sum(body["months"]) == 6
    assert body["waters"] == [{"kind": "lake", "id": seeded_lake["waterbody"].id, "name": "Lake Fork", "count": 6}]


def test_one_fish_at_a_time(make_client):
    c = make_client()
    signup(c)
    _catch(c, species_slug="largemouth-bass", gear=["lure-soft-worm"], caught_on="2026-06-21", caught_time="06:10", utc_offset=-300)
    _catch(c, species_slug="bluegill", gear=["bait-nightcrawler"], caught_on="2026-07-04")
    _catch(c, species_other="Sauger", caught_on="2026-03-02")
    bass = c.get("/api/pins/analysis", params={"species": "largemouth-bass"}).json()
    assert bass["species"] == "largemouth-bass" and bass["total"] == 1
    assert bass["fish"] == [] and len(bass["all_species"]) == 3
    assert [(b["key"], b["count"]) for b in bass["baits"]] == [("lure-soft-worm", 1)]
    assert bass["times_logged"] == 1 and bass["months"][5] == 1
    sauger = c.get("/api/pins/analysis", params={"species": "~sauger"}).json()
    assert sauger["total"] == 1 and sauger["baits_logged"] == 0
    assert c.get("/api/pins/analysis", params={"species": "kraken"}).json()["total"] == 0


def test_nothing_yet_and_only_for_the_signed_in_angler(make_client):
    c = make_client()
    assert c.get("/api/pins/analysis").status_code == 401
    signup(c)
    body = c.get("/api/pins/analysis").json()
    assert body["total"] == 0 and body["first_on"] is None and body["fish"] == []
    assert body["months"] == [0] * 12 and all(t["count"] == 0 for t in body["times"])


def test_a_catch_without_a_date_counts_in_the_month_it_was_shared(make_client, db_session):
    c = make_client()
    signup(c)
    pin = _catch(c, title="Undated")
    db_session.get(CatchPin, pin["id"]).caught_on = None
    db_session.commit()
    body = c.get("/api/pins/analysis").json()
    shared = db_session.scalar(select(CatchPin.created_at).where(CatchPin.id == pin["id"]))
    assert body["months"][shared.month - 1] == 1
