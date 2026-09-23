"""Rule-based spot scoring (PRD §5.2, build-plan item D).

    Spot Score = Access 30% + Habitat 25% + Weather 20%
               + Species Match 15% + Freshness 10%

Two properties matter more than the exact numbers, and both come straight
from the PRD:

1. **Missing signals are not zeros.** PRD §5.2: "若缺少测深或水草数据，不要
   把缺失项当作零分，而应降低置信度并重新归一化已有信号." A factor with no
   data returns `None`, is dropped from the weighted sum, and the remaining
   weights are renormalized. `confidence` is then the fraction of the
   intended signal we actually had — so a spot scored without habitat data
   reports 0.75 confidence rather than silently pretending it scored 1.00.
   Scoring a missing signal as 0 would systematically punish exactly the
   lakes we know least about, which is backwards.

2. **Every factor carries its own reason.** The PRD's whole premise (§5.2,
   and §18's "候选钓点由可解释规则评分产生，LLM 只负责解释") is that the
   ranking is explainable without the LLM. The LLM's job on Day 3 is to
   phrase these reasons, not to invent them.

Habitat is unavailable for every candidate at MVP — we have no bathymetry
or vegetation data (PRD §5.2 names exactly this gap). It is modeled as a
real factor returning `None` rather than quietly dropped, so the
confidence penalty is visible and so wiring in real habitat data later is
a data change, not a scoring-engine rewrite.

**Where the weather numbers come from:** every threshold in the weather
factor traces to `docs/weather-scoring-rationale.md`, which cites the
angling sources behind it and marks which breakpoints are judgment calls.
Read that before tuning any of them. The short version: there is no
authoritative quantitative rubric for weather-to-fishing-quality anywhere,
so these are priors calibrated to expert consensus — defensible, but not
fitted to catch data, because this project has no catch data yet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.services.weather_adapter import WeatherSnapshot

# PRD §5.2 default weights. They must sum to 1.0 — `confidence` is defined
# as the share of total weight that had data, which only means anything if
# the full set sums to one.
WEIGHT_ACCESS = 0.30
WEIGHT_HABITAT = 0.25
WEIGHT_WEATHER = 0.20
WEIGHT_SPECIES_MATCH = 0.15
WEIGHT_FRESHNESS = 0.10


@dataclass(frozen=True)
class FactorScore:
    """One scoring signal. `value is None` means "we have no data for this",
    which is different from "we have data and it's bad" (value 0.0).

    `availability` handles the in-between case: a factor that is built from
    several sub-signals and only got some of them. Weather is the live
    example — it is genuinely informed by wind and precipitation, but has no
    water-temperature source at all, which is the single best-supported
    signal in the angling literature. Reporting that as fully-available
    weather would overstate what we know, and reporting it as missing
    weather would throw away the wind data we do have. So the value stands
    on what was measured, and the *confidence* is discounted by how much of
    the factor was actually informed.
    """

    name: str
    weight: float
    value: float | None
    reason: str
    availability: float = 1.0

    @property
    def available(self) -> bool:
        return self.value is not None

    @property
    def confidence_weight(self) -> float:
        """How much of this factor's weight counts as genuinely informed."""
        return self.weight * self.availability if self.available else 0.0


@dataclass(frozen=True)
class ScoredSpot:
    score: float  # 0-1, renormalized over available factors
    confidence: float  # 0-1, share of intended signal weight that had data
    factors: list[FactorScore]
    missing_signals: list[str]


def combine_factors(factors: list[FactorScore]) -> ScoredSpot:
    """Weighted mean over *available* factors only, with the weights
    renormalized to sum to 1 across those that had data."""
    available = [f for f in factors if f.available]
    available_weight = sum(f.weight for f in available)

    if available_weight == 0:
        # No signal at all — score 0 at confidence 0. Note this is not the
        # same as "a bad spot"; the caller must not rank on score alone
        # without looking at confidence.
        return ScoredSpot(
            score=0.0,
            confidence=0.0,
            factors=factors,
            missing_signals=[f.name for f in factors],
        )

    # Score uses full weight: a partially-informed factor still gives the
    # best estimate we have from what was measured. Confidence uses the
    # discounted weight, so the uncertainty lands there instead.
    weighted = sum((f.value or 0.0) * f.weight for f in available)
    informed_weight = sum(f.confidence_weight for f in factors)
    return ScoredSpot(
        score=round(weighted / available_weight, 4),
        confidence=round(informed_weight, 4),
        factors=factors,
        missing_signals=[f.name for f in factors if not f.available],
    )


# --------------------------------------------------------------------------
# Individual factors
# --------------------------------------------------------------------------


def score_access(
    public_status: str, access_type: str, parking: bool
) -> FactorScore:
    """Access is the candidate's own property, so it's always available.

    Anything not explicitly confirmed public scores 0 rather than being
    omitted — that's a known-bad signal, not a missing one. PRD §12 makes
    "never mark an unconfirmed private area as public access" an acceptance
    criterion, so the caller is expected to filter these out entirely; the
    0 here is a second line of defense in case one slips through.
    """
    if public_status != "confirmed_public":
        return FactorScore(
            name="access",
            weight=WEIGHT_ACCESS,
            value=0.0,
            reason=f"access is '{public_status}', not confirmed public",
        )

    # Bank and pier access need no boat and no launch fee — the widest
    # audience, and the PRD's target user is explicitly a beginner.
    type_scores = {"bank": 1.0, "pier": 1.0, "park": 0.9, "boat_ramp": 0.6}
    base = type_scores.get(access_type, 0.7)
    parking_bonus = 0.0 if parking else -0.15
    value = max(0.0, min(1.0, base + parking_bonus))

    parking_note = "parking available" if parking else "no documented parking"
    return FactorScore(
        name="access",
        weight=WEIGHT_ACCESS,
        value=value,
        reason=f"confirmed public {access_type} access, {parking_note}",
    )


def score_habitat() -> FactorScore:
    """Always unavailable at MVP — no bathymetry or aquatic-vegetation data
    source is wired up yet (PRD §5.2 names this exact gap). Returning None
    costs 25% of confidence on every candidate, which is the honest
    representation: we are ranking on three quarters of the intended
    signal."""
    return FactorScore(
        name="habitat",
        weight=WEIGHT_HABITAT,
        value=None,
        reason=(
            "no bathymetry or vegetation data available — excluded from the "
            "score and deducted from confidence rather than scored as zero"
        ),
    )


def _parse_wind_mph(wind_speed: str | None) -> float | None:
    """NWS reports wind as a human string like '10 mph' or '5 to 10 mph'.
    Takes the upper bound of a range — the gustier end is what decides
    whether a spot is actually fishable."""
    if not wind_speed:
        return None
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", wind_speed)]
    if not numbers:
        return None
    return max(numbers)


#: NWS reports wind direction as the compass point the wind blows *from*
#: ("SE" = a southeast wind, blowing toward the northwest). Baitfish and
#: the plankton they follow get pushed to the shore the wind blows *into*,
#: which is the opposite point — that windblown bank is the one worth
#: fishing, and naming the wrong shore would send an angler to the dead
#: side of the lake.
_OPPOSITE_COMPASS = {
    "N": "S", "NNE": "SSW", "NE": "SW", "ENE": "WSW",
    "E": "W", "ESE": "WNW", "SE": "NW", "SSE": "NNW",
    "S": "N", "SSW": "NNE", "SW": "NE", "WSW": "ENE",
    "W": "E", "WNW": "ESE", "NW": "SE", "NNW": "SSE",
}


def downwind_shore(wind_direction: str | None) -> str | None:
    """The shore a wind blows toward — where baitfish stack up."""
    if not wind_direction:
        return None
    return _OPPOSITE_COMPASS.get(wind_direction.strip().upper())


# Weather sub-signal weights, applied *within* the 20% weather factor and
# renormalized the same way the top-level factors are — so an unavailable
# sub-signal (water temperature, always, today) doesn't silently become a
# zero either. Ordered by how well the sources actually support them; see
# docs/weather-scoring-rationale.md for the citations behind every number
# in this section.
SUB_WEIGHT_WIND = 0.45
SUB_WEIGHT_WATER_TEMP = 0.30
SUB_WEIGHT_PRECIPITATION = 0.15
SUB_WEIGHT_FRONT = 0.10

#: Wind bands in mph. The *shape* here is sourced — a light chop outscores
#: dead calm, because wind-driven current concentrates plankton on the
#: downwind shore and surface chop cuts light penetration, making fish less
#: spooky. The exact breakpoints are a judgment call: the angling literature
#: describes the curve and the mechanism, never cutoffs.
WIND_CALM_MAX = 4.0
WIND_FAVORABLE_MAX = 15.0
WIND_WORKABLE_MAX = 22.0
#: Above this, low scoring is about angler safety on open water, not the fish.
WIND_UNSAFE = 22.0

#: A drop this large across the forecast window reads as an approaching
#: front. Pre-frontal is the consensus feeding window — this is what anglers
#: reading a falling barometer are actually detecting (see the rationale doc
#: on why barometric pressure itself is deliberately not scored).
FRONT_TEMP_DROP_F = 8.0


def _score_wind(snapshot: WeatherSnapshot) -> tuple[float | None, str]:
    wind_mph = _parse_wind_mph(snapshot.current.wind_speed)
    if wind_mph is None:
        return None, "wind speed unavailable"

    speed = snapshot.current.wind_speed
    if wind_mph < WIND_CALM_MAX:
        return 0.55, f"nearly calm ({speed}) — little current to concentrate bait"
    if wind_mph <= WIND_FAVORABLE_MAX:
        shore = downwind_shore(snapshot.current.wind_direction)
        shore_note = f"the {shore} shore" if shore else "the downwind shore"
        return 1.0, (
            f"light chop ({speed} from the "
            f"{snapshot.current.wind_direction or 'unknown direction'}) pushing "
            f"plankton and baitfish toward {shore_note}"
        )
    if wind_mph <= WIND_WORKABLE_MAX:
        return 0.6, f"breezy ({speed}) — fishable but harder to control a boat"
    return 0.2, (
        f"strong wind ({speed}) — unsafe on open water, not just poor fishing"
    )


def _score_water_temperature() -> tuple[float | None, str]:
    """Always unavailable. NWS gives *air* temperature, and water temperature
    is the actually-predictive number — it lags air by days to weeks and
    stratifies with depth. Substituting air temp would be the most misleading
    thing this engine could do: authoritative-looking, and wrong in exactly
    the spring/fall conditions where it matters most. The 65-75F peak-feeding
    band and the rest of the table are in the rationale doc, ready for the day
    a real water-temp source (USGS gauges, TPWD survey data) is wired in."""
    return None, (
        "no water-temperature source — NWS reports air temperature, which is "
        "not a safe substitute, so this is excluded rather than approximated"
    )


def _score_precipitation(snapshot: WeatherSnapshot) -> tuple[float | None, str]:
    precip = snapshot.hourly[0].probability_of_precipitation if snapshot.hourly else None
    if precip is None:
        return None, "precipitation chance unavailable"
    if precip <= 20:
        return 1.0, "little chance of rain"
    if precip <= 50:
        return 0.7, f"{precip}% chance of rain"
    return 0.35, f"{precip}% chance of rain — likely to cut the trip short"


def _score_front(snapshot: WeatherSnapshot) -> tuple[float | None, str]:
    """Detects an approaching front from the forecast temperature trend.

    Only *approaching* fronts: the NWS hourly forecast looks forward, so a
    front that has already passed — the notorious post-frontal "bluebird
    sky" bite, which is the condition anglers most want warned about — is
    invisible here. Closing that needs recent observations, a real API
    addition rather than a tweak. Flagged in the rationale doc instead of
    faked.
    """
    temps = [p.temperature for p in snapshot.hourly[:12] if p.temperature is not None]
    if len(temps) < 3:
        return None, "not enough forecast data to detect a front"

    drop = max(temps) - min(temps)
    if drop >= FRONT_TEMP_DROP_F and temps.index(max(temps)) < temps.index(min(temps)):
        return 1.0, (
            f"temperature falling {drop:.0f}F across the forecast window — "
            "a front is moving in, and the hours ahead of it are the feeding window"
        )
    return 0.7, "no front signal in the forecast window"


def score_weather(snapshot: WeatherSnapshot) -> FactorScore:
    """Combines wind, water temperature, precipitation and frontal movement.

    Every threshold traces to docs/weather-scoring-rationale.md. Two choices
    there are worth knowing about at the call site:

    - **Barometric pressure is deliberately absent.** Belief in it is near
      universal among pro anglers, but a fish moving three feet vertically
      experiences a bigger pressure swing than a passing hurricane, and the
      sources conceding this conclude pressure is a *proxy* for fronts,
      wind and cloud cover. Those are scored directly, so giving pressure
      its own weight would double-count them.
    - **Water temperature is the best-supported signal and we can't measure
      it**, so it comes back unavailable and costs sub-factor confidence.

    Returns None outright when the weather adapter fell back — treating an
    outage as neutral-or-good weather would let a spot score well on data we
    never had.
    """
    if snapshot.source == "fallback":
        return FactorScore(
            name="weather",
            weight=WEIGHT_WEATHER,
            value=None,
            reason=(
                "weather service unavailable — excluded from the score "
                "rather than assumed favorable"
            ),
        )

    sub_signals = [
        (SUB_WEIGHT_WIND, *_score_wind(snapshot)),
        (SUB_WEIGHT_WATER_TEMP, *_score_water_temperature()),
        (SUB_WEIGHT_PRECIPITATION, *_score_precipitation(snapshot)),
        (SUB_WEIGHT_FRONT, *_score_front(snapshot)),
    ]

    available = [(w, v, note) for w, v, note in sub_signals if v is not None]
    if not available:
        return FactorScore(
            name="weather",
            weight=WEIGHT_WEATHER,
            value=None,
            reason="no usable weather sub-signal",
        )

    total_weight = sum(w for w, _, _ in available)
    all_weight = sum(w for w, _, _ in sub_signals)
    value = round(sum(w * (v or 0.0) for w, v, _ in available) / total_weight, 4)

    # Lead with the signals that actually moved the score, heaviest first.
    notes = [note for _, _, note in sorted(available, key=lambda s: -s[0]) if note]
    missing = [note for w, v, note in sub_signals if v is None]
    reason = "; ".join(notes)
    if missing:
        reason = f"{reason} (excluded: {'; '.join(missing)})"

    return FactorScore(
        name="weather",
        weight=WEIGHT_WEATHER,
        value=value,
        reason=reason,
        # Missing water temperature costs weather confidence rather than
        # being papered over — see the class docstring.
        availability=round(total_weight / all_weight, 4),
    )


def score_species_match(confidence_tier: str | None) -> FactorScore:
    """Scores how well-documented the target species is *in this specific
    lake*. PRD §4.2 forbids treating a statewide species list as proof a
    fish is in a given lake, so this reads the per-lake evidence tier.

    `None` means no target species was requested — a genuine absence of the
    signal (the user didn't ask about a species), so the factor drops out.
    That is different from a requested species having no evidence here,
    which is a real 0.
    """
    if confidence_tier is None:
        return FactorScore(
            name="species_match",
            weight=WEIGHT_SPECIES_MATCH,
            value=None,
            reason="no target species requested",
        )

    tiers = {"confirmed": 1.0, "likely": 0.65, "reported": 0.4}
    value = tiers.get(confidence_tier, 0.0)
    if value == 0.0:
        reason = "target species is not documented in this lake"
    else:
        reason = f"target species is '{confidence_tier}' in this lake's records"
    return FactorScore(
        name="species_match",
        weight=WEIGHT_SPECIES_MATCH,
        value=value,
        reason=reason,
    )


def score_freshness(observed_at: datetime | None, now: datetime | None = None) -> FactorScore:
    """How stale the underlying evidence is. Fishing data ages: a 2019 survey
    is weaker evidence than a 2026 one, and the PRD (§6) is explicit that
    regulations and survey data must never be cached as permanent fact."""
    if observed_at is None:
        return FactorScore(
            name="freshness",
            weight=WEIGHT_FRESHNESS,
            value=None,
            reason="no observation date on the underlying record",
        )

    now = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    age_days = max(0.0, (now - observed_at).total_seconds() / 86400)
    if age_days <= 365:
        value, note = 1.0, "within the last year"
    elif age_days <= 365 * 3:
        value, note = 0.7, f"about {age_days / 365:.0f} years old"
    elif age_days <= 365 * 6:
        value, note = 0.4, f"about {age_days / 365:.0f} years old"
    else:
        value, note = 0.2, f"over {age_days / 365:.0f} years old"

    return FactorScore(
        name="freshness",
        weight=WEIGHT_FRESHNESS,
        value=value,
        reason=f"source data {note}",
    )


# --------------------------------------------------------------------------
# Time-window advice (PRD §4.3)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TimeWindow:
    start_time: datetime
    end_time: datetime
    reason: str


def best_time_window(snapshot: WeatherSnapshot, max_hours: int = 3) -> TimeWindow | None:
    """Picks the best contiguous block in the hourly forecast, scoring each
    hour the same way `score_weather` scores current conditions.

    Returns None whenever the weather data isn't trustworthy — no hourly
    periods, or a fallback snapshot. Both checks matter: `source` is the
    authoritative signal, and testing it (not just emptiness) means a
    fallback that ever carries placeholder hourly entries still can't
    produce advice. A made-up "best time to fish" is worse than no advice.
    """
    if snapshot.source == "fallback" or not snapshot.hourly:
        return None

    hour_scores: list[float] = []
    for period in snapshot.hourly:
        # Same wind bands as the spot score, so "when to go" and "where to
        # go" can't disagree about what counts as good wind.
        wind = _parse_wind_mph(period.wind_speed)
        if wind is None:
            wind_value = 0.6
        elif wind < WIND_CALM_MAX:
            wind_value = 0.55
        elif wind <= WIND_FAVORABLE_MAX:
            wind_value = 1.0
        elif wind <= WIND_WORKABLE_MAX:
            wind_value = 0.6
        else:
            wind_value = 0.2

        precip = period.probability_of_precipitation
        if precip is None:
            precip_value = 0.8
        elif precip <= 20:
            precip_value = 1.0
        elif precip <= 50:
            precip_value = 0.7
        else:
            precip_value = 0.35

        # Low-light feeding windows. Kept modest, and kept *here* rather than
        # in the spot score, because the sources support it for timing ("when
        # to go") far better than as a property of a place — above ~75F
        # feeding shifts to dawn/dusk/night, which arrives through water
        # temperature as much as through light.
        hour = period.start_time.hour
        low_light_bonus = 0.15 if hour in (5, 6, 7, 18, 19, 20) else 0.0

        hour_scores.append(0.6 * wind_value + 0.3 * precip_value + low_light_bonus)

    window = min(max_hours, len(hour_scores))
    best_start = max(
        range(len(hour_scores) - window + 1),
        key=lambda i: sum(hour_scores[i : i + window]),
    )
    best_period = snapshot.hourly[best_start]
    last_period = snapshot.hourly[best_start + window - 1]
    # NWS hourly periods are one hour long and carry only a start time, so
    # the window ends an hour after its last period begins.
    end_time = last_period.start_time + timedelta(hours=1)

    return TimeWindow(
        start_time=best_period.start_time,
        end_time=end_time,
        reason=(
            f"steadiest conditions in the forecast window: "
            f"{best_period.short_forecast.lower()}, wind {best_period.wind_speed}"
        ),
    )
