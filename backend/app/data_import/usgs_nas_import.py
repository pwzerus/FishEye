"""Non-native fish recorded in a state's lakes, from USGS NAS (public domain).

The USGS Nonindigenous Aquatic Species database (https://nas.er.usgs.gov)
records where fish living outside their native range have been found:
museum specimens, agency reports, literature. In California that is most of
the sport fish (largemouth bass, striped bass, crappie, bluegill are all
introduced there). Each record that falls inside a lake becomes a
SpeciesOccurrence (source "usgs_nas"), the same "reported" tier as GBIF
(docs/adr/0012): shown as "recorded here", never as confirmed, never scored.

Kept: records with exact ("Accurate") or locality-geocoded ("Approximate")
coordinates; not county or state centroids. Left out: records whose status
says the fish is no longer there (failed, extirpated, eradicated), and fish
species_names.py doesn't know.

Lakes are matched like GBIF records: the smallest OpenStreetMap lake box
holding the point; in California also the boxes of lakes added from CDFW's
layer (cdfw_import.py). Re-running replaces the state's NAS records.

    python -m app.data_import.usgs_nas_import --state CA --fetch
    python -m app.data_import.usgs_nas_import --state CA --osm osm_cache/ca_osm.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.data_import.gbif_occurrence_import import LakeIndex, lake_targets
from app.data_import.osm_waterbody_import import Bounds, OsmLake, merge_pieces, parse_elements
from app.data_import.provenance import USER_AGENT, source_record
from app.data_import.species_names import by_scientific_name, canonical
from app.data_import.us_states import BY_CODE
from app.models.waterbody import SpeciesOccurrence, State, Waterbody

API = "https://nas.er.usgs.gov/api/v2/occurrence/search"
DEFAULT_CACHE = Path("usgs_nas_cache")
PAGE = 1000
REQUEST_DELAY_S = 1.0
GONE = {"failed", "extirpated", "eradicated"}
KEEP_FIELDS = ("key", "scientificName", "commonName", "decimalLatitude", "decimalLongitude",
               "latLongAccuracy", "year", "status", "recordType", "locality", "county")


def fetch(state_code: str, cache: Path) -> Path:
    import httpx

    rows: list[dict[str, Any]] = []
    offset = 0
    with httpx.Client(timeout=120, headers={"User-Agent": USER_AGENT}) as client:
        while True:
            for attempt in range(4):
                resp = client.get(API, params={"state": state_code, "group": "Fishes", "limit": PAGE, "offset": offset})
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(5 * 2**attempt)
                    continue
                resp.raise_for_status()
                break
            body = resp.json()
            page = body.get("results") or []
            rows += [{k: r.get(k) for k in KEEP_FIELDS} for r in page]
            time.sleep(REQUEST_DELAY_S)
            if not page or str(body.get("endOfRecords")).lower() == "true":
                break
            offset += len(page)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{state_code.lower()}_nas.json"
    path.write_text(json.dumps({"fetched_at": datetime.now(timezone.utc).isoformat(), "source": API, "records": rows}), encoding="utf-8")
    return path


def species_for(record: dict[str, Any]) -> str | None:
    hit = canonical(record.get("commonName"))
    by_sci = by_scientific_name(record.get("scientificName"))
    if by_sci:
        return by_sci
    return hit[0] if hit and hit[0] not in ("Trout", "Catfish") else None


@dataclass
class ImportSummary:
    records: int = 0
    skipped: Counter[str] = field(default_factory=Counter)
    matched: int = 0
    lakes: int = 0
    by_species: Counter[str] = field(default_factory=Counter)


def _cdfw_lakes(db: Session, state: State, cdfw_cache: Path) -> tuple[list[OsmLake], dict[str, int]]:
    """California lakes added from CDFW's layer have no OpenStreetMap box;
    CDFW's own box stands in for it."""
    path = cdfw_cache / "ca_lakes.json"
    if state.code != "CA" or not path.exists():
        return [], {}
    added = {
        wb.dfg_water_id: wb.id
        for wb in db.scalars(select(Waterbody).where(
            Waterbody.state_id == state.id, Waterbody.osm_ref.is_(None), Waterbody.dfg_water_id.is_not(None)))
    }
    lakes, targets = [], {}
    for r in json.loads(path.read_text(encoding="utf-8")):
        if r.get("id") in added and r.get("bbox"):
            ref = f"cdfw/{r['id']}"
            b = Bounds(*r["bbox"])
            lakes.append(OsmLake(ref, r.get("name") or "", r["lat"], r["lng"], b))
            targets[ref] = added[r["id"]]
    return lakes, targets


def run(db: Session, state_code: str, payload: dict[str, Any], osm_payload: dict[str, Any], cdfw_cache: Path = Path("cdfw_cache")) -> ImportSummary:
    state = db.scalar(select(State).where(State.code == state_code))
    if state is None:
        raise ValueError(f"No {state_code} lakes in the database.")
    stamp = payload.get("fetched_at")
    fetched = datetime.fromisoformat(stamp).astimezone(timezone.utc).replace(tzinfo=None) if stamp else datetime.now(timezone.utc).replace(tzinfo=None)
    source_record(db, "usgs_nas", fetched)
    osm_lakes = merge_pieces(parse_elements(osm_payload)[0])
    targets = lake_targets(db, state, osm_lakes)
    extra, extra_targets = _cdfw_lakes(db, state, cdfw_cache)
    targets.update(extra_targets)
    index = LakeIndex(osm_lakes + extra)

    summary = ImportSummary()
    rows = []
    seen: set[str] = set()
    for r in payload.get("records") or []:
        summary.records += 1
        key = str(r.get("key"))
        if key in seen:
            summary.skipped["duplicate"] += 1
            continue
        seen.add(key)
        if (r.get("status") or "").lower() in GONE:
            summary.skipped["no longer there (failed/extirpated/eradicated)"] += 1
            continue
        if r.get("latLongAccuracy") not in ("Accurate", "Approximate"):
            summary.skipped["county or state centroid only"] += 1
            continue
        name = species_for(r)
        if name is None:
            summary.skipped["species not mapped"] += 1
            continue
        try:
            lat, lng = float(r["decimalLatitude"]), float(r["decimalLongitude"])
        except (TypeError, ValueError):
            summary.skipped["no coordinates"] += 1
            continue
        lake = index.lookup(lat, lng)
        wb_id = targets.get(lake.osm_ref) if lake is not None else None
        if wb_id is None:
            summary.skipped["not in a lake"] += 1
            continue
        rows.append({
            "waterbody_id": wb_id, "species_name": name, "source": "usgs_nas", "source_record_id": key,
            "year": int(r["year"]) if str(r.get("year") or "").isdigit() else None,
            "basis_of_record": (r.get("recordType") or None) and str(r["recordType"])[:32],
            "source_group": "usgs_nas", "dataset_name": "USGS Nonindigenous Aquatic Species",
            "institution_code": "USGS", "license": "PD", "latitude": lat, "longitude": lng, "imported_at": fetched,
        })
        summary.by_species[name] += 1
    db.execute(delete(SpeciesOccurrence).where(
        SpeciesOccurrence.source == "usgs_nas",
        SpeciesOccurrence.waterbody_id.in_(select(Waterbody.id).where(Waterbody.state_id == state.id)),
    ))
    if rows:
        db.execute(insert(SpeciesOccurrence), rows)
    db.flush()
    summary.matched = len(rows)
    summary.lakes = len({r["waterbody_id"] for r in rows})
    return summary


def main(argv: list[str] | None = None) -> int:
    from app.db.session import SessionLocal, engine
    from app.db.upgrades import prepare_database

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", required=True)
    ap.add_argument("--osm", type=Path, help="the state's OpenStreetMap payload (default osm_cache/<state>_osm.json)")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--cdfw-cache", type=Path, default=Path("cdfw_cache"),
                    help="California: CDFW's lake layer, for lakes added from it (cdfw_import.py)")
    args = ap.parse_args(argv)
    code = args.state.upper()
    if code not in BY_CODE:
        print(f"unknown state {code}", file=sys.stderr)
        return 2
    path = fetch(code, args.cache) if args.fetch else args.cache / f"{code.lower()}_nas.json"
    if not path.exists():
        print(f"No {path}: run with --fetch first.", file=sys.stderr)
        return 2
    osm_path = args.osm or Path("osm_cache") / f"{code.lower()}_osm.json"
    prepare_database(engine)
    with SessionLocal() as db:
        summary = run(db, code, json.loads(path.read_text(encoding="utf-8")),
                      json.loads(osm_path.read_text(encoding="utf-8")), cdfw_cache=args.cdfw_cache)
        db.commit()
    print(f"{code}: {summary.records} NAS fish records; {summary.matched} in {summary.lakes} lakes")
    print("  skipped: " + ", ".join(f"{k}={v}" for k, v in summary.skipped.most_common()))
    print("  by species: " + ", ".join(f"{k} {v}" for k, v in summary.by_species.most_common(12)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
