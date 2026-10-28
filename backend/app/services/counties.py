"""Which US county a point is in, from the Census outlines in
app/data/us_counties.json.gz (built by app.data_import.census_counties).

Catches are browsed by state, then county, then lake; a catch's county is
looked up once, when it is saved. Outlines are simplified to ~100 m, so a
pin right on a county line may land in the neighbour: fine for browsing.
"""
from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

COUNTIES_FILE = Path(__file__).resolve().parents[1] / "data" / "us_counties.json.gz"
CELL = 1.0  # degrees: the grid the outlines are indexed on


@dataclass(frozen=True)
class County:
    geoid: str  # 5-digit FIPS, e.g. "48201"
    name: str  # "Harris County", "Orleans Parish"
    state: str  # "TX"
    rings: tuple[tuple[tuple[float, float], ...], ...]
    bbox: tuple[float, float, float, float]  # west, south, east, north


class CountyIndex:
    def __init__(self, counties: list[County]) -> None:
        self.by_geoid = {c.geoid: c for c in counties}
        self._grid: dict[tuple[int, int], list[County]] = {}
        for c in counties:
            w, s, e, n = c.bbox
            for gx in range(math.floor(w / CELL), math.floor(e / CELL) + 1):
                for gy in range(math.floor(s / CELL), math.floor(n / CELL) + 1):
                    self._grid.setdefault((gx, gy), []).append(c)

    def at(self, lat: float, lng: float) -> County | None:
        for c in self._grid.get((math.floor(lng / CELL), math.floor(lat / CELL)), ()):
            w, s, e, n = c.bbox
            if w <= lng <= e and s <= lat <= n and _inside(c.rings, lng, lat):
                return c
        return None


def _inside(rings, x: float, y: float) -> bool:
    inside = False
    for ring in rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def load(path: Path = COUNTIES_FILE) -> CountyIndex:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        raw = json.load(f)["counties"]
    counties = []
    for c in raw:
        rings = tuple(tuple((x, y) for x, y in r) for r in c["rings"])
        xs = [p[0] for r in rings for p in r]
        ys = [p[1] for r in rings for p in r]
        counties.append(County(c["geoid"], c["name"], c["state"], rings, (min(xs), min(ys), max(xs), max(ys))))
    return CountyIndex(counties)


@lru_cache(maxsize=1)
def index() -> CountyIndex | None:
    """The outlines, loaded on first use; None when the file is missing
    (catches then just have no county)."""
    if not COUNTIES_FILE.exists():
        return None
    return load()


def county_at(lat: float, lng: float) -> County | None:
    idx = index()
    return idx.at(lat, lng) if idx else None


def county_name(geoid: str | None) -> str | None:
    idx = index()
    c = idx.by_geoid.get(geoid) if idx and geoid else None
    return c.name if c else None
