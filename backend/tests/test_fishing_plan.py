"""Today's plan: where, when and what to fish with (app/services/fishing_plan.py)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.knowledge.species_guides import get_guide
from app.services import fishing_plan
from app.services import recommendations as rec_module
from app.services.fishing_plan import TACKLE, Conditions, build_plan, heads_up, tackle_for, where_to_fish
from app.services.weather_adapter import CurrentConditions, HourlyPeriod, WeatherSnapshot

CDT = timezone(timedelta(hours=-5))
DAY = datetime(2026, 10, 1, tzinfo=CDT)


def cond(**overrides) -> Conditions:
    base = dict(
        wind_mph=10.0,
        wind_from="SE",
        wind_text="10 mph",
        sky="mixed",
        forecast_text="Partly Sunny",
        rain_chance=10,
        temperature=78.0,
        low_light=False,
        light_word="dusk",
        front_drop_f=None,
    )
    base.update(overrides)
    return Conditions(**base)


def snapshot(*, wind="10 mph", direction="SE", sky="Partly Sunny", temps=None, rain=10) -> WeatherSnapshot:
    hours = list(range(4, 24))
    temps = temps or [78] * len(hours)
    hourly = [
        HourlyPeriod(
            start_time=DAY + timedelta(hours=h),
            temperature=t,
            temperature_unit="F",
            wind_speed=wind,
            wind_direction=direction,
            short_forecast=sky,
            probability_of_precipitation=rain,
        )
        for h, t in zip(hours, temps)
    ]
    return WeatherSnapshot(
        latitude=32.8,
        longitude=-95.6,
        current=CurrentConditions(
            temperature=temps[0],
            temperature_unit="F",
            wind_speed=wind,
            wind_direction=direction,
            short_forecast=sky,
            is_daytime=True,
        ),
        hourly=hourly,
        alerts=[],
        source="nws",
        stale=False,
        fetched_at=DAY,
    )


# --- picks never come from thin air ------------------------------------------


@pytest.mark.parametrize("species", sorted(TACKLE))
def test_every_pick_is_something_the_guide_lists(species):
    guide = get_guide(species)
    assert guide is not None
    allowed = set(guide.lures) | set(guide.live_baits)
    tackle = TACKLE[species]
    names = [r.pick for r in tackle.lures + tackle.baits]
    names += [n for n, _ in tackle.lure_fallback + tackle.bait_fallback]
    missing = [n for n in names if n not in allowed]
    assert missing == [], f"{species}: not in the guide: {missing}"


def test_every_guided_sport_fish_has_rules():
    assert set(fishing_plan.sport_species_with_guides()) <= set(TACKLE)


# --- the picks follow the conditions -----------------------------------------


def names(picks):
    return [p["name"] for p in picks]


def test_bass_picks_change_with_the_day():
    bass = get_guide("Largemouth Bass")
    windy_dusk = tackle_for(bass, cond(wind_mph=14, sky="cloudy", low_light=True))
    calm_noon = tackle_for(bass, cond(wind_mph=2, sky="sunny", low_light=False))
    front = tackle_for(bass, cond(front_drop_f=14.0, low_light=True))

    assert names(windy_dusk["lures"]) == ["Topwater lures", "Spinnerbaits"]
    assert names(calm_noon["lures"]) == ["Plastic worms", "Jigs"]
    assert names(front["lures"])[0] == "Crankbaits and ¼–½ oz lipless crankbaits"
    assert windy_dusk["lures"] != calm_noon["lures"]


def test_every_pick_says_why():
    bass = get_guide("Largemouth Bass")
    out = tackle_for(bass, cond(low_light=True))
    assert all(p["why"] for p in out["lures"] + out["baits"])
    assert "dusk" in out["lures"][0]["why"]


def test_bait_fishing_is_always_offered_when_the_guide_has_bait():
    for species in ("Largemouth Bass", "White Crappie", "Bluegill", "White Bass"):
        out = tackle_for(get_guide(species), cond())
        assert len(out["baits"]) >= 1, species


def test_catfish_get_bait_only():
    out = tackle_for(get_guide("Channel Catfish"), cond(low_light=True))
    assert out["lures"] == []
    assert len(out["baits"]) == 2
    assert out["baits"][0]["name"] == "Nightcrawlers"
    assert out["lure_note"]


def test_no_weather_still_gives_standard_picks():
    out = tackle_for(get_guide("Largemouth Bass"), None)
    assert names(out["lures"]) == ["Plastic worms", "Spinnerbaits"]
    assert out["baits"]


# --- where ---------------------------------------------------------------------


def test_fish_the_bank_the_wind_blows_into():
    where = where_to_fish(cond(wind_mph=12, wind_from="SE"))
    assert where["shore"] == "NW"
    assert "SE wind" in where["text"]


def test_too_much_wind_sends_you_to_the_sheltered_bank():
    where = where_to_fish(cond(wind_mph=28, wind_from="SE"))
    assert where["shore"] == "SE"
    assert "sheltered" in where["text"]


def test_no_wind_means_no_favored_bank():
    assert where_to_fish(cond(wind_mph=2))["shore"] is None


# --- heads-up only when it matters --------------------------------------------


def test_a_normal_day_has_nothing_to_flag():
    assert heads_up(cond()) == []


def test_heads_up_names_the_numbers():
    notes = heads_up(cond(wind_mph=28, front_drop_f=14.0, rain_chance=70, sky="rain"))
    text = " ".join(notes)
    assert "28 mph" in text
    assert "14°F" in text
    assert "70%" in text


def test_thunder_is_flagged_first():
    assert heads_up(cond(sky="thunder"))[0].startswith("Thunderstorms")


# --- the whole plan -----------------------------------------------------------


def test_plan_from_a_forecast():
    plan = build_plan(snapshot(wind="12 mph", direction="SE"), "Largemouth Bass", ["Largemouth Bass"], True)
    assert plan["species"] == "Largemouth Bass"
    assert plan["species_slug"] == "largemouth-bass"
    assert plan["where"]["shore"] == "NW"
    assert plan["when"]["label"] in ("morning", "evening")
    assert plan["also"] is not None
    assert "SE wind 12 mph" in plan["conditions"]
    assert plan["lures"] and plan["baits"]
    assert plan["heads_up"] == []


def test_plan_flags_an_incoming_front():
    temps = [80] * 10 + [79, 76, 72, 69, 67, 66, 65, 65, 65, 65]
    plan = build_plan(snapshot(temps=temps), "Largemouth Bass", ["Largemouth Bass"], True)
    assert any("front" in n for n in plan["heads_up"])


def test_plan_without_weather_still_suggests_tackle():
    fallback = snapshot()
    fallback = WeatherSnapshot(**{**fallback.__dict__, "hourly": [], "source": "fallback", "stale": True})
    plan = build_plan(fallback, "Largemouth Bass", ["Largemouth Bass"], True)
    assert plan["where"] is None and plan["when"] is None
    assert plan["lures"]


def test_plan_without_a_fish_skips_tackle():
    plan = build_plan(snapshot(), None, ["Largemouth Bass", "Bluegill"], None)
    assert plan["species"] is None
    assert plan["lures"] == [] and plan["baits"] == []
    assert plan["where"] is not None


# --- through the API ------------------------------------------------------------


@pytest.fixture()
def stub_weather(monkeypatch):
    def _install(snap: WeatherSnapshot):
        monkeypatch.setattr(rec_module, "get_weather", lambda lat, lng: snap)

    return _install


def test_api_plans_for_the_lakes_own_fish_by_default(client, seeded_lake, stub_weather):
    stub_weather(snapshot())
    body = client.post("/api/recommendations", json={"waterbody_id": seeded_lake["waterbody"].id}).json()
    plan = body["plan"]
    assert plan["species"] == "Largemouth Bass"
    assert plan["species_options"] == ["Largemouth Bass"]
    assert plan["species_on_record"] is True


def test_api_honors_the_chosen_fish(client, seeded_lake, stub_weather):
    stub_weather(snapshot())
    body = client.post(
        "/api/recommendations",
        json={"waterbody_id": seeded_lake["waterbody"].id, "target_species": "Bluegill"},
    ).json()
    assert body["plan"]["species"] == "Bluegill"
    # Not in this lake's records — said, not hidden.
    assert body["plan"]["species_on_record"] is False
