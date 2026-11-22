"""US place names for the search box's suggestions (services/place_suggest.py).

    python -m app.cli.us_places            # reads census_cache/, writes app/data/us_places.tsv.gz

Every Census place (city, town, village, borough and census-designated place),
county, New England town and ZIP code (ZCTA) in the 50 states and DC, with
its internal point and population, so a suggestion carries its own point and
needs no geocoder. All from the U.S. Census Bureau, public domain
(docs/data-sources.md, "Place names for the search box"):

- 2025 Gazetteer files: names and internal points
  (https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/,
  the four *_national.zip files below, downloaded into census_cache/);
- ACS 2020-2024 5-year estimates, table B01003 (total population), only to
  rank names typed alike: census_cache/acsdt5y2024-b01003.dat from
  https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/.

Each line of the output: kind, name, state, latitude, longitude, population,
and for a ZIP code the nearest place's name. Kinds: p place, c county,
t New England town, z ZIP code.
"""
from __future__ import annotations

import gzip
import math
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CACHE = Path("census_cache")
OUT = Path("app/data/us_places.tsv.gz")
PLACES = "2025_Gaz_place_national.zip"
COUNTIES = "2025_Gaz_counties_national.zip"
TOWNS = "2025_Gaz_cousubs_national.zip"
ZIPS = "2025_Gaz_zcta_national.zip"
POPULATION = "acsdt5y2024-b01003.dat"

# Puerto Rico and the island areas: FishEye covers the 50 states and DC.
NOT_COVERED = {"PR", "GU", "VI", "AS", "MP", "UM"}
# New England's towns are what people there name; elsewhere the places cover it.
NEW_ENGLAND = {"CT", "ME", "MA", "NH", "RI", "VT"}
# Fictitious, inactive or nonfunctioning entities aren't places anyone looks for.
LIVE = {"A", "S", "B", "C"}
# A consolidated government's Census name, and the name people use for it.
CALLED = {
    ("Nashville-Davidson", "TN"): "Nashville",
    ("Louisville/Jefferson County", "KY"): "Louisville",
    ("Lexington-Fayette", "KY"): "Lexington",
    ("Athens-Clarke County", "GA"): "Athens",
    ("Augusta-Richmond County", "GA"): "Augusta",
    ("Macon-Bibb County", "GA"): "Macon",
    ("Urban Honolulu", "HI"): "Honolulu",
    ("Butte-Silver Bow", "MT"): "Butte",
    ("Anaconda-Deer Lodge County", "MT"): "Anaconda",
    ("Hartsville/Trousdale County", "TN"): "Hartsville",
}
# A town this close to a place of the same name is that place.
SAME_PLACE_KM = 10.0
# A ZIP code is named for the biggest place this close to its middle.
TOWN_KM = 15.0


@dataclass(frozen=True)
class Row:
    kind: str
    name: str
    state: str
    latitude: float
    longitude: float
    population: int
    near: str = ""


def plain_name(census_name: str) -> str:
    """ "Boise City city" -> "Boise City", "Nashville-Davidson metropolitan
    government (balance)" -> "Nashville-Davidson": the Census adds the kind
    of place, in lower case, after the name."""
    words = census_name.split()
    while len(words) > 1 and (words[-1].islower() or words[-1] == "CDP" or words[-1].startswith("(")):
        words.pop()
    return " ".join(words)


def gazetteer(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as z:
        text = z.read(z.namelist()[0]).decode("utf-8")
    lines = text.splitlines()
    head = [c.strip() for c in lines[0].split("|")]
    return [dict(zip(head, (c.strip() for c in line.split("|")))) for line in lines[1:] if line.strip()]


def populations(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    with open(path, encoding="utf-8") as f:
        next(f)
        for line in f:
            geo, estimate, _ = line.rstrip("\n").split("|", 2)
            if estimate.lstrip("-").isdigit() and int(estimate) >= 0:
                out[geo] = int(estimate)
    return out


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


class Grid:
    """Rows bucketed by whole degrees, for the nearest place to a point."""

    def __init__(self, rows: list[Row]) -> None:
        self.cells: dict[tuple[int, int], list[Row]] = defaultdict(list)
        for r in rows:
            self.cells[(math.floor(r.latitude), math.floor(r.longitude))].append(r)

    def named(self, lat: float, lon: float) -> Row | None:
        """The place a ZIP code goes by: the biggest within TOWN_KM (78745 is
        south Austin, not the small city of Sunset Valley next to its middle),
        or else the nearest."""
        close = [
            r
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            for r in self.cells.get((math.floor(lat) + dy, math.floor(lon) + dx), ())
            if km((lat, lon), (r.latitude, r.longitude)) <= TOWN_KM
        ]
        return max(close, key=lambda r: r.population) if close else self.nearest(lat, lon)

    def nearest(self, lat: float, lon: float) -> Row | None:
        best, best_km = None, float("inf")
        for reach in (1, 2, 4):
            for dy in range(-reach, reach + 1):
                for dx in range(-reach, reach + 1):
                    for r in self.cells.get((math.floor(lat) + dy, math.floor(lon) + dx), ()):
                        d = km((lat, lon), (r.latitude, r.longitude))
                        if d < best_km:
                            best, best_km = r, d
            if best is not None:
                return best
        return best


def build(cache: Path = CACHE) -> list[Row]:
    pop = populations(cache / POPULATION)
    rows: list[Row] = []
    for r in gazetteer(cache / PLACES):
        # A consolidated city's "(balance)" is marked fictitious (F), but it is
        # Indianapolis, Nashville or Louisville to anyone searching.
        if r["USPS"] in NOT_COVERED or (r["FUNCSTAT"] not in LIVE and not r["NAME"].endswith("(balance)")):
            continue
        name = plain_name(r["NAME"])
        name = CALLED.get((name, r["USPS"]), name)
        rows.append(Row("p", name, r["USPS"], float(r["INTPTLAT"]), float(r["INTPTLONG"]), pop.get(r["GEOIDFQ"], 0)))
    places = list(rows)
    by_name: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for p in places:
        by_name[(p.name.lower(), p.state)].append(p)
    for r in gazetteer(cache / COUNTIES):
        name = r["NAME"]
        # Independent cities (Richmond city, Baltimore city) and DC are places already.
        if r["USPS"] in NOT_COVERED or r["USPS"] == "DC" or name.endswith(" city"):
            continue
        rows.append(Row("c", name, r["USPS"], float(r["INTPTLAT"]), float(r["INTPTLONG"]), pop.get(r["GEOIDFQ"], 0)))
    for r in gazetteer(cache / TOWNS):
        if r["USPS"] not in NEW_ENGLAND or r["FUNCSTAT"] != "A":
            continue
        name = plain_name(r["NAME"])
        point = (float(r["INTPTLAT"]), float(r["INTPTLONG"]))
        if any(km(point, (p.latitude, p.longitude)) <= SAME_PLACE_KM for p in by_name.get((name.lower(), r["USPS"]), ())):
            continue
        rows.append(Row("t", name, r["USPS"], *point, pop.get(r["GEOIDFQ"], 0)))
    grid = Grid(places)
    for r in gazetteer(cache / ZIPS):
        lat, lon = float(r["INTPTLAT"]), float(r["INTPTLONG"])
        near = grid.named(lat, lon)
        if near is None or near.state in NOT_COVERED or r["GEOID"][:3] in {"006", "007", "008", "009"}:
            continue
        rows.append(Row("z", r["GEOID"], near.state, lat, lon, pop.get(r["GEOIDFQ"], 0), near.name))
    return rows


def write(rows: list[Row], out: Path = OUT) -> None:
    lines = [
        f"{r.kind}\t{r.name}\t{r.state}\t{r.latitude:.4f}\t{r.longitude:.4f}\t{r.population}\t{r.near}"
        for r in sorted(rows, key=lambda r: (r.kind, r.state, r.name))
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0: the same rows give the same bytes, so a rebuild with no change shows no diff.
    with gzip.GzipFile(out, "wb", mtime=0) as f:
        f.write(("\n".join(lines) + "\n").encode("utf-8"))


def main() -> None:
    rows = build()
    write(rows)
    kinds = defaultdict(int)
    for r in rows:
        kinds[r.kind] += 1
    print(f"wrote {OUT}: {len(rows)} names ({kinds['p']} places, {kinds['c']} counties, "
          f"{kinds['t']} New England towns, {kinds['z']} ZIP codes), {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
