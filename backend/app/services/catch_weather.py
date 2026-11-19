"""The weather when and where a catch was made (models CatchWeather), for
the angler's own catch analysis (services/catch_analysis.py). 2026-11-19.

Looked up from the National Weather Service: the report of the airport
station nearest the spot, from the list in app/data/nws_stations.json
(tools/weather/nws_stations.py). The spot never leaves FishEye: the nearest
station is found here, and only its id and a time window go to
api.weather.gov. Its data is public domain ("open data, free to use for any
purpose", weather.gov/documentation/services-web-api).

The weather service keeps seven days of station reports ("only 7 days of
observations are retained"), so a catch is looked up only when it has a time
and was made within the last six and a half days (`can_look_up`). For an
older catch the angler can pick the sky themselves (WEATHER_ANGLER).

A lookup runs after the catch is saved, off the request (`schedule`), and
again from the analysis page for a recent catch whose lookup failed
(`pending`). A station that answered without a report for that hour leaves a
row with every reading empty, so it isn't asked again; a network failure
leaves no row, so it is.
"""
from __future__ import annotations

import json
import logging
import math
import time as clock
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.data_import.provenance import USER_AGENT
from app.db.types import utcnow
from app.models.community import PIN_REMOVED, WEATHER_NWS, CatchPin, CatchWeather
from app.services.geo import haversine_km

logger = logging.getLogger(__name__)

NWS = "https://api.weather.gov"
STATIONS_FILE = Path(__file__).resolve().parents[1] / "data" / "nws_stations.json"
# Seven days are kept; the lookup also reads the three and a half hours
# before the catch, for the pressure trend.
LOOKUP_DAYS = 6.5
NEAREST = 3  # stations tried, nearest first
MAX_STATION_KM = 80.0
# A report this close to the catch's time stands for it. Airport stations
# report every hour, a few minutes before the hour.
REPORT_WITHIN = timedelta(minutes=75)
# The pressure three hours before, read from a report this close to it.
TREND_BACK = timedelta(hours=3)
TREND_WITHIN = timedelta(minutes=50)
# hPa over three hours. Less than 1 either way reads as steady.
TREND_HPA = 1.0
REQUEST_TIMEOUT = 10.0


@dataclass(frozen=True)
class Station:
    id: str
    lat: float
    lng: float


@dataclass(frozen=True)
class Reading:
    at: datetime
    sky: str | None
    temp_f: float | None
    wind_mph: float | None
    pressure_hpa: float | None


@dataclass(frozen=True)
class Weather:
    """What a lookup found. Every reading None: the stations answered, but
    none had a report near that time."""

    station: str | None
    observed_at: datetime | None
    sky: str | None
    temp_f: float | None
    wind_mph: float | None
    pressure_hpa: float | None
    trend: str | None


NO_REPORT = Weather(None, None, None, None, None, None, None)

Fetch = Callable[[str, dict[str, str]], dict]


# ------------------------------------------------------------- when


def caught_at(pin: CatchPin) -> datetime | None:
    """The catch's moment in UTC, from its day, its time by the angler's
    clock, and that clock's offset. None without all three."""
    if pin.caught_on is None or pin.caught_time is None or pin.caught_utc_offset is None:
        return None
    local = datetime.combine(pin.caught_on, pin.caught_time.replace(second=0, microsecond=0))
    return (local - timedelta(minutes=pin.caught_utc_offset)).replace(tzinfo=timezone.utc)


def can_look_up(pin: CatchPin, now: datetime | None = None) -> bool:
    """Whether the weather service still has reports for the catch's time."""
    when = caught_at(pin)
    if when is None:
        return False
    now = now or datetime.now(timezone.utc)
    return now - timedelta(days=LOOKUP_DAYS) <= when <= now + timedelta(hours=1)


# ----------------------------------------------------------- stations


@lru_cache(maxsize=1)
def stations() -> tuple[Station, ...]:
    try:
        rows = json.loads(STATIONS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("No %s: catches get no weather until tools/weather/nws_stations.py is run.", STATIONS_FILE)
        return ()
    return tuple(Station(r["id"], float(r["lat"]), float(r["lng"])) for r in rows)


def nearest_stations(lat: float, lng: float, among: tuple[Station, ...] | None = None) -> list[Station]:
    """The NEAREST stations within MAX_STATION_KM of the spot, nearest first."""
    pool = stations() if among is None else among
    # A cheap box first: a degree of latitude is 111 km, and a degree of
    # longitude no less than 40 km anywhere in the US but northern Alaska.
    near = [s for s in pool if abs(s.lat - lat) <= 1.0 and abs(s.lng - lng) <= 2.5]
    ranked = sorted((haversine_km(lat, lng, s.lat, s.lng), s.id, s) for s in near)
    return [s for km, _id, s in ranked if km <= MAX_STATION_KM][:NEAREST]


# ------------------------------------------------------------ reports


_SNOW = {"snow", "snow_grains", "snow_pellets", "ice_pellets", "ice_crystals", "blowing_snow"}
_RAIN = {"rain", "drizzle", "showers", "thunderstorms", "freezing_rain", "freezing_drizzle", "hail", "small_hail"}
_COVER = {"CLR": 0, "SKC": 0, "NSC": 0, "NCD": 0, "FEW": 1, "SCT": 2, "BKN": 3, "OVC": 4, "VV": 4}


def sky_of(props: dict) -> str | None:
    """"clear", "partly", "cloudy", "rain" or "snow", from a station report:
    snow or rain falling first, then the most cloud reported (a few clouds
    count as clear, scattered as partly cloudy, broken or overcast as
    cloudy), then the report's own words."""
    falling = {str(w.get("weather") or "") for w in props.get("presentWeather") or [] if isinstance(w, dict)}
    if falling & _SNOW:
        return "snow"
    if falling & _RAIN:
        return "rain"
    covers = [_COVER[c["amount"]] for c in props.get("cloudLayers") or [] if isinstance(c, dict) and c.get("amount") in _COVER]
    if covers:
        most = max(covers)
        return "clear" if most <= 1 else "partly" if most == 2 else "cloudy"
    if "fog_mist" in falling:
        return "cloudy"
    text = str(props.get("textDescription") or "").lower()
    # "Partly" before "cloudy": "Partly Cloudy" is partly cloudy.
    for words, sky in (
        (("snow", "sleet", "ice"), "snow"),
        (("rain", "drizzle", "shower", "thunder"), "rain"),
        (("partly",), "partly"),
        (("cloudy", "overcast", "fog", "mist"), "cloudy"),
        (("clear", "sunny", "fair"), "clear"),
    ):
        if any(w in text for w in words):
            return sky
    return None


def _value(props: dict, key: str) -> float | None:
    v = (props.get(key) or {}).get("value")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def reading(props: dict) -> Reading | None:
    try:
        at = datetime.fromisoformat(str(props["timestamp"])).astimezone(timezone.utc)
    except (KeyError, ValueError):
        return None
    temp_c = _value(props, "temperature")
    wind_kmh = _value(props, "windSpeed")
    pressure_pa = _value(props, "barometricPressure") or _value(props, "seaLevelPressure")
    return Reading(
        at=at,
        sky=sky_of(props),
        temp_f=round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else None,
        wind_mph=round(wind_kmh / 1.609344, 1) if wind_kmh is not None else None,
        pressure_hpa=round(pressure_pa / 100, 1) if pressure_pa is not None else None,
    )


def pick(readings: list[Reading], when: datetime, station: str) -> Weather | None:
    """The report nearest `when` (within REPORT_WITHIN) that says something,
    with the pressure trend over the three hours before it."""
    usable = [r for r in readings if r.sky is not None or r.temp_f is not None]
    near = [r for r in usable if abs(r.at - when) <= REPORT_WITHIN]
    if not near:
        return None
    best = min(near, key=lambda r: (abs(r.at - when), r.at))
    trend = None
    if best.pressure_hpa is not None:
        target = best.at - TREND_BACK
        before = [r for r in readings if r.pressure_hpa is not None and abs(r.at - target) <= TREND_WITHIN]
        if before:
            then = min(before, key=lambda r: abs(r.at - target))
            change = best.pressure_hpa - (then.pressure_hpa or 0.0)
            trend = "rising" if change >= TREND_HPA else "falling" if change <= -TREND_HPA else "steady"
    return Weather(station, best.at, best.sky, best.temp_f, best.wind_mph, best.pressure_hpa, trend)


def _fetch(url: str, params: dict[str, str]) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    with httpx.Client(timeout=REQUEST_TIMEOUT, headers=headers) as client:
        for attempt in range(2):
            try:
                r = client.get(url, params=params)
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPError, ValueError):
                if attempt:
                    raise
                clock.sleep(1.0)
    raise RuntimeError("unreachable")


def look_up(lat: float, lng: float, when: datetime, fetch: Fetch = _fetch) -> Weather | None:
    """The weather at `when` by the nearest station with a report then.
    NO_REPORT when the stations answered without one, None when none could
    be asked (no station near, or the weather service didn't answer): then
    it's tried again later."""
    near = nearest_stations(lat, lng)
    if not near:
        return None
    params = {
        "start": (when - TREND_BACK - TREND_WITHIN).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": (when + REPORT_WITHIN).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    answered = False
    for station in near:
        try:
            data = fetch(f"{NWS}/stations/{station.id}/observations", params)
        except Exception as exc:  # noqa: BLE001 - one station down mustn't stop the next
            logger.info("Weather for a catch: %s didn't answer (%s).", station.id, exc)
            continue
        answered = True
        found = [r for f in data.get("features") or [] if (r := reading(f.get("properties") or {})) is not None]
        weather = pick(found, when, station.id)
        if weather is not None:
            return weather
    return NO_REPORT if answered else None


# ------------------------------------------------------------ storing


def enabled() -> bool:
    return get_settings().catch_weather == "on"


def needs_lookup(pin: CatchPin, now: datetime | None = None) -> bool:
    return pin.weather is None and pin.status != PIN_REMOVED and can_look_up(pin, now)


def fill(pin_id: int, session_factory: Callable[[], Session] | None = None, fetch: Fetch = _fetch) -> None:
    """Look up and store one catch's weather. Runs after the response, in
    its own session; never raises."""
    if session_factory is None:
        from app.db.session import SessionLocal

        session_factory = SessionLocal
    db = session_factory()
    try:
        pin = db.get(CatchPin, pin_id)
        if pin is None or not needs_lookup(pin):
            return
        when = caught_at(pin)
        assert when is not None
        weather = look_up(pin.latitude, pin.longitude, when, fetch)
        if weather is None:
            return
        db.add(
            CatchWeather(
                pin_id=pin.id,
                source=WEATHER_NWS,
                station=weather.station,
                observed_at=weather.observed_at,
                sky=weather.sky,
                temp_f=weather.temp_f,
                wind_mph=weather.wind_mph,
                pressure_hpa=weather.pressure_hpa,
                trend=weather.trend,
                created_at=utcnow(),
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()  # another lookup of the same catch got there first
    except Exception:  # noqa: BLE001 - weather is a nicety; the catch is saved
        db.rollback()
        logger.exception("Weather lookup for catch %s failed.", pin_id)
    finally:
        db.close()


def schedule(background, pin: CatchPin) -> None:
    """Queue `fill` after the response when the catch can be looked up."""
    if enabled() and needs_lookup(pin):
        background.add_task(fill, pin.id)


def pending(db: Session, user_id: int, limit: int = 5, now: datetime | None = None) -> list[int]:
    """The angler's recent catches still without weather, newest first: a
    lookup that failed is tried again when they open their analysis."""
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(days=LOOKUP_DAYS + 1)).date()
    pins = db.scalars(
        select(CatchPin)
        .where(
            CatchPin.user_id == user_id,
            CatchPin.caught_on >= since,
            CatchPin.caught_time.is_not(None),
            CatchPin.caught_utc_offset.is_not(None),
            ~CatchPin.weather.has(),
        )
        .order_by(CatchPin.caught_on.desc(), CatchPin.id.desc())
    ).all()
    return [p.id for p in pins if needs_lookup(p, now)][:limit]
