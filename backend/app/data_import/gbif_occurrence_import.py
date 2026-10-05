"""Species records from GBIF, the "reported" tier (docs/adr/0012-gbif-reported-species.md).

The statewide OSM layer (ADR 0010) knows a lake exists but nothing about its
fish. GBIF aggregates museum specimens, agency surveys (including Fishes of
Texas and TPWD) and iNaturalist research-grade observations. This importer
attaches those records to lakes, so a lake's panel can say "Largemouth Bass:
37 records, most recent 2023, from Fishes of Texas and iNaturalist".

The measurement that justified doing this is in
docs/experiments/2026-09-24-gbif-texas-coverage.md.

WHAT IT WRITES
--------------
One SpeciesOccurrence row per GBIF record inside a lake. Never a
WaterbodySpecies row: a record says a fish was recorded here once, not that
an official survey confirms it, and scoring and the AI advisor only read
confirmed species.

HOW A RECORD IS MATCHED TO A LAKE
---------------------------------
- Coordinates must be precise to MAX_UNCERTAINTY_M; fossils are dropped.
- A record goes to the smallest OSM lake bounding box containing it. A box
  is larger than the water, so shoreline and inflowing-creek records can
  count. The UI says so. Matching to real lake outlines needs the polygons,
  which the OSM import doesn't keep yet.
- An OSM element that is one of our verified lakes (the importer's own twin
  rule) credits that verified lake, so TPWD lakes get their records too.

Re-running replaces every GBIF record for the state: records GBIF has since
removed or re-located disappear, nothing is duplicated.

Run from backend/, after the OSM import, on a machine that can reach
api.gbif.org. The experiment's download can be reused as-is:

    python -m app.data_import.gbif_occurrence_import --osm tx_osm.json --from-file gbif_tx_raw.json
    python -m app.data_import.gbif_occurrence_import --osm tx_osm.json --save-raw gbif_tx_raw.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.data_import.osm_waterbody_import import (
    OsmLake,
    _find_verified_twin,
    parse_elements,
)
from app.db.session import Base, SessionLocal, engine
from app.knowledge.species_guides import GUIDES
from app.models.waterbody import SpeciesOccurrence, State, Waterbody

GBIF_API = "https://api.gbif.org/v1"
# Generous boxes around each state. Records outside the state proper are
# harmless: they only count if they fall inside one of its lakes.
STATE_BOUNDS: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "TX": ((25.8, 36.6), (-106.7, -93.5)),
}
PAGE_SIZE = 300
# GBIF documents a 100,000-record paging depth, but users report errors past
# 10,000. Every query window is split until it holds fewer than this.
MAX_WINDOW = 9_000
MAX_UNCERTAINTY_M = 1_000
REQUEST_DELAY_S = 0.25

# Names GBIF may file a species under besides the guide's scientific name.
# Largemouth bass taxonomy is in flux (Florida bass, M. nigricans).
EXTRA_NAMES: dict[str, list[str]] = {
    "Largemouth Bass": ["Micropterus nigricans", "Micropterus floridanus"],
}


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------


def _get_json(client: httpx.Client, path: str, params: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(4):
        resp = client.get(f"{GBIF_API}{path}", params=params)
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            time.sleep(2**attempt)
            continue
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY_S)
        data: dict[str, Any] = resp.json()
        return data
    raise RuntimeError("unreachable")


def resolve_taxon_keys(client: httpx.Client) -> dict[str, list[int]]:
    """Common name -> GBIF taxon keys. A synonym resolves to its accepted
    key, so records filed under either name are found."""
    keys: dict[str, list[int]] = {}
    for guide in GUIDES:
        names = [guide.scientific_name, *EXTRA_NAMES.get(guide.common_name, [])]
        found: list[int] = []
        for name in names:
            if "×" in name:  # hybrids aren't a GBIF species; recorded under a parent at best
                continue
            m = _get_json(client, "/species/match", {"name": name, "strict": "true"})
            key = m.get("acceptedUsageKey") or m.get("usageKey")
            if key and m.get("matchType") in {"EXACT", "FUZZY"} and m.get("rank") == "SPECIES":
                if key not in found:
                    found.append(int(key))
        keys[guide.common_name] = found
    return keys


@dataclass(frozen=True)
class Window:
    lat: tuple[float, float]
    lng: tuple[float, float]
    year: tuple[int, int]

    def params(self) -> dict[str, str]:
        return {
            "decimalLatitude": f"{self.lat[0]},{self.lat[1]}",
            "decimalLongitude": f"{self.lng[0]},{self.lng[1]}",
            "year": f"{self.year[0]},{self.year[1]}",
        }

    def split(self) -> tuple[Window, Window]:
        y0, y1 = self.year
        if y1 > y0:
            mid = (y0 + y1) // 2
            return Window(self.lat, self.lng, (y0, mid)), Window(self.lat, self.lng, (mid + 1, y1))
        a, b = self.lat
        mid_lat = (a + b) / 2
        return Window((a, mid_lat), self.lng, self.year), Window((mid_lat, b), self.lng, self.year)


BASE_FILTERS = {
    "country": "US",
    "hasCoordinate": "true",
    "hasGeospatialIssue": "false",
    "occurrenceStatus": "PRESENT",
}


def _fetch_window(client: httpx.Client, taxon_key: int, window: Window, depth: int = 0) -> list[dict[str, Any]]:
    params = {**BASE_FILTERS, "taxonKey": taxon_key, **window.params()}
    count = int(_get_json(client, "/occurrence/search", {**params, "limit": 0})["count"])
    if count == 0:
        return []
    if count > MAX_WINDOW and depth < 30:
        a, b = window.split()
        # GBIF ranges include both ends, so a record exactly on a latitude
        # split line comes back from both halves: keep one copy.
        merged: dict[Any, dict[str, Any]] = {}
        for r in _fetch_window(client, taxon_key, a, depth + 1) + _fetch_window(client, taxon_key, b, depth + 1):
            merged.setdefault(r.get("key"), r)
        return list(merged.values())
    out: list[dict[str, Any]] = []
    offset = 0
    while offset < count:
        page = _get_json(client, "/occurrence/search", {**params, "limit": PAGE_SIZE, "offset": offset})
        out.extend(page.get("results", []))
        if page.get("endOfRecords"):
            break
        offset += PAGE_SIZE
    return out


KEEP_FIELDS = (
    "key",
    "decimalLatitude",
    "decimalLongitude",
    "coordinateUncertaintyInMeters",
    "year",
    "basisOfRecord",
    "license",
    "datasetName",
    "institutionCode",
)


def fetch_all(
    client: httpx.Client, taxon_keys: dict[str, list[int]], state_code: str = "TX"
) -> list[dict[str, Any]]:
    lat, lng = STATE_BOUNDS[state_code]
    records: list[dict[str, Any]] = []
    seen: set[int] = set()
    full = Window(lat, lng, (1800, 2030))
    for common_name, keys in taxon_keys.items():
        for key in keys:
            raw = _fetch_window(client, key, full)
            print(f"  {common_name} (taxon {key}): {len(raw)} records")
            for r in raw:
                if r.get("key") in seen:
                    continue
                seen.add(r["key"])
                records.append({**{f: r.get(f) for f in KEEP_FIELDS}, "species": common_name})
    return records


# --------------------------------------------------------------------------
# Matching (pure)
# --------------------------------------------------------------------------

CELL_DEG = 0.1


class LakeIndex:
    """Grid index over lake bounding boxes; point -> smallest containing lake."""

    def __init__(self, lakes: list[OsmLake]) -> None:
        self.lakes = lakes
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        for i, lake in enumerate(lakes):
            b = lake.bounds
            for cy in range(math.floor(b.south / CELL_DEG), math.floor(b.north / CELL_DEG) + 1):
                for cx in range(math.floor(b.west / CELL_DEG), math.floor(b.east / CELL_DEG) + 1):
                    self.cells[(cy, cx)].append(i)

    def lookup(self, lat: float, lng: float) -> OsmLake | None:
        cell = (math.floor(lat / CELL_DEG), math.floor(lng / CELL_DEG))
        hits = [self.lakes[i] for i in self.cells.get(cell, []) if self.lakes[i].bounds.contains(lat, lng)]
        if not hits:
            return None
        return min(hits, key=lambda lake: lake.bounds.area())


def usable(record: dict[str, Any]) -> bool:
    u = record.get("coordinateUncertaintyInMeters")
    return u is None or float(u) <= MAX_UNCERTAINTY_M


def license_family(url: str | None) -> str:
    u = (url or "").lower()
    if "publicdomain/zero" in u or "cc0" in u:
        return "CC0"
    if "by-nc" in u:
        return "CC BY-NC"
    if "/by/" in u or "cc_by_4" in u or u.endswith("by/4.0/legalcode"):
        return "CC BY"
    return "other/unknown"


def source_group(record: dict[str, Any]) -> str:
    """Who collected the record, in the four groups the UI shows. Checked
    against every institution/dataset pair in the Texas download."""
    dataset = (record.get("datasetName") or "").lower()
    institution = (record.get("institutionCode") or "").lower()
    if "fishes of texas" in dataset:
        return "fishes_of_texas"
    if institution == "inaturalist" or "inaturalist" in dataset:
        return "inaturalist"
    if institution == "tpwd":
        return "tpwd"
    return "other"


GUIDE_NAMES = frozenset(g.common_name for g in GUIDES)


@dataclass
class MatchSummary:
    records_read: int = 0
    duplicates: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    matched: int = 0
    lakes_with_records: int = 0
    by_license: dict[str, int] = field(default_factory=dict)


def match_records(
    lakes: list[OsmLake],
    records: list[dict[str, Any]],
    target_for: dict[str, int],  # osm_ref -> waterbody id
) -> tuple[list[tuple[int, dict[str, Any]]], MatchSummary]:
    """(waterbody_id, record) pairs, plus what was dropped and why."""
    summary = MatchSummary(records_read=len(records))
    skipped: Counter[str] = Counter()
    index = LakeIndex(lakes)
    seen: set[Any] = set()
    out: list[tuple[int, dict[str, Any]]] = []
    for r in records:
        if r.get("key") in seen:
            summary.duplicates += 1
            continue
        seen.add(r.get("key"))
        if r.get("species") not in GUIDE_NAMES:
            skipped["not a guide species"] += 1
            continue
        if r.get("basisOfRecord") == "FOSSIL_SPECIMEN":
            skipped["fossil"] += 1
            continue
        if r.get("decimalLatitude") is None or r.get("decimalLongitude") is None:
            skipped["no coordinates"] += 1
            continue
        if not usable(r):
            skipped["coordinates imprecise"] += 1
            continue
        lake = index.lookup(float(r["decimalLatitude"]), float(r["decimalLongitude"]))
        if lake is None:
            skipped["not in any lake"] += 1
            continue
        wb_id = target_for.get(lake.osm_ref)
        if wb_id is None:
            skipped["lake not in database"] += 1
            continue
        out.append((wb_id, r))
    summary.skipped = dict(skipped)
    summary.matched = len(out)
    summary.lakes_with_records = len({wb_id for wb_id, _ in out})
    summary.by_license = dict(Counter(license_family(r.get("license")) for _, r in out).most_common())
    return out, summary


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------


def lake_targets(db: Session, state: State, lakes: list[OsmLake]) -> dict[str, int]:
    """Which waterbody each OSM element stands for. Usually the row the OSM
    import created for it; for an element that is one of our verified lakes,
    that verified lake, even when it's a second element of the same lake
    (OSM often maps a reservoir as a way plus a relation, or by its arms)."""
    by_ref = {
        wb.osm_ref: wb.id
        for wb in db.scalars(
            select(Waterbody).where(Waterbody.state_id == state.id, Waterbody.osm_ref.is_not(None))
        )
        if wb.osm_ref is not None
    }
    verified = list(
        db.scalars(select(Waterbody).where(Waterbody.state_id == state.id, Waterbody.data_tier == "verified"))
    )
    targets: dict[str, int] = {}
    for lake in lakes:
        if lake.osm_ref in by_ref:
            targets[lake.osm_ref] = by_ref[lake.osm_ref]
            continue
        twin = _find_verified_twin(lake, verified)
        if twin is not None:
            targets[lake.osm_ref] = twin.id
    return targets


def replace_occurrences(
    db: Session,
    state: State,
    matched: list[tuple[int, dict[str, Any]]],
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(timezone.utc)
    state_lakes = select(Waterbody.id).where(Waterbody.state_id == state.id)
    db.execute(
        delete(SpeciesOccurrence).where(
            SpeciesOccurrence.source == "gbif", SpeciesOccurrence.waterbody_id.in_(state_lakes)
        )
    )
    rows = [
        {
            "waterbody_id": wb_id,
            "species_name": r["species"],
            "source": "gbif",
            "source_record_id": str(r["key"]),
            "year": int(r["year"]) if r.get("year") is not None else None,
            "basis_of_record": r.get("basisOfRecord"),
            "source_group": source_group(r),
            "dataset_name": (r.get("datasetName") or None) and str(r["datasetName"])[:256],
            "institution_code": (r.get("institutionCode") or None) and str(r["institutionCode"])[:128],
            "license": license_family(r.get("license")),
            "latitude": float(r["decimalLatitude"]),
            "longitude": float(r["decimalLongitude"]),
            "imported_at": now,
        }
        for wb_id, r in matched
    ]
    if rows:
        db.execute(insert(SpeciesOccurrence), rows)
    db.flush()


def run(db: Session, state_code: str, osm_payload: dict[str, Any], records: list[dict[str, Any]]) -> MatchSummary:
    state = db.scalar(select(State).where(State.code == state_code.upper()))
    if state is None:
        raise ValueError(f"no {state_code} lakes in the database; run the OSM import first")
    lakes, _, _ = parse_elements(osm_payload)
    targets = lake_targets(db, state, lakes)
    matched, summary = match_records(lakes, records, targets)
    replace_occurrences(db, state, matched)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", default="TX")
    parser.add_argument("--osm", type=Path, required=True, help="the Overpass file the OSM import used (--save-raw)")
    parser.add_argument("--from-file", type=Path, help="reuse GBIF records saved by --save-raw")
    parser.add_argument("--save-raw", type=Path, help="save fetched GBIF records here")
    args = parser.parse_args(argv)

    code = args.state.upper()
    if code not in STATE_BOUNDS:
        print(f"unsupported state {code!r}; add it to STATE_BOUNDS first", file=sys.stderr)
        return 2

    osm_payload = json.loads(args.osm.read_text(encoding="utf-8"))
    if args.from_file:
        records = json.loads(args.from_file.read_text(encoding="utf-8"))
    else:
        headers = {"User-Agent": get_settings().nominatim_user_agent}
        with httpx.Client(timeout=60, headers=headers) as client:
            print("Resolving species names on GBIF...")
            keys = resolve_taxon_keys(client)
            print(f"Fetching {code} records (a few minutes)...")
            records = fetch_all(client, keys, code)
        if args.save_raw:
            args.save_raw.write_text(json.dumps(records), encoding="utf-8")
            print(f"raw records saved to {args.save_raw}")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        summary = run(db, code, osm_payload, records)
        db.commit()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        db.close()

    print(f"GBIF records read: {summary.records_read}" + (f" ({summary.duplicates} duplicates)" if summary.duplicates else ""))
    print(f"saved {summary.matched} records on {summary.lakes_with_records} lakes")
    print("licences: " + ", ".join(f"{k} {v}" for k, v in summary.by_license.items()))
    print("not saved: " + ", ".join(f"{k} {v}" for k, v in sorted(summary.skipped.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
