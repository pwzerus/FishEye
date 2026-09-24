"""Unit tests for the PRD §5.2 scoring engine.

The renormalization tests are the important ones — "missing data lowers
confidence and renormalizes, rather than scoring zero" is a stated PRD
requirement, and it's the kind of rule that silently regresses into
`value or 0` during a later refactor.
"""
from datetime import datetime, timedelta, timezone

from app.services import scoring
from app.services.scoring import FactorScore
from app.services.weather_adapter import (
    CurrentConditions,
    HourlyPeriod,
    WeatherAlert,
    WeatherSnapshot,
)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def _snapshot(
    *,
    source: str = "nws",
    wind_speed: str | None = "10 mph",
    wind_direction: str | None = "SE",
    precip: int | None = 10,
    hourly: list[HourlyPeriod] | None = None,
    alerts: list[WeatherAlert] | None = None,
) -> WeatherSnapshot:
    current = CurrentConditions(
        temperature=78,
        temperature_unit="F",
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        short_forecast="Partly Sunny",
        is_daytime=True,
    )
    if hourly is None:
        hourly = [
            HourlyPeriod(
                start_time=NOW,
                temperature=78,
                temperature_unit="F",
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                short_forecast="Partly Sunny",
                probability_of_precipitation=precip,
            )
        ]
    return WeatherSnapshot(
        latitude=30.0,
        longitude=-96.0,
        current=current,
        hourly=hourly,
        alerts=alerts or [],
        source=source,
        stale=source == "fallback",
        fetched_at=NOW,
    )


# --------------------------------------------------------------------------
# combine_factors — the renormalization contract
# --------------------------------------------------------------------------


def test_all_factors_available_gives_full_confidence():
    factors = [
        FactorScore("a", 0.30, 1.0, ""),
        FactorScore("b", 0.25, 1.0, ""),
        FactorScore("c", 0.20, 1.0, ""),
        FactorScore("d", 0.15, 1.0, ""),
        FactorScore("e", 0.10, 1.0, ""),
    ]
    result = scoring.combine_factors(factors)
    assert result.score == 1.0
    assert result.confidence == 1.0
    assert result.missing_signals == []


def test_missing_factor_lowers_confidence_without_lowering_score():
    """The core PRD §5.2 rule: a missing signal must not drag the score down
    the way a zero would — it comes out of confidence instead."""
    all_good = [
        FactorScore("a", 0.30, 1.0, ""),
        FactorScore("b", 0.25, 1.0, ""),
        FactorScore("c", 0.20, 1.0, ""),
    ]
    with_missing = [
        FactorScore("a", 0.30, 1.0, ""),
        FactorScore("b", 0.25, None, "no data"),
        FactorScore("c", 0.20, 1.0, ""),
    ]

    assert scoring.combine_factors(all_good).score == 1.0
    result = scoring.combine_factors(with_missing)
    assert result.score == 1.0  # unchanged — not dragged toward zero
    assert result.confidence == 0.50  # 0.30 + 0.20 of the intended weight
    assert result.missing_signals == ["b"]


def test_missing_factor_scores_differently_than_a_zero_factor():
    """Regression guard: if someone ever replaces `None` with 0.0, this test
    fails — which is the whole point."""
    missing = scoring.combine_factors(
        [FactorScore("a", 0.5, 1.0, ""), FactorScore("b", 0.5, None, "")]
    )
    zeroed = scoring.combine_factors(
        [FactorScore("a", 0.5, 1.0, ""), FactorScore("b", 0.5, 0.0, "")]
    )
    assert missing.score == 1.0
    assert zeroed.score == 0.5
    assert missing.confidence < zeroed.confidence


def test_no_available_signal_returns_zero_score_at_zero_confidence():
    result = scoring.combine_factors(
        [FactorScore("a", 0.5, None, ""), FactorScore("b", 0.5, None, "")]
    )
    assert result.score == 0.0
    assert result.confidence == 0.0
    assert set(result.missing_signals) == {"a", "b"}


def test_partially_informed_factor_costs_confidence_but_not_score():
    """A factor built from sub-signals that only got some of them (weather
    with too little forecast data to detect a front) should still
    contribute its measured value at full weight, while the uncertainty
    lands in confidence."""
    partial = scoring.combine_factors(
        [
            FactorScore("a", 0.5, 1.0, ""),
            FactorScore("b", 0.5, 1.0, "", availability=0.6),
        ]
    )
    assert partial.score == 1.0  # value stands on what was measured
    assert partial.confidence == 0.8  # 0.5 + (0.5 x 0.6)
    # Partially informed is not the same as missing — it still has data.
    assert partial.missing_signals == []


def test_weather_sub_weights_sum_to_one():
    """The weather factor's availability fraction is sub_available/sub_total,
    which only reads as 'share informed' if the sub-weights sum to 1."""
    total = (
        scoring.SUB_WEIGHT_WIND
        + scoring.SUB_WEIGHT_PRECIPITATION
        + scoring.SUB_WEIGHT_FRONT
    )
    assert total == 1.0


def test_prd_weights_sum_to_one():
    """confidence is defined as 'share of intended weight that had data',
    which only holds if the full weight set sums to 1."""
    total = (
        scoring.WEIGHT_ACCESS
        + scoring.WEIGHT_WEATHER
        + scoring.WEIGHT_SPECIES_MATCH
        + scoring.WEIGHT_FRESHNESS
    )
    assert total == 1.0


# --------------------------------------------------------------------------
# Individual factors
# --------------------------------------------------------------------------


def test_access_scores_bank_with_parking_above_boat_ramp_without():
    bank = scoring.score_access("confirmed_public", "bank", parking=True)
    ramp = scoring.score_access("confirmed_public", "boat_ramp", parking=False)
    assert bank.value is not None and ramp.value is not None
    assert bank.value > ramp.value


def test_unconfirmed_access_scores_zero_rather_than_missing():
    """An unconfirmed private area is known-bad, not unknown — it must score
    0 (and be filtered upstream), never drop out and inflate confidence."""
    factor = scoring.score_access("unconfirmed", "bank", parking=True)
    assert factor.value == 0.0
    assert factor.available is True


def test_weather_is_unavailable_when_adapter_fell_back():
    factor = scoring.score_weather(_snapshot(source="fallback"))
    assert factor.value is None
    assert "unavailable" in factor.reason


def test_light_chop_scores_above_dead_calm_and_above_gale():
    light = scoring.score_weather(_snapshot(wind_speed="10 mph"))
    calm = scoring.score_weather(_snapshot(wind_speed="1 mph"))
    gale = scoring.score_weather(_snapshot(wind_speed="30 mph"))
    assert light.value is not None and calm.value is not None and gale.value is not None
    assert light.value > calm.value
    assert light.value > gale.value
    assert "baitfish" in light.reason


def test_windblown_shore_is_the_one_the_wind_blows_toward():
    """NWS reports the direction wind comes *from*, so an SE wind pushes
    baitfish to the NW shore. Naming the SE shore here would send an angler
    to the dead side of the lake."""
    assert scoring.downwind_shore("SE") == "NW"
    assert scoring.downwind_shore("N") == "S"
    assert scoring.downwind_shore("WSW") == "ENE"
    assert scoring.downwind_shore(None) is None
    assert scoring.downwind_shore("variable") is None

    factor = scoring.score_weather(_snapshot(wind_speed="10 mph", wind_direction="SE"))
    assert "toward the NW shore" in factor.reason


def test_wind_range_uses_upper_bound():
    assert scoring._parse_wind_mph("5 to 15 mph") == 15.0
    assert scoring._parse_wind_mph("10 mph") == 10.0
    assert scoring._parse_wind_mph(None) is None
    assert scoring._parse_wind_mph("calm") is None


def test_weather_never_claims_full_availability_with_too_little_forecast_data():
    """A single forecast hour isn't enough to detect an approaching front.
    The weather factor must report that gap as reduced availability rather
    than scoring as if it had every sub-signal."""
    factor = scoring.score_weather(_snapshot())
    assert factor.availability < 1.0
    assert "not enough forecast data" in factor.reason
    # It still contributes — wind and precipitation data are real data.
    assert factor.value is not None
    assert factor.confidence_weight < factor.weight


def test_weather_is_fully_available_with_a_normal_forecast_window():
    """With enough hourly periods to score wind, precipitation and a front,
    nothing is missing — there's no sub-signal left that can only ever be
    None (water temperature was removed for exactly that reason)."""
    hourly = [
        HourlyPeriod(
            start_time=NOW + timedelta(hours=i),
            temperature=78,
            temperature_unit="F",
            wind_speed="10 mph",
            wind_direction="SE",
            short_forecast="Partly Sunny",
            probability_of_precipitation=10,
        )
        for i in range(12)
    ]
    factor = scoring.score_weather(_snapshot(hourly=hourly))
    assert factor.availability == 1.0


def test_barometric_pressure_is_not_a_scoring_input():
    """Deliberate omission, not an oversight: a fish moving three feet
    vertically sees a bigger pressure change than a passing hurricane, so
    pressure is a proxy for fronts/wind/cloud rather than a cause. Those are
    scored directly; adding pressure would double-count them. See
    docs/weather-scoring-rationale.md. This test exists so the omission is a
    recorded decision rather than something a later contributor 'fixes'."""
    import inspect

    source = inspect.getsource(scoring)
    sub_weights = [
        name for name in dir(scoring) if name.startswith("SUB_WEIGHT_")
    ]
    assert not any("PRESSURE" in name for name in sub_weights)
    # The reasoning must stay documented in the module itself.
    assert "pressure" in source.lower()


def test_approaching_front_is_detected_from_the_temperature_trend():
    """Pre-frontal is the consensus feeding window, and a falling forecast
    temperature is what anglers reading a barometer are really detecting."""

    def period(hour: int, temp: int) -> HourlyPeriod:
        return HourlyPeriod(
            start_time=datetime(2026, 9, 22, hour, tzinfo=timezone.utc),
            temperature=temp,
            temperature_unit="F",
            wind_speed="10 mph",
            wind_direction="SE",
            short_forecast="Cloudy",
            probability_of_precipitation=20,
        )

    falling = _snapshot(hourly=[period(h, t) for h, t in zip(range(12, 18), [88, 86, 82, 78, 76, 74])])
    steady = _snapshot(hourly=[period(h, t) for h, t in zip(range(12, 18), [80, 81, 80, 79, 80, 80])])

    front = scoring.score_weather(falling)
    no_front = scoring.score_weather(steady)
    assert "front is moving in" in front.reason
    assert "front" not in no_front.reason or "no front signal" in no_front.reason
    assert front.value is not None and no_front.value is not None
    assert front.value > no_front.value


def test_rising_temperature_is_not_read_as_a_front():
    """A warming trend of the same magnitude must not trip front detection —
    the ordering of the max and min is what distinguishes them."""

    def period(hour: int, temp: int) -> HourlyPeriod:
        return HourlyPeriod(
            start_time=datetime(2026, 9, 22, hour, tzinfo=timezone.utc),
            temperature=temp,
            temperature_unit="F",
            wind_speed="10 mph",
            wind_direction="SE",
            short_forecast="Sunny",
            probability_of_precipitation=10,
        )

    warming = _snapshot(hourly=[period(h, t) for h, t in zip(range(8, 14), [70, 74, 78, 80, 82, 84])])
    factor = scoring.score_weather(warming)
    assert "front is moving in" not in factor.reason


def test_heavy_rain_chance_lowers_weather_score():
    dry = scoring.score_weather(_snapshot(precip=5))
    wet = scoring.score_weather(_snapshot(precip=80))
    assert dry.value is not None and wet.value is not None
    assert dry.value > wet.value


def test_species_match_tiers_are_ordered():
    confirmed = scoring.score_species_match("confirmed")
    likely = scoring.score_species_match("likely")
    reported = scoring.score_species_match("reported")
    absent = scoring.score_species_match("")
    assert confirmed.value and likely.value and reported.value is not None
    assert confirmed.value > likely.value > reported.value > absent.value


def test_no_target_species_drops_the_factor_instead_of_scoring_zero():
    """Not asking about a species isn't evidence against a spot."""
    factor = scoring.score_species_match(None)
    assert factor.value is None
    assert factor.available is False


def test_freshness_decays_with_age():
    recent = scoring.score_freshness(NOW - timedelta(days=30), now=NOW)
    old = scoring.score_freshness(NOW - timedelta(days=365 * 4), now=NOW)
    ancient = scoring.score_freshness(NOW - timedelta(days=365 * 10), now=NOW)
    assert recent.value is not None and old.value is not None and ancient.value is not None
    assert recent.value > old.value > ancient.value


def test_freshness_handles_naive_datetimes():
    """The DB stores naive datetimes (SQLite), so the factor must not blow up
    comparing them against an aware 'now'."""
    naive = datetime(2026, 9, 1, 12, 0)
    factor = scoring.score_freshness(naive, now=NOW)
    assert factor.value == 1.0


def test_freshness_unavailable_without_a_date():
    assert scoring.score_freshness(None).value is None


# --------------------------------------------------------------------------
# Time window
# --------------------------------------------------------------------------


def test_best_time_window_prefers_the_calmer_block():
    def period(hour: int, wind: str, precip: int) -> HourlyPeriod:
        return HourlyPeriod(
            start_time=datetime(2026, 9, 22, hour, tzinfo=timezone.utc),
            temperature=80,
            temperature_unit="F",
            wind_speed=wind,
            wind_direction="S",
            short_forecast="Sunny",
            probability_of_precipitation=precip,
        )

    hourly = [
        period(10, "30 mph", 90),
        period(11, "30 mph", 90),
        period(12, "8 mph", 5),
        period(13, "8 mph", 5),
        period(14, "8 mph", 5),
    ]
    window = scoring.best_time_window(_snapshot(hourly=hourly), max_hours=3)
    assert window is not None
    assert window.start_time.hour == 12
    assert window.end_time.hour == 15  # 3-hour window ending after the 14:00 period


def test_no_time_window_without_hourly_data():
    """Fallback mode has no hourly data — inventing a 'best time to fish'
    would be worse than saying nothing."""
    assert scoring.best_time_window(_snapshot(source="fallback", hourly=[])) is None


def test_no_time_window_from_a_fallback_snapshot_even_if_it_has_hourly_data():
    """Defense in depth: `source` is authoritative. If a fallback snapshot
    ever carries placeholder hourly periods, we still must not turn them
    into time-of-day advice."""
    populated_fallback = _snapshot(source="fallback")
    assert populated_fallback.hourly  # the helper gave it hourly data
    assert scoring.best_time_window(populated_fallback) is None
