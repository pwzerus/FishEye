"""Experiment: how many Texas lakes could GBIF fill in with species records?

A one-off measurement, not part of the app. It answers two questions before
anyone builds a GBIF import:

1. Coverage. Of the lakes on the map (tx_osm.json, the statewide OSM layer),
   how many have at least one GBIF record of a species this app has a guide
   for? Broken down by reservoir / lake / pond.
2. Quality. On the seven lakes whose species list comes from TPWD survey
   reports, how well does GBIF agree with TPWD? This is the number that
   decides whether GBIF records are worth showing at all, even labelled
   "community reported".

GBIF aggregates iNaturalist research-grade observations, museum specimens
and survey datasets. Records are matched to a lake when they fall inside the
lake's OSM bounding box (the smallest one, if several overlap). A bounding
box is larger than the water, so a record on the shore or in an inflowing
river can count; treat coverage as an upper bound.

Run from backend/ on a machine that can reach api.gbif.org:

    python -m app.experiments.gbif_texas_coverage --osm tx_osm.json --save-raw gbif_tx_raw.json
    python -m app.experiments.gbif_texas_coverage --osm tx_osm.json --from-file gbif_tx_raw.json

Writes a machine-readable report to gbif_tx_report.json and prints a summary.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select

from app.core.config import get_settings

# Fetching and matching now live in the importer this experiment led to;
# the experiment reuses them so both always agree on what a match is.
from app.data_import.gbif_occurrence_import import (
    LakeIndex,
    fetch_all,
    license_family,
    resolve_taxon_keys,
    usable,
)
from app.data_import.osm_waterbody_import import (
    VERIFIED_MATCH_MARGIN_M,
    OsmLake,
    core_name,
    parse_elements,
)
from app.db.session import SessionLocal
from app.models.waterbody import Species, Waterbody, WaterbodySpecies

RECENT_YEAR = 2015

# The seven lakes whose species come from TPWD survey reports. The three
# original seed lakes carry placeholder species and are left out of the
# quality check.
TPWD_VERIFIED = {
    "Lake Somerville",
    "Lake Bryan",
    "Lake Conroe",
    "Lake Houston",
    "Lake Livingston",
    "Fayette County Reservoir",
    "Gibbons Creek Reservoir",
}


# --------------------------------------------------------------------------
# Matching (pure)
# --------------------------------------------------------------------------


# About a quarter of Texas's named OSM "reservoirs" are USDA Soil Conservation
# Service flood-control structures ("Soil Conservation Service Site 4
# Reservoir"), mostly on private ranch land. They're reported separately so
# they don't inflate the coverage denominator.
_FLOOD_CONTROL = re.compile(r"soil conservation service|\bscs site\b|watershed .*site", re.I)


def is_flood_control(name: str) -> bool:
    return bool(_FLOOD_CONTROL.search(name))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class VerifiedLake:
    name: str
    latitude: float
    longitude: float
    species: frozenset[str]  # confirmed by TPWD


def osm_refs_for(verified: VerifiedLake, lakes: list[OsmLake], linked: set[str]) -> set[str]:
    """Every OSM element that is this lake. OSM often maps one reservoir as
    several elements under different word orders ("Somerville Lake"), so this
    uses the importer's own twin rule: shared core name words, and the
    verified lake's centre within reach of the element's extent."""
    words = set(core_name(verified.name).split())
    refs = set(linked)
    for lake in lakes:
        lake_words = set(core_name(lake.name).split())
        if (
            words
            and lake_words
            and (words <= lake_words or lake_words <= words)
            and lake.bounds.expanded(VERIFIED_MATCH_MARGIN_M).contains(verified.latitude, verified.longitude)
        ):
            refs.add(lake.osm_ref)
    return refs


def build_report(
    lakes: list[OsmLake],
    records: list[dict[str, Any]],
    db_lakes: dict[str, tuple[str, str]],  # osm_ref -> (name, data_tier)
    tpwd_lakes: list[VerifiedLake],
) -> dict[str, Any]:
    index = LakeIndex(lakes)
    by_ref = {lake.osm_ref: lake for lake in lakes}

    per_lake_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmatched = 0
    usable_records = [r for r in records if usable(r)]
    for r in usable_records:
        lake = index.lookup(float(r["decimalLatitude"]), float(r["decimalLongitude"]))
        if lake is None:
            unmatched += 1
            continue
        per_lake_records[lake.osm_ref].append(r)

    matched = [r for rs in per_lake_records.values() for r in rs]

    def tier_of(ref: str) -> str:
        return db_lakes.get(ref, ("", "osm"))[1]

    def name_of(ref: str) -> str:
        return db_lakes.get(ref, (by_ref[ref].name, ""))[0] or by_ref[ref].name

    by_type_total = Counter(lake.water_type for lake in lakes)
    by_type_hit = Counter(by_ref[ref].water_type for ref in per_lake_records)
    species_per_lake = {ref: {r["species"] for r in rs} for ref, rs in per_lake_records.items()}

    # Quality: agreement with TPWD on the survey-verified lakes.
    validation = []
    for vl in sorted(tpwd_lakes, key=lambda x: x.name):
        linked = {ref for ref, (name, _) in db_lakes.items() if name == vl.name}
        refs = osm_refs_for(vl, lakes, linked)
        gbif: set[str] = set()
        for ref in refs:
            gbif |= species_per_lake.get(ref, set())
        tpwd = set(vl.species)
        lake_name = vl.name
        validation.append(
            {
                "lake": lake_name,
                "tpwd_species": sorted(tpwd),
                "gbif_species": sorted(gbif),
                "both": sorted(tpwd & gbif),
                "gbif_only": sorted(gbif - tpwd),
                "tpwd_only": sorted(tpwd - gbif),
            }
        )
    gbif_total = sum(len(v["gbif_species"]) for v in validation)
    tpwd_total = sum(len(v["tpwd_species"]) for v in validation)
    both_total = sum(len(v["both"]) for v in validation)

    top = sorted(per_lake_records.items(), key=lambda kv: -len(kv[1]))[:20]

    return {
        "records": {
            "fetched": len(records),
            "usable_coordinates": len(usable_records),
            "missing_uncertainty": sum(1 for r in records if r.get("coordinateUncertaintyInMeters") is None),
            "matched_to_a_lake": len(matched),
            "not_in_any_lake": unmatched,
            "by_species_matched": dict(Counter(r["species"] for r in matched).most_common()),
            "basis_of_record": dict(Counter(r.get("basisOfRecord") for r in matched).most_common()),
            "license": dict(Counter(license_family(r.get("license")) for r in matched).most_common()),
            "since_2015_share": round(
                sum(1 for r in matched if (r.get("year") or 0) >= RECENT_YEAR) / max(len(matched), 1), 3
            ),
        },
        "coverage": {
            "lakes_total": len(lakes),
            "lakes_with_any_record": len(per_lake_records),
            "lakes_with_2plus_species": sum(1 for s in species_per_lake.values() if len(s) >= 2),
            "lakes_with_5plus_records": sum(1 for rs in per_lake_records.values() if len(rs) >= 5),
            "by_water_type": {
                t: {"lakes": by_type_total[t], "with_records": by_type_hit.get(t, 0)} for t in sorted(by_type_total)
            },
            "verified_lakes_with_records": sum(1 for ref in per_lake_records if tier_of(ref) == "verified"),
            "flood_control_structures": {
                "lakes": sum(1 for lake in lakes if is_flood_control(lake.name)),
                "with_records": sum(1 for ref in per_lake_records if is_flood_control(by_ref[ref].name)),
            },
            "excluding_flood_control": {
                "lakes": sum(1 for lake in lakes if not is_flood_control(lake.name)),
                "with_records": sum(1 for ref in per_lake_records if not is_flood_control(by_ref[ref].name)),
            },
        },
        "tpwd_agreement": {
            "lakes": validation,
            "gbif_species_confirmed_by_tpwd": f"{both_total}/{gbif_total}",
            "tpwd_species_found_in_gbif": f"{both_total}/{tpwd_total}",
        },
        "top_lakes": [
            {
                "name": name_of(ref),
                "tier": tier_of(ref),
                "water_type": by_ref[ref].water_type,
                "records": len(rs),
                "species": sorted({r["species"] for r in rs}),
            }
            for ref, rs in top
        ],
    }


def print_summary(report: dict[str, Any]) -> None:
    r, c, v = report["records"], report["coverage"], report["tpwd_agreement"]
    pct = lambda a, b: f"{a}/{b} ({100 * a / max(b, 1):.1f}%)"  # noqa: E731
    print("\n=== GBIF records ===")
    print(f"fetched {r['fetched']}, usable coordinates {r['usable_coordinates']}, "
          f"matched to a lake {r['matched_to_a_lake']}, outside every lake {r['not_in_any_lake']}")
    print(f"record types: {r['basis_of_record']}")
    print(f"licences: {r['license']}")
    print(f"recorded {RECENT_YEAR} or later: {r['since_2015_share']:.0%}")
    print(f"matched records by species: {r['by_species_matched']}")
    print("\n=== Coverage ===")
    print(f"lakes with at least one record: {pct(c['lakes_with_any_record'], c['lakes_total'])}")
    for t, d in c["by_water_type"].items():
        print(f"  {t:10} {pct(d['with_records'], d['lakes'])}")
    fc, ex = c["flood_control_structures"], c["excluding_flood_control"]
    print(f"  flood-control structures (mostly private): {pct(fc['with_records'], fc['lakes'])}")
    print(f"  everything else:                          {pct(ex['with_records'], ex['lakes'])}")
    print(f"lakes with 2+ species: {c['lakes_with_2plus_species']}, with 5+ records: {c['lakes_with_5plus_records']}")
    print("\n=== Agreement with TPWD (7 survey-verified lakes) ===")
    print(f"GBIF species also on TPWD's list: {v['gbif_species_confirmed_by_tpwd']}")
    print(f"TPWD species that GBIF also has:  {v['tpwd_species_found_in_gbif']}")
    for lake in v["lakes"]:
        print(f"  {lake['lake']}: both={len(lake['both'])} gbif_only={lake['gbif_only']} tpwd_only={len(lake['tpwd_only'])}")
    print("\n=== Top lakes by record count ===")
    for t in report["top_lakes"][:10]:
        print(f"  {t['name'][:40]:40} {t['tier']:9} {t['water_type']:10} {t['records']:5} records, {len(t['species'])} species")


def _db_context() -> tuple[dict[str, tuple[str, str]], list[VerifiedLake]]:
    db = SessionLocal()
    try:
        db_lakes = {
            wb.osm_ref: (wb.name, wb.data_tier)
            for wb in db.scalars(select(Waterbody).where(Waterbody.osm_ref.is_not(None)))
            if wb.osm_ref is not None
        }
        species: dict[int, set[str]] = defaultdict(set)
        for wb_id, name in db.execute(
            select(WaterbodySpecies.waterbody_id, Species.common_name).join(
                Species, Species.id == WaterbodySpecies.species_id
            )
        ).all():
            species[wb_id].add(name)
        tpwd = [
            VerifiedLake(wb.name, wb.latitude, wb.longitude, frozenset(species[wb.id]))
            for wb in db.scalars(select(Waterbody).where(Waterbody.name.in_(TPWD_VERIFIED)))
        ]
        return db_lakes, tpwd
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--osm", type=Path, required=True, help="tx_osm.json from osm_waterbody_import --save-raw")
    parser.add_argument("--from-file", type=Path, help="reuse GBIF records saved by --save-raw")
    parser.add_argument("--save-raw", type=Path, help="save fetched GBIF records here")
    parser.add_argument("--report", type=Path, default=Path("gbif_tx_report.json"))
    args = parser.parse_args(argv)

    lakes, _, _ = parse_elements(json.loads(args.osm.read_text(encoding="utf-8")))
    print(f"{len(lakes)} lakes loaded from {args.osm}")

    if args.from_file:
        records = json.loads(args.from_file.read_text(encoding="utf-8"))
    else:
        headers = {"User-Agent": get_settings().nominatim_user_agent}
        with httpx.Client(timeout=60, headers=headers) as client:
            print("Resolving species names on GBIF...")
            keys = resolve_taxon_keys(client)
            print("  " + ", ".join(f"{k}: {v or 'not found'}" for k, v in keys.items()))
            print("Fetching Texas records (a few minutes)...")
            records = fetch_all(client, keys)
        if args.save_raw:
            args.save_raw.write_text(json.dumps(records), encoding="utf-8")
            print(f"raw records saved to {args.save_raw}")

    db_lakes, tpwd = _db_context()
    report = build_report(lakes, records, db_lakes, tpwd)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_summary(report)
    print(f"\nFull report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
