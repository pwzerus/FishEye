"""Every lake TPWD publishes a page for, from the pages tpwd_fetch.py saved.

See docs/adr/0022-statewide-tpwd-lakes.md. For each of TPWD's ~175 lake
pages this:

1. places the lake on the map (below);
2. stores TPWD's own profile of it (AgencyLakeProfile): surface area,
   location, the predominant-species list and TPWD's poor-to-excellent
   fishing ratings, with links to the lake page and latest survey report;
3. links the guide species TPWD says are there (WaterbodySpecies,
   confidence "confirmed"), each with the sentence or list item that says
   so;
4. adds TPWD's public boat ramps on that lake (AccessPoint,
   "confirmed_public"), from TPWD's statewide Public Boat Ramps dataset.

The lake becomes data_tier "verified": its species and access now come from
the state agency.

PLACING A LAKE
--------------
TPWD's lake pages have no coordinates. Two independent sources do:
OpenStreetMap (already imported, osm_waterbody_import.py) and TPWD's boat
ramp dataset, whose every ramp names its lake. A lake is matched to an
OpenStreetMap lake of the same name (core_name: "Lake Somerville" =
"Somerville Lake"); when TPWD has ramps on it, the OpenStreetMap lake must
also be near those ramps, which is what separates Moss Lake near Gainesville
from a Moss Lake two hundred miles away. Then:

- same name and near TPWD's ramps          -> that lake ("osm_name")
- same name, no ramps, only one such lake  -> that lake ("osm_name_only")
- ramps but no OpenStreetMap lake near     -> a new lake at the ramps' median
                                              point ("ramps"), marked as such
- one of the hand-curated lakes            -> kept as it is ("existing")
- anything else                            -> left out and listed in the
                                              summary, never guessed

Ramps are only used within a radius of their own median that grows with
the lake's surface area. A few rows in TPWD's dataset name a lake but sit a
county or more away; those are dropped rather than plotted.

Run (offline; reads what tpwd_fetch.py saved):
    python -m app.data_import.tpwd_statewide_import
    python -m app.data_import.tpwd_statewide_import --dry-run
    python -m app.data_import.tpwd_statewide_import --cache tpwd_cache --ramps tpwd_cache/BoatRamps_Public.geojson
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_import.osm_waterbody_import import core_name
from app.data_import.tpwd_lake_survey_scraper import upsert_species
from app.data_import.tpwd_pages import BASE, LakePage, ReportPage, parse_lake_page, parse_report_page
from app.models.waterbody import AccessPoint, AgencyLakeProfile, State, Waterbody, WaterbodySpecies

AGENCY = "tpwd"
DEFAULT_CACHE = Path("tpwd_cache")
# A ramp counts as the same as an existing confirmed access point within this.
DUPLICATE_ACCESS_M = 150.0
ACRES_TO_KM2 = 0.004046856

# TPWD name -> OpenStreetMap name, where the two differ by more than
# core_name() evens out. Each one was checked: the OpenStreetMap lake sits
# next to TPWD's own boat ramps for that lake (see the ADR).
NAME_ALIASES: dict[str, str] = {
    "Lake LBJ": "Lake Lyndon B. Johnson",
    "Falcon Reservoir": "Presa Internacional Falcón",
    "Palo Pinto Reservoir": "Palo Pinto Creek Reservoir",
    "Walter Long Lake": "Walter E Long Lake",
}


# Lakes whose only same-named OpenStreetMap lake is a different lake, found by
# checking every "osm_name_only" placement against the location TPWD's page
# gives. Left out rather than plotted in the wrong county.
NOT_THE_SAME_LAKE: dict[str, str] = {
    "Lone Star Lake": "TPWD's is in Morris County; OpenStreetMap's only Lone Star Lake is near Mineral Wells",
}


@dataclass(frozen=True)
class Ramp:
    pwaid: int
    lake_name: str
    latitude: float
    longitude: float
    tpw_id: str  # e.g. "burleson001": TPWD's county-prefixed id


def load_ramps(path: Path) -> list[Ramp]:
    """The lake and reservoir ramps in TPWD's Public Boat Ramps GeoJSON
    (rivers and bays are a different app)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    ramps: list[Ramp] = []
    for feature in data.get("features", []):
        p = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        if p.get("AccessType") != "Lake/Reservoir" or geometry.get("type") != "Point":
            continue
        lng, lat = geometry["coordinates"][:2]
        name = (p.get("AccessTypeDescription") or "").strip()
        if not name:
            continue
        ramps.append(Ramp(int(p.get("PWAID") or p.get("OBJECTID")), name, float(lat), float(lng), str(p.get("TPWAID") or "")))
    return ramps


def km_between(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Equirectangular distance; plenty for "is it within a few km"."""
    x = (lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    return 6371.0 * math.hypot(math.radians(lat2 - lat1), math.radians(x))


def search_radius_km(surface_acres: int | None) -> float:
    """How far from the middle of a lake its ramps (and its OpenStreetMap
    twin's centre) may be: four times the side of a square of the lake's
    area, at least 8 km. Toledo Bend (181,600 acres) gets about 110 km,
    Lake Somerville (11,456) about 27."""
    area_km2 = (surface_acres or 0) * ACRES_TO_KM2
    return max(8.0, 4.0 * math.sqrt(area_km2))


@dataclass
class Placement:
    waterbody: Waterbody | None
    method: str  # osm_name | osm_name_only | ramps | existing | unplaced
    ramps: list[Ramp] = field(default_factory=list)
    reason: str = ""


class LakeIndex:
    """The state's lakes by core name, loaded once."""

    def __init__(self, waterbodies: list[Waterbody]) -> None:
        self.by_core: dict[str, list[Waterbody]] = defaultdict(list)
        for wb in waterbodies:
            self.by_core[core_name(wb.name)].append(wb)

    def named(self, *names: str) -> list[Waterbody]:
        out: list[Waterbody] = []
        for name in names:
            for wb in self.by_core.get(core_name(name), []):
                if wb not in out:
                    out.append(wb)
        return out

    def add(self, wb: Waterbody) -> None:
        self.by_core[core_name(wb.name)].append(wb)


def place(lake: LakePage, lakes: LakeIndex, ramps_by_core: dict[str, list[Ramp]]) -> Placement:
    names = [lake.name] + ([NAME_ALIASES[lake.name]] if lake.name in NAME_ALIASES else [])
    radius = search_radius_km(lake.surface_acres)

    ramps: list[Ramp] = []
    for name in names:
        ramps += [r for r in ramps_by_core.get(core_name(name), []) if r not in ramps]
    anchor: tuple[float, float] | None = None
    if ramps:
        anchor = (statistics.median(r.latitude for r in ramps), statistics.median(r.longitude for r in ramps))
        ramps = [r for r in ramps if km_between(r.latitude, r.longitude, *anchor) <= radius]

    candidates = lakes.named(*names)
    if anchor is not None:
        candidates = [wb for wb in candidates if km_between(wb.latitude, wb.longitude, *anchor) <= radius]

    # A lake this import placed on an earlier run keeps the placement it got
    # then (re-running must not relabel a "ramps" lake as "osm_name" just
    # because it now exists under that name).
    for wb in candidates:
        profile = wb.agency_profile
        if profile is not None and profile.agency == AGENCY and profile.agency_lake_id == lake.slug:
            return Placement(wb, profile.placement, ramps)
    # A hand-curated lake: verified before this import ever touched it.
    curated = [wb for wb in candidates if wb.data_tier == "verified" and wb.agency_profile is None]
    if curated:
        return Placement(curated[0], "existing", ramps)
    candidates = [wb for wb in candidates if wb.agency_profile is None]
    if anchor is not None:
        if candidates:
            nearest = min(candidates, key=lambda wb: km_between(wb.latitude, wb.longitude, *anchor))
            return Placement(nearest, "osm_name", ramps)
        return Placement(None, "ramps", ramps)
    if len(candidates) == 1:
        if lake.name in NOT_THE_SAME_LAKE:
            return Placement(None, "unplaced", reason=NOT_THE_SAME_LAKE[lake.name])
        return Placement(candidates[0], "osm_name_only", ramps)
    if candidates:
        return Placement(None, "unplaced", reason=f"{len(candidates)} lakes share the name and TPWD lists no ramps to tell them apart")
    return Placement(None, "unplaced", reason="no OpenStreetMap lake of that name and no TPWD ramps")


@dataclass
class ImportSummary:
    placed: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    unplaced: list[tuple[str, str]] = field(default_factory=list)
    species_links: int = 0
    ramps_added: int = 0
    ramps_skipped_duplicate: int = 0
    osm_entrances_replaced: int = 0
    lakes_without_ramps: list[str] = field(default_factory=list)


def _evidence(lake: LakePage, report: ReportPage | None, retrieved_at: datetime) -> dict[str, tuple[str, str, datetime]]:
    """species -> (evidence, source_url, observed_at). The survey report's
    own sentence when it has one, otherwise the lake page's list item."""
    out: dict[str, tuple[str, str, datetime]] = {}
    if report is not None:
        observed = datetime(report.year, 1, 1) if report.year else retrieved_at
        for m in report.mentions:
            out[m.species_name] = (m.evidence_sentence, report.url, observed)
    for name, item in lake.species.items():
        out.setdefault(
            name,
            (f"Listed by TPWD among this lake's predominant fish species: “{item}”.", lake.url, retrieved_at),
        )
    return out


def _write_species(db: Session, wb: Waterbody, evidence: dict[str, tuple[str, str, datetime]]) -> int:
    """Replace this lake's TPWD-sourced species links; any other source's
    (hand curation) are left alone."""
    for link in list(wb.species_links):
        if link.source_url.startswith(BASE):
            wb.species_links.remove(link)
    db.flush()
    existing = {link.species.common_name for link in wb.species_links}
    written = 0
    for name, (sentence, url, observed) in evidence.items():
        if name in existing:
            continue
        species = upsert_species(db, name)
        db.add(
            WaterbodySpecies(
                waterbody_id=wb.id,
                species_id=species.id,
                confidence="confirmed",
                evidence=sentence[:2000],
                source_url=url,
                observed_at=observed,
            )
        )
        written += 1
    db.flush()
    return written


def _write_ramps(db: Session, wb: Waterbody, ramps: list[Ramp], summary: ImportSummary) -> int:
    if wb.public_access_status == "closed":
        return 0  # PRD §12: a closed lake shows no public access, official or not
    confirmed = [ap for ap in wb.access_points if ap.public_status == "confirmed_public"]
    added = 0
    for ramp in ramps:
        ref = f"tpwd_ramp/{ramp.pwaid}"
        mine = next((ap for ap in confirmed if ap.osm_ref == ref), None)
        if mine is None and any(
            km_between(ap.latitude, ap.longitude, ramp.latitude, ramp.longitude) * 1000 < DUPLICATE_ACCESS_M
            for ap in confirmed
        ):
            summary.ramps_skipped_duplicate += 1
            continue
        if mine is None:
            mine = AccessPoint(waterbody_id=wb.id, osm_ref=ref, public_status="confirmed_public")
            db.add(mine)
            confirmed.append(mine)
        mine.name = f"Public boat ramp (TPWD #{ramp.pwaid})"
        mine.latitude = ramp.latitude
        mine.longitude = ramp.longitude
        mine.access_type = "boat_ramp"
        mine.parking = False
        added += 1
    if added:
        # Official ramps replace OpenStreetMap's guesses on this lake.
        for ap in list(wb.access_points):
            if ap.public_status == "osm_reported":
                wb.access_points.remove(ap)
                summary.osm_entrances_replaced += 1
    db.flush()
    return added


def _access_summary(wb: Waterbody, lake: LakePage, ramp_count: int) -> str:
    if wb.public_access_status == "closed":
        return wb.access_summary
    if ramp_count:
        return (
            f"TPWD's statewide boat-ramp list has {ramp_count} public ramp"
            f"{'s' if ramp_count != 1 else ''} on {lake.name}. Fees, hours and parks are on TPWD's access page."
        )
    return (
        f"TPWD's statewide boat-ramp list has no ramp on {lake.name}. "
        "Check TPWD's access page before you go."
    )


def import_lake(
    db: Session,
    state: State,
    lake: LakePage,
    report: ReportPage | None,
    placement: Placement,
    retrieved_at: datetime,
    summary: ImportSummary,
) -> Waterbody:
    wb = placement.waterbody
    if wb is None:  # "ramps": TPWD's ramps are the only location there is
        lat = statistics.median(r.latitude for r in placement.ramps)
        lng = statistics.median(r.longitude for r in placement.ramps)
        wb = Waterbody(
            state_id=state.id, name=lake.name, latitude=lat, longitude=lng, access_summary="",
            source_url=lake.url, source_updated_at=retrieved_at, field_tested=False,
            public_access_status="open", data_tier="verified", water_type="reservoir",
        )
        db.add(wb)
        db.flush()
    elif placement.method != "existing":
        wb.name = lake.name
        wb.data_tier = "verified"
        wb.source_url = lake.url
        wb.source_updated_at = retrieved_at

    summary.species_links += _write_species(db, wb, _evidence(lake, report, retrieved_at))
    added = _write_ramps(db, wb, placement.ramps, summary)
    summary.ramps_added += added
    if added and wb.public_access_status == "unknown":
        wb.public_access_status = "open"
    if not placement.ramps:
        summary.lakes_without_ramps.append(lake.name)
    if placement.method != "existing":
        wb.access_summary = _access_summary(wb, lake, sum(
            1 for ap in wb.access_points if ap.public_status == "confirmed_public"
        ))

    profile = db.scalar(
        select(AgencyLakeProfile).where(AgencyLakeProfile.agency == AGENCY, AgencyLakeProfile.agency_lake_id == lake.slug)
    )
    if profile is None:
        profile = wb.agency_profile or AgencyLakeProfile(agency=AGENCY, agency_lake_id=lake.slug)
        if profile.id is None:
            db.add(profile)
    profile.waterbody_id = wb.id
    profile.agency_lake_id = lake.slug
    profile.agency_name = lake.name
    profile.page_url = lake.url
    profile.access_page_url = lake.access_url
    profile.survey_report_url = report.url if report else None
    profile.survey_year = report.year if report else None
    profile.location = lake.location
    profile.surface_acres = lake.surface_acres
    profile.max_depth_ft = lake.max_depth_ft
    profile.impounded = lake.impounded
    profile.predominant_species = list(lake.predominant)
    profile.ratings = [{"label": r.label, "rating": r.rating} for r in lake.ratings]
    profile.placement = placement.method
    profile.retrieved_at = retrieved_at
    db.flush()
    return wb


def _retrieved(manifest: dict, filename: str) -> datetime:
    stamp = manifest.get(filename, {}).get("fetched_at")
    if stamp:
        return datetime.fromisoformat(stamp).astimezone(timezone.utc).replace(tzinfo=None)
    return datetime.now(timezone.utc).replace(tzinfo=None)


def find_ramps_file(cache: Path) -> Path | None:
    for pattern in ("*.geojson", "*ramp*.json"):
        found = sorted(cache.glob(pattern))
        if found:
            return found[0]
    return None


def run(db: Session, cache: Path, ramps: list[Ramp], state_code: str = "TX") -> ImportSummary:
    manifest_path = cache / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    state = db.scalar(select(State).where(State.code == state_code))
    if state is None:
        raise SystemExit(f"No {state_code} lakes in the database yet: run the OpenStreetMap import first.")

    reports: dict[str, ReportPage] = {}
    for path in sorted(cache.glob("report__*.html")):
        rid = path.stem.split("__", 1)[1]
        reports[rid] = parse_report_page(path.read_text(encoding="utf-8"), rid)

    lakes = LakeIndex(list(db.scalars(select(Waterbody).where(Waterbody.state_id == state.id))))
    ramps_by_core: dict[str, list[Ramp]] = defaultdict(list)
    for r in ramps:
        ramps_by_core[core_name(r.lake_name)].append(r)

    summary = ImportSummary()
    claimed: dict[int, str] = {}
    for path in sorted(cache.glob("lake__*.html")):
        slug = path.stem.split("__", 1)[1]
        lake = parse_lake_page(path.read_text(encoding="utf-8"), slug)
        placement = place(lake, lakes, ramps_by_core)
        if placement.method == "unplaced":
            summary.unplaced.append((lake.name, placement.reason))
            continue
        if placement.waterbody is not None and placement.waterbody.id in claimed:
            summary.unplaced.append((lake.name, f"its match is already {claimed[placement.waterbody.id]}"))
            continue
        report = reports.get(lake.report_id) if lake.report_id else None
        wb = import_lake(db, state, lake, report, placement, _retrieved(manifest, path.name), summary)
        if placement.method == "ramps":
            lakes.add(wb)
        claimed[wb.id] = lake.name
        summary.placed[placement.method] += 1
    return summary


def main(argv: list[str] | None = None) -> int:
    from app.db.session import Base, SessionLocal, engine

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help=f"folder tpwd_fetch saved (default: {DEFAULT_CACHE})")
    ap.add_argument("--ramps", type=Path, help="TPWD Public Boat Ramps GeoJSON (default: the .geojson in --cache)")
    ap.add_argument("--state", default="TX")
    ap.add_argument("--dry-run", action="store_true", help="do everything, then roll back")
    args = ap.parse_args(argv)

    ramps_path = args.ramps or find_ramps_file(args.cache)
    if ramps_path is None or not ramps_path.exists():
        print(
            "No boat-ramp file. Download TPWD's Public Boat Ramps as GeoJSON from\n"
            "https://gis-tpwd.opendata.arcgis.com/datasets/public-boat-ramps into the cache folder.",
            file=sys.stderr,
        )
        return 2
    if not any(args.cache.glob("lake__*.html")):
        print(f"No lake pages in {args.cache}/: run python -m app.data_import.tpwd_fetch first.", file=sys.stderr)
        return 2

    Base.metadata.create_all(bind=engine)
    ramps = load_ramps(ramps_path)
    with SessionLocal() as db:
        summary = run(db, args.cache, ramps, args.state)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()

    placed = sum(summary.placed.values())
    print(f"{placed} TPWD lakes imported{' (dry run, nothing saved)' if args.dry_run else ''}:")
    for method, n in sorted(summary.placed.items()):
        print(f"  {n:4d}  {method}")
    print(f"  species links: {summary.species_links}")
    print(f"  boat ramps added: {summary.ramps_added} "
          f"(skipped as duplicates of existing access: {summary.ramps_skipped_duplicate}; "
          f"OpenStreetMap entrances replaced: {summary.osm_entrances_replaced})")
    print(f"  lakes with no TPWD ramp: {len(summary.lakes_without_ramps)}")
    if summary.unplaced:
        print(f"{len(summary.unplaced)} not placed (left out, not guessed):")
        for name, reason in summary.unplaced:
            print(f"  - {name}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
