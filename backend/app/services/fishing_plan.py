"""Today's plan for one lake: which bank, when, and what to throw.

The lake page used to rank access points with a weighted score. That told an
angler little they could act on, and the number looked like a measurement it
wasn't. This module answers the questions people actually ask on the way to
the water instead:

- **Where** — the bank today's wind is blowing into (it stacks up baitfish),
  the sheltered bank when the wind is too strong to fish, or cover and shade
  when there's no wind to speak of.
- **When** — the morning or evening bite window from `scoring.bite_windows`.
- **What** — lures *and* bait for the chosen fish, picked by that window's
  conditions (light, wind, cloud, rain, an incoming front) from the species
  guide's own lists. A rule never names a lure the guide doesn't list, and
  every pick says why it was picked, so two different days give two different
  answers.
- **Heads-up** — only when something would change the trip: a front, strong
  wind, thunder, likely rain. A normal day gets no label at all.

Everything is a plain rule over the NWS forecast. Water temperature is left
out on purpose: NWS doesn't report it, and air temperature is a poor stand-in
(docs/weather-scoring-rationale.md).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.knowledge.species_guides import GUIDES, SpeciesGuide, get_guide, slugify
from app.services import scoring
from app.services.scoring import TimeWindow
from app.services.weather_adapter import HourlyPeriod, WeatherSnapshot

#: Wind bands, in mph — shared with the scoring module so the plan and the
#: bite windows can't disagree about what counts as calm or too windy.
CALM_BELOW = scoring.WIND_CALM_MAX
CHOP_FROM = 8.0
TOO_WINDY_ABOVE = scoring.WIND_WORKABLE_MAX
RAIN_LIKELY = 50

#: How many lure and bait suggestions to show. Fish caught almost only on
#: bait (catfish) get two bait picks instead.
LURE_PICKS = 2
BAIT_PICKS = 1


@dataclass(frozen=True)
class Conditions:
    """The weather during the window someone is planning around."""

    wind_mph: float | None
    wind_from: str | None
    wind_text: str | None
    sky: str  # "thunder" | "rain" | "cloudy" | "mixed" | "sunny" | "unknown"
    forecast_text: str
    rain_chance: int | None
    temperature: float | None
    low_light: bool
    light_word: str  # "dawn" | "dusk" — for "at dawn, …" phrasing
    front_drop_f: float | None  # set when the temperature is about to fall sharply

    @property
    def calm(self) -> bool:
        return self.wind_mph is not None and self.wind_mph < CALM_BELOW

    @property
    def choppy(self) -> bool:
        return self.wind_mph is not None and CHOP_FROM <= self.wind_mph <= TOO_WINDY_ABOVE

    @property
    def too_windy(self) -> bool:
        return self.wind_mph is not None and self.wind_mph > TOO_WINDY_ABOVE

    @property
    def overcast(self) -> bool:
        return self.sky in ("cloudy", "rain", "thunder")

    @property
    def bright(self) -> bool:
        return self.sky == "sunny" and not self.low_light

    @property
    def wet(self) -> bool:
        return self.sky in ("rain", "thunder") or (self.rain_chance or 0) >= RAIN_LIKELY

    @property
    def front(self) -> bool:
        return self.front_drop_f is not None


def _sky(text: str) -> str:
    t = text.lower()
    if "thunder" in t or "t-storm" in t:
        return "thunder"
    if any(w in t for w in ("rain", "shower", "drizzle")):
        return "rain"
    if "partly" in t:
        return "mixed"
    if any(w in t for w in ("cloudy", "overcast", "fog")):
        return "cloudy"
    if "sunny" in t or "clear" in t:
        return "sunny"
    return "unknown"


def _front_drop(snapshot: WeatherSnapshot) -> float | None:
    """How far the temperature falls in the next 24 forecast hours, when the
    fall is sharp enough to read as a front (same threshold as scoring)."""
    temps = [p.temperature for p in snapshot.hourly[:24] if p.temperature is not None]
    if len(temps) < 3:
        return None
    peak = temps.index(max(temps))
    trough = min(range(peak, len(temps)), key=lambda i: temps[i])
    drop = temps[peak] - temps[trough]
    return drop if drop >= scoring.FRONT_TEMP_DROP_F else None


def _block(snapshot: WeatherSnapshot, window: TimeWindow) -> list[HourlyPeriod]:
    return [p for p in snapshot.hourly if window.start_time <= p.start_time < window.end_time]


def conditions_for(snapshot: WeatherSnapshot, window: TimeWindow) -> Conditions:
    block = _block(snapshot, window) or snapshot.hourly[:1]
    first = block[0]
    winds = [(scoring._parse_wind_mph(p.wind_speed), p) for p in block]
    windiest = max(winds, key=lambda w: w[0] or -1.0)
    rain = [p.probability_of_precipitation for p in block if p.probability_of_precipitation is not None]
    skies = [_sky(p.short_forecast) for p in block]
    # The worst sky in the window decides: one stormy hour matters more than
    # two calm ones.
    order = ("thunder", "rain", "cloudy", "mixed", "sunny", "unknown")
    sky = min(skies, key=order.index)
    return Conditions(
        wind_mph=windiest[0],
        wind_from=(windiest[1].wind_direction or "").strip().upper() or None,
        wind_text=windiest[1].wind_speed,
        sky=sky,
        forecast_text=first.short_forecast,
        rain_chance=max(rain) if rain else None,
        temperature=first.temperature,
        low_light=any(p.start_time.hour in scoring.LOW_LIGHT_HOURS for p in block),
        light_word="dawn" if (window.label or "") == "morning" or first.start_time.hour < 12 else "dusk",
        front_drop_f=_front_drop(snapshot),
    )


# --- where ------------------------------------------------------------------


def where_to_fish(c: Conditions) -> dict:
    if c.wind_mph is None:
        return {"shore": None, "text": "Start on points and around cover: docks, fallen trees, weed edges."}
    if c.too_windy:
        if c.wind_from:
            return {
                "shore": c.wind_from,
                "text": f"Wind up to {c.wind_mph:.0f} mph. Fish the sheltered {c.wind_from} bank, "
                "where the water is calmer and you can still cast.",
            }
        return {"shore": None, "text": f"Wind up to {c.wind_mph:.0f} mph. Look for a sheltered cove out of the wind."}
    if c.calm:
        return {
            "shore": None,
            "text": "Little wind, so no bank stands out. Fish shade and cover: docks, fallen trees, weed edges.",
        }
    shore = scoring.downwind_shore(c.wind_from)
    if shore is None:
        return {"shore": None, "text": "Fish the bank the wind is blowing into, starting on points and cover."}
    return {
        "shore": shore,
        "text": f"Try the {shore} bank. The {c.wind_from} wind is pushing baitfish toward it, "
        "so start on the points and cover along that side.",
    }


# --- what -------------------------------------------------------------------

Why = str | Callable[[Conditions], str]


@dataclass(frozen=True)
class Rule:
    when: Callable[[Conditions], bool]
    pick: str  # must be one of the guide's own lures / live baits
    why: Why


@dataclass(frozen=True)
class Tackle:
    lures: tuple[Rule, ...] = ()
    lure_fallback: tuple[tuple[str, str], ...] = ()
    baits: tuple[Rule, ...] = ()
    bait_fallback: tuple[tuple[str, str], ...] = ()
    lure_note: str | None = None


def _always(_: Conditions) -> bool:
    return True


LMB_CRANK = "Crankbaits and ¼–½ oz lipless crankbaits"
LMB_SHINER = "Large live shiners (8–9 in) under a bobber."
WHITE_BASS_TOP = "Topwater lures when schools are breaking the surface"
SPOT_WORM = "4–6 in straight-tail worms (green pumpkin or watermelon) on a shaky head or drop shot"
STRIPER_POPPER = "6 in pencil poppers (topwater)"
STRIPER_SLAB = "1–2 oz slabs in chartreuse, chrome or white"
HYBRID_MARABOU = "White or chartreuse marabou jigs in low light"
BLUEGILL_WORM = "A small piece of worm or nightcrawler, just enough to cover the hook"

TACKLE: dict[str, Tackle] = {
    "Largemouth Bass": Tackle(
        lures=(
            Rule(lambda c: c.front, LMB_CRANK, "A front is on the way, and bass often feed hard before it. Cover water fast."),
            Rule(
                lambda c: c.low_light and not c.too_windy,
                "Topwater lures",
                lambda c: f"Low light at {c.light_word}: bass come up and hit surface lures.",
            ),
            Rule(
                lambda c: c.choppy or c.overcast,
                "Spinnerbaits",
                "Wind chop and cloud cover hide your line, and bass chase a moving, flashing bait.",
            ),
            Rule(lambda c: c.choppy, LMB_CRANK, "Run it along the windblown bank to cover water quickly."),
            Rule(
                lambda c: c.calm or c.bright,
                "Plastic worms",
                "Calm, bright water makes bass cautious. Crawl a worm slowly through cover.",
            ),
            Rule(lambda c: c.bright, "Jigs", "Bright sun pushes bass tight to cover. Pitch a jig right into it."),
        ),
        lure_fallback=(
            ("Plastic worms", "Works in almost any conditions. Fish it slowly near cover."),
            ("Spinnerbaits", "A good search bait for finding active fish."),
        ),
        baits=(
            Rule(
                lambda c: c.calm or c.bright,
                LMB_SHINER,
                "When bass won't chase, a live shiner drifting past cover is hard for them to refuse.",
            ),
        ),
        bait_fallback=((LMB_SHINER, "Fish it next to cover. Bass take a real shiner faster than any plastic."),),
    ),
    "Spotted Bass": Tackle(
        lures=(
            Rule(
                lambda c: c.bright or c.calm,
                SPOT_WORM,
                "Clear, bright conditions. A small finesse worm near rock gets bit when bigger baits don't.",
            ),
            Rule(
                lambda c: c.choppy or c.overcast,
                "5 in stick-style worms",
                "With some wind or cloud, swim a stick worm along rocky banks and points.",
            ),
        ),
        lure_fallback=(
            (SPOT_WORM, "Spotted bass favor small soft plastics. Drag it slowly near rock."),
            ("5 in stick-style worms", "Let it fall slowly along drop-offs."),
        ),
    ),
    "White Bass": Tackle(
        lures=(
            Rule(
                lambda c: c.low_light,
                WHITE_BASS_TOP,
                lambda c: f"At {c.light_word}, schools chase shad to the surface. Watch for splashes and cast into them.",
            ),
            Rule(
                lambda c: c.choppy,
                "Small crankbaits",
                "Wind pushes shad onto the windblown bank and white bass follow. Retrieve steadily along it.",
            ),
            Rule(
                lambda c: c.choppy or c.overcast,
                "Inline spinners",
                "A flashing spinner stands out in choppy or cloudy water.",
            ),
            Rule(
                lambda c: c.bright,
                "Slabs and jigging spoons",
                "In bright midday sun the schools drop deeper. Jig a slab near the bottom.",
            ),
        ),
        lure_fallback=(
            ("2–3 in curly-tail grubs on a jighead", "Easy and reliable: cast, let it sink, retrieve steadily."),
            ("Inline spinners", "Covers water quickly to find a school."),
        ),
        bait_fallback=(("2–4 in minnows or shad", "Fish it where you find a school, under a bobber or on a light weight."),),
    ),
    "Striped Bass": Tackle(
        lures=(
            Rule(
                lambda c: c.low_light,
                STRIPER_POPPER,
                lambda c: f"Stripers push bait to the surface at {c.light_word}. A big popper draws explosive strikes.",
            ),
            Rule(
                lambda c: c.choppy,
                "Swimbaits",
                "Wind stirs up bait along the windblown bank. Swim a shad-like bait through it.",
            ),
            Rule(lambda c: c.bright, STRIPER_SLAB, "In bright sun stripers go deeper. Jig a heavy slab under the schools."),
        ),
        lure_fallback=(
            (STRIPER_SLAB, "Jig it under schools of bait."),
            ("Bucktail jigs", "A dependable all-round striper lure."),
        ),
        bait_fallback=(("Live threadfin or gizzard shad", "Drift live shad where you find fish. The most reliable way to catch stripers."),),
    ),
    "Hybrid Striped Bass": Tackle(
        lures=(
            Rule(
                lambda c: c.low_light,
                HYBRID_MARABOU,
                lambda c: f"Low light at {c.light_word}. A white or chartreuse jig shows up well.",
            ),
            Rule(
                lambda c: c.choppy or c.front,
                "½ oz lipless crankbaits",
                "Cover water fast along the windblown side, where shad gather.",
            ),
            Rule(lambda c: c.bright, "¼–1 oz slabs", "Bright sun sends hybrids deeper. Fish a slab straight down."),
        ),
        lure_fallback=(
            ("Grubs on 1/8–½ oz jigheads", "An easy all-round choice. Cast and retrieve steadily."),
            ("½ oz lipless crankbaits", "Covers water fast to find a school."),
        ),
        bait_fallback=(("2–4 in live shad or fathead minnows", "Hybrids rarely pass up live shad or minnows."),),
    ),
    "Channel Catfish": Tackle(
        baits=(
            Rule(
                lambda c: c.low_light,
                "Nightcrawlers",
                lambda c: "Catfish feed more actively from dusk into the night. Fish a nightcrawler on the bottom."
                if c.light_word == "dusk"
                else "Catfish are still feeding after the night. Fish a nightcrawler on the bottom.",
            ),
            Rule(
                lambda c: c.wet or c.overcast,
                "Stinkbait",
                "Clouds and rain put catfish on the move, and a strong-smelling bait helps them find it.",
            ),
            Rule(
                lambda c: c.choppy,
                "Shrimp (stays on the hook well)",
                "Casting in wind tears soft baits off. Shrimp stays on the hook.",
            ),
        ),
        bait_fallback=(
            ("Chicken liver", "A classic catfish bait. Fish it on the bottom."),
            ("Nightcrawlers", "Works almost anywhere catfish live."),
        ),
        lure_note="Catfish are caught on bait. No lure needed.",
    ),
    "Blue Catfish": Tackle(
        baits=(
            Rule(
                lambda c: c.choppy,
                "Fresh cut shad (fresh beats frozen)",
                "Wind pushes shad onto the windblown bank. Fish cut shad on the bottom there.",
            ),
        ),
        bait_fallback=(
            ("Fresh cut shad (fresh beats frozen)", "Blue cats hunt by smell. Fresh cut shad on the bottom is the standard."),
            ("Live shad", "For a bigger fish, fish a live shad near drop-offs."),
        ),
        lure_note="Blue catfish are caught on bait. No lure needed.",
    ),
    "White Crappie": Tackle(
        lures=(
            Rule(
                lambda c: c.low_light,
                "Small poppers at dawn or dusk",
                lambda c: f"At {c.light_word} crappie rise to feed. A small popper can draw strikes on top.",
            ),
            Rule(lambda c: c.choppy or c.overcast, "Beetle-spins", "A little flash helps in choppy or cloudy water. Retrieve slowly."),
            Rule(
                lambda c: c.bright,
                "Small soft-plastic jigs",
                "Bright sun pushes crappie into shade. Drop a small jig next to docks and brush.",
            ),
        ),
        lure_fallback=(
            ("Small soft-plastic jigs", "Fish it slowly near brush piles, docks and bridge pilings."),
            ("Beetle-spins", "Covers water to find a school."),
        ),
        bait_fallback=(("1½–2½ in minnows (the preferred bait)", "A minnow under a bobber near cover. Crappie's favorite meal."),),
    ),
    "Black Crappie": Tackle(
        lures=(
            Rule(lambda c: c.choppy or c.overcast, "Beetle-spins", "A little flash helps in choppy or cloudy water. Retrieve slowly."),
            Rule(
                lambda c: c.bright,
                "Small soft-plastic jigs",
                "Bright sun pushes crappie into shade. Drop a small jig next to docks and brush.",
            ),
        ),
        lure_fallback=(
            ("Small soft-plastic jigs", "Fish it slowly near brush piles, docks and bridge pilings."),
            ("Small jigging spoons", "Jig it straight down over brush."),
        ),
        bait_fallback=(("1½–2½ in minnows", "A minnow under a bobber near cover. Crappie's favorite meal."),),
    ),
    "Bluegill": Tackle(
        lures=(
            Rule(
                lambda c: c.low_light,
                "Small poppers",
                lambda c: f"Bluegill feed at the surface at {c.light_word}. A small popper is fun and effective.",
            ),
            Rule(lambda c: c.choppy or c.overcast, "Tiny spinners", "A bit of flash gets noticed in choppy or cloudy water."),
        ),
        lure_fallback=(
            ("Tiny jigs, 1/32 oz and smaller (black works well)", "Fish it slowly near weeds and docks."),
            ("Tiny spinners", "Retrieve slowly along the bank."),
        ),
        baits=(
            Rule(
                lambda c: c.bright,
                "Crickets",
                "On bright days bluegill hang in shade by docks and brush. Fish a cricket under a bobber there.",
            ),
        ),
        bait_fallback=((BLUEGILL_WORM, "The easiest bite in the lake. Fish it under a bobber near the bank."),),
    ),
}


def _display(name: str) -> str:
    return name.rstrip(".")


def _why(rule_why: Why, c: Conditions) -> str:
    return rule_why(c) if callable(rule_why) else rule_why


def _choose(rules: tuple[Rule, ...], fallback: tuple[tuple[str, str], ...], c: Conditions | None, n: int) -> list[dict]:
    picks: list[dict] = []
    seen: set[str] = set()
    if c is not None:
        for rule in rules:
            if len(picks) >= n:
                break
            if rule.pick in seen or not rule.when(c):
                continue
            picks.append({"name": _display(rule.pick), "why": _why(rule.why, c)})
            seen.add(rule.pick)
    for name, why in fallback:
        if len(picks) >= n:
            break
        if name not in seen:
            picks.append({"name": _display(name), "why": why})
            seen.add(name)
    return picks


def tackle_for(guide: SpeciesGuide, c: Conditions | None) -> dict:
    tackle = TACKLE.get(guide.common_name)
    if tackle is None:
        # A guide without rules yet: its own first lure and bait, said plainly.
        return {
            "lures": [{"name": _display(n), "why": "A standard choice for this fish."} for n in guide.lures[:LURE_PICKS]],
            "baits": [{"name": _display(n), "why": "A standard bait for this fish."} for n in guide.live_baits[:BAIT_PICKS]],
            "lure_note": None,
        }
    bait_n = BAIT_PICKS if (tackle.lures or tackle.lure_fallback) else 2
    return {
        "lures": _choose(tackle.lures, tackle.lure_fallback, c, LURE_PICKS),
        "baits": _choose(tackle.baits, tackle.bait_fallback, c, bait_n),
        "lure_note": tackle.lure_note,
    }


# --- heads-up ---------------------------------------------------------------


def heads_up(c: Conditions) -> list[str]:
    notes: list[str] = []
    if c.sky == "thunder":
        notes.append("Thunderstorms in the forecast. Get off the water at the first rumble of thunder.")
    if c.too_windy:
        notes.append(f"Wind up to {c.wind_mph:.0f} mph: hard to cast, and risky in a small boat.")
    if c.front:
        notes.append(
            f"The temperature drops {c.front_drop_f:.0f}°F in the next day as a front moves in. "
            "Fish often feed before it, so sooner is better."
        )
    if c.sky != "thunder" and (c.rain_chance or 0) >= RAIN_LIKELY:
        notes.append(f"Rain likely during this window ({c.rain_chance}% chance).")
    return notes


# --- the plan ---------------------------------------------------------------


def _pick_window(windows: list[TimeWindow]) -> tuple[TimeWindow | None, TimeWindow | None]:
    """The window to plan around, and the other one. A clearly better window
    wins (same 0.03 margin the UI used for "Better bet"); otherwise the
    sooner one, which is the one a person can still make."""
    if not windows:
        return None, None
    if len(windows) == 1:
        return windows[0], None
    a, b = windows[0], windows[1]
    if a.score is not None and b.score is not None and abs(a.score - b.score) >= 0.03:
        best = a if a.score > b.score else b
    else:
        best = a
    return best, (b if best is a else a)


def _window_out(w: TimeWindow | None) -> dict | None:
    if w is None:
        return None
    return {"start_time": w.start_time, "end_time": w.end_time, "label": w.label}


def _conditions_line(c: Conditions) -> str:
    parts = []
    if c.temperature is not None:
        parts.append(f"{c.temperature:.0f}°F")
    if c.forecast_text:
        parts.append(c.forecast_text.lower())
    if c.wind_text:
        parts.append(f"{c.wind_from + ' ' if c.wind_from else ''}wind {c.wind_text}")
    return ", ".join(parts)


def build_plan(
    snapshot: WeatherSnapshot,
    species: str | None,
    species_options: list[str],
    species_on_record: bool | None,
) -> dict:
    """The lake page's plan. `species` must already be resolved (or None,
    when there's no fish to plan for yet)."""
    windows = scoring.bite_windows(snapshot)
    chosen, other = _pick_window(windows)
    c = conditions_for(snapshot, chosen) if chosen is not None else None

    guide = get_guide(species) if species else None
    tackle = tackle_for(guide, c) if guide is not None else {"lures": [], "baits": [], "lure_note": None}

    return {
        "species": guide.common_name if guide else None,
        # The fish's guide page (/fish/<slug>): how to rig and fish each pick.
        "species_slug": slugify(guide.common_name) if guide else None,
        "species_options": species_options,
        "species_on_record": species_on_record if guide else None,
        "where": where_to_fish(c) if c is not None else None,
        "when": _window_out(chosen),
        "also": _window_out(other),
        "conditions": _conditions_line(c) if c is not None else None,
        "lures": tackle["lures"],
        "baits": tackle["baits"],
        "lure_note": tackle["lure_note"],
        "heads_up": heads_up(c) if c is not None else [],
    }


def sport_species_with_guides() -> list[str]:
    return [g.common_name for g in GUIDES if g.role == "sport"]
