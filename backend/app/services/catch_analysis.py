"""The angler's own catches, counted: which fish, on which bait, at what
time of day, in what weather, in which months and on which water. FishEye
Plus's log analysis (the business plan), free while FishEye is in testing.
2026-11-19.

Only the angler's own catches, public and private, whatever their gear
switch says (ADR 0056: paid features can't depend on consent). A catch a
moderator removed isn't counted.

Counts, not rates: a log holds the catches, not the hours fished without
one, so "most catches at dawn" is what it can say, not "fish bite best at
dawn". The page says how many catches each count comes from.
"""
from __future__ import annotations

import math
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.knowledge import gear as gear_list
from app.models.community import PIN_REMOVED, SKIES, TRENDS, CatchPin
from app.models.water import River
from app.models.waterbody import Waterbody
from app.services import water
from app.services.catch_weather import caught_at
from app.services.pins import GEAR_LABELS, species_label

# What "bait" counts: the /gear list's lures and its live and natural bait.
BAIT_CATEGORIES = ("lures", "bait")
BAIT_IDS = {i.id for i in gear_list.ITEMS if i.category in BAIT_CATEGORIES}
TIMES = ("dawn", "morning", "midday", "afternoon", "dusk", "night")
# Air temperature, °F: below 50, 50-64, 65-79, 80 and up.
TEMPS = (("cold", 50.0), ("cool", 65.0), ("warm", 80.0), ("hot", math.inf))
# Wind, mph: under 5, 5-14, 15 and up.
WINDS = (("calm", 5.0), ("breeze", 15.0), ("windy", math.inf))
TOP_BAITS = 8
TOP_WATERS = 6


# ------------------------------------------------------------ the sun


def sun_times(lat: float, lng: float, day: date) -> tuple[datetime | None, datetime, datetime | None]:
    """Sunrise, solar noon and sunset in UTC for a place and day: NOAA's
    general solar position formulas, within a couple of minutes in the US.
    Sunrise and sunset are None when the sun stays up or down all day."""
    g = 2 * math.pi / 365 * (day.timetuple().tm_yday - 1)
    eqtime = 229.18 * (
        0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g)
    )
    decl = (
        0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
        + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    )
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    noon = midnight + timedelta(minutes=720 - 4 * lng - eqtime)
    phi = math.radians(lat)
    cos_ha = math.cos(math.radians(90.833)) / (math.cos(phi) * math.cos(decl)) - math.tan(phi) * math.tan(decl)
    if not -1.0 <= cos_ha <= 1.0:
        return None, noon, None
    ha = math.degrees(math.acos(cos_ha))
    return noon - timedelta(minutes=4 * ha), noon, noon + timedelta(minutes=4 * ha)


def time_of_day(pin: CatchPin) -> str | None:
    """"dawn" (from an hour before sunrise to two hours after), "dusk" (two
    hours before sunset to an hour after), "night" outside those, and in
    between "midday" (an hour and a half either side of solar noon),
    "morning" or "afternoon". By that day's sun at the spot, so dawn is
    dawn in June and in December. None without a time."""
    when = caught_at(pin)
    if when is None or pin.caught_on is None or pin.caught_time is None:
        return None
    rise, noon, set_ = sun_times(pin.latitude, pin.longitude, pin.caught_on)
    if rise is None or set_ is None:
        # Days without a sunrise or a sunset (northern Alaska): the clock.
        hour = pin.caught_time.hour
        return (
            "night" if hour < 5 or hour >= 21 else "dawn" if hour < 8 else "morning" if hour < 11
            else "midday" if hour < 14 else "afternoon" if hour < 18 else "dusk"
        )
    hour = timedelta(hours=1)
    if when < rise - hour or when >= set_ + hour:
        return "night"
    if when < rise + 2 * hour:
        return "dawn"
    if when >= set_ - 2 * hour:
        return "dusk"
    if abs(when - noon) < 1.5 * hour:
        return "midday"
    return "morning" if when < noon else "afternoon"


# ------------------------------------------------------------ counting


def species_key(pin: CatchPin) -> str | None:
    if pin.species_slug:
        return pin.species_slug
    if pin.species_other and pin.species_other.strip():
        return "~" + " ".join(pin.species_other.lower().split())
    return None


def _band(value: float | None, bands: tuple[tuple[str, float], ...]) -> str | None:
    if value is None:
        return None
    return next(name for name, below in bands if value < below)


def _counts(keys: list[str | None], order: tuple[str, ...]) -> list[dict]:
    c = Counter(k for k in keys if k is not None)
    return [{"key": k, "count": c[k]} for k in order]


def analyse(db: Session, user_id: int, species: str | None = None) -> dict:
    pins = db.scalars(
        select(CatchPin)
        .where(CatchPin.user_id == user_id, CatchPin.status != PIN_REMOVED)
        .options(selectinload(CatchPin.gear), selectinload(CatchPin.weather))
        .order_by(CatchPin.id)
    ).all()

    fish: dict[str, dict] = {}
    for p in pins:
        key = species_key(p)
        if key is None:
            continue
        row = fish.setdefault(
            key,
            {"key": key, "slug": p.species_slug, "label": species_label(p) or p.species_other or key, "count": 0},
        )
        row["count"] += 1
    all_species = sorted(fish.values(), key=lambda r: (-r["count"], r["label"].lower()))

    if species:
        pins = [p for p in pins if species_key(p) == species]

    days = [p.caught_on or p.created_at.date() for p in pins]
    months = [0] * 12
    for d in days:
        months[d.month - 1] += 1

    baits: Counter[str] = Counter()
    baits_logged = 0
    for p in pins:
        used = {g.item_id for g in p.gear if g.item_id in BAIT_IDS}
        baits.update(used)
        baits_logged += bool(used)

    times = [time_of_day(p) for p in pins]
    readings = [p.weather for p in pins if p.weather is not None and (p.weather.sky or p.weather.temp_f is not None)]

    lake_count = Counter(p.waterbody_id for p in pins if p.waterbody_id)
    river_count = Counter(p.river_id for p in pins if p.river_id and not p.waterbody_id)
    waters: list[dict] = []
    if lake_count:
        for w in db.scalars(select(Waterbody).where(Waterbody.id.in_(lake_count))):
            waters.append({"kind": water.LAKE, "id": w.id, "name": w.name, "count": lake_count[w.id]})
    if river_count:
        for r in db.scalars(select(River).where(River.id.in_(river_count))):
            waters.append({"kind": water.RIVER, "id": r.id, "name": r.name, "count": river_count[r.id]})
    waters.sort(key=lambda w: (-w["count"], w["name"].lower()))

    shown_fish = [] if species else all_species
    return {
        "all_species": all_species,
        "species": species,
        "total": len(pins),
        "first_on": min(days) if days else None,
        "last_on": max(days) if days else None,
        "fish": shown_fish,
        "waters": waters[:TOP_WATERS],
        "months": months,
        "baits": [
            {"key": k, "count": n, "label": GEAR_LABELS.get(k)}
            for k, n in sorted(baits.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_BAITS]
        ],
        "baits_logged": baits_logged,
        "times": _counts(times, TIMES),
        "times_logged": sum(t is not None for t in times),
        "skies": _counts([w.sky for w in readings], SKIES),
        "trends": _counts([w.trend for w in readings], TRENDS),
        "temps": _counts([_band(w.temp_f, TEMPS) for w in readings], tuple(n for n, _ in TEMPS)),
        "winds": _counts([_band(w.wind_mph, WINDS) for w in readings], tuple(n for n, _ in WINDS)),
        "weather_logged": len(readings),
    }
