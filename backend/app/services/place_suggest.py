"""Place names as you type ("aus" -> Austin, TX), from FishEye's own list of
US places: app/data/us_places.tsv.gz, built by app/cli/us_places.py from
Census Bureau files (public domain). Nothing outside is asked, so a
suggestion can follow every keystroke for any number of people, and a chosen
one carries its own point and needs no geocoding. Nominatim
(services/geocoding.py, one request a second for the whole app, and no
suggestions as you type under its policy) is left for what the list
doesn't have: a street address or a landmark.

How a name is found:
- by its start ("aus" -> Austin) or a later word's start ("fran" -> San
  Francisco), ignoring case, accents and punctuation, with Saint/St.,
  Mount/Mt. and Fort/Ft. read alike;
- digits look up ZIP codes ("787" -> 78701, near Austin, TX);
- `state` keeps one state's names only (the search box reads "austin, tx").

How they're ordered: a match at the name's start before one at a later
word, then by population, lifted for the state the map is in and for names
near where it's looking, so the nearest of the country's Springfields leads.
"""
from __future__ import annotations

import bisect
import gzip
import math
import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "us_places.tsv.gz"
KINDS = {"p": "place", "c": "county", "t": "town", "z": "zip"}
MIN_LETTERS = 2
ZIP_MIN_DIGITS = 3
# Score lifts (population counts log10, so 0 to about 7).
AT_START = 3.0  # "aus" starts "Austin", not only a later word of the name
WHOLE_NAME = 1.0  # the whole name typed
SAME_STATE = 2.5  # the state the map is in
NEAR_KM = 300.0  # within this, a lift that grows to NEAR_LIFT at the point
NEAR_LIFT = 2.0
COUNTY = -1.0  # "st lou" is St. Louis before St. Louis County, three times its size


@dataclass(frozen=True, slots=True)
class Place:
    kind: str  # place, county, town (New England) or zip
    name: str
    state: str
    latitude: float
    longitude: float
    population: int
    near: str = ""  # a ZIP code's nearest place

    @property
    def label(self) -> str:
        if self.kind == "zip":
            return f"{self.name} ({self.near}, {self.state})" if self.near else f"{self.name}, {self.state}"
        return f"{self.name}, {self.state}"


_SHORT = [(re.compile(r"\bsaint\b"), "st"), (re.compile(r"\bmount\b"), "mt"), (re.compile(r"\bfort\b"), "ft")]


def plain(text: str) -> str:
    """Lower case, no accents or punctuation, single spaces."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def shortened(text: str) -> str:
    """Saint, Mount and Fort as St, Mt and Ft (whole words only)."""
    for pattern, short in _SHORT:
        text = pattern.sub(short, text)
    return text


def km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a_lat, a_lon, b_lat, b_lon))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


class PlaceIndex:
    def __init__(self, places: list[Place]) -> None:
        self.places = places
        keys: set[tuple[str, int, bool]] = set()
        zips: list[tuple[str, int]] = []
        for i, p in enumerate(places):
            if p.kind == "zip":
                zips.append((p.name, i))
                continue
            for form in {plain(p.name), shortened(plain(p.name))}:
                words = form.split()
                for start in range(len(words)):
                    keys.add((" ".join(words[start:]), i, start == 0))
        entries = sorted(keys)
        self._keys = [k for k, _, _ in entries]
        self._entries = entries
        zips.sort()
        self._zips = [z for z, _ in zips]
        self._zip_rows = [i for _, i in zips]

    @classmethod
    def load(cls, path: Path = DATA) -> PlaceIndex:
        places = []
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                kind, name, state, lat, lon, pop, near = line.rstrip("\n").split("\t")
                places.append(Place(KINDS[kind], name, state, float(lat), float(lon), int(pop), near))
        return cls(places)

    def suggest(
        self,
        typed: str,
        *,
        state: str | None = None,
        prefer_state: str | None = None,
        near: tuple[float, float] | None = None,
        limit: int = 6,
    ) -> list[Place]:
        text = plain(typed)
        state = state.upper() if state else None
        if text.isdigit():
            return self._zip_codes(text, state, limit) if len(text) >= ZIP_MIN_DIGITS else []
        if len(text.replace(" ", "")) < MIN_LETTERS:
            return []
        best: dict[int, float] = {}
        for query in {text, shortened(text)}:
            lo = bisect.bisect_left(self._keys, query)
            hi = bisect.bisect_left(self._keys, query + "\x7f")
            for key, i, at_start in self._entries[lo:hi]:
                p = self.places[i]
                if state and p.state != state:
                    continue
                score = math.log10(p.population + 1)
                if at_start:
                    score += AT_START + (WHOLE_NAME if key == query else 0.0)
                if prefer_state and p.state == prefer_state:
                    score += SAME_STATE
                if near:
                    score += NEAR_LIFT * max(0.0, 1 - km(near[0], near[1], p.latitude, p.longitude) / NEAR_KM)
                if p.kind == "county":
                    score += COUNTY
                if score > best.get(i, -1e9):
                    best[i] = score
        ranked = sorted(best, key=lambda i: (-best[i], self.places[i].name, self.places[i].state))
        out, seen = [], set()
        for i in ranked:
            label = self.places[i].label
            if label not in seen:
                seen.add(label)
                out.append(self.places[i])
            if len(out) == limit:
                break
        return out

    def _zip_codes(self, digits: str, state: str | None, limit: int) -> list[Place]:
        lo = bisect.bisect_left(self._zips, digits)
        hi = bisect.bisect_left(self._zips, digits + "a")
        found = [self.places[i] for i in self._zip_rows[lo:hi]]
        if state:
            found = [p for p in found if p.state == state]
        # A whole ZIP code typed is the one meant; a start, the most lived-in first.
        found.sort(key=lambda p: (p.name != digits, -p.population, p.name))
        return found[:limit]


_index: PlaceIndex | None = None
_lock = threading.Lock()


def index() -> PlaceIndex:
    global _index
    if _index is None:
        with _lock:
            if _index is None:
                _index = PlaceIndex.load()
    return _index


def suggest(typed: str, **kwargs) -> list[Place]:
    return index().suggest(typed, **kwargs)
