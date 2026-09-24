"""Statewide lake layer from OpenStreetMap (docs/adr/0010-statewide-osm-layer.md).

The hand-verified lakes (seed_tx_lakes.py, tpwd_lake_survey_scraper.py) are
the only ones this app knows anything *about*. This importer answers a
narrower question for everywhere else: does a lake exist here at all, and
does OpenStreetMap know of a public boat ramp or fishing pier on it?

WHAT IT WRITES
--------------
- Named lakes and reservoirs as Waterbody rows with data_tier="osm" and
  public_access_status="unknown". Never any species: OSM has no fish
  data, and PRD constraint 1 forbids inventing it.
- Slipways, fishing spots and fishing piers inside those lakes as
  AccessPoint rows with public_status="osm_reported". The scoring engine
  only ranks "confirmed_public" (services/recommendations.py), so these are
  shown to users with a "verify before you go" label and never scored.

WHAT IT DELIBERATELY LEAVES OUT
-------------------------------
- Anything tagged access=private/no/customers — PRD constraint 4: never
  show private land as a public entrance.
- Unnamed water: overwhelmingly stock tanks and backyard/HOA ponds on
  private land in Texas. (Named ponds ARE imported — a city-park pond is
  often the best beginner spot there is — but stored with
  water_type="pond", which the UI uses to warn that ponds are often on
  private land.)
- Named water smaller than MIN_LAKE_EXTENT_M across (MIN_POND_EXTENT_M for
  ponds): decorative water features and the like.
- Access points that fall inside no imported lake (river and coastal
  ramps). This is a freshwater lake app; rivers are a separate project.
- OSM access points on lakes that are already verified: the official
  confirmed_public data stays the only access data shown for those.

Verified lakes are never overwritten. An OSM lake that matches one (same
core name, the verified lake's centre inside the OSM lake's extent) only
has its osm_ref recorded on the verified row, so re-imports stay idempotent
and never create a second "Lake Somerville" next to ours.

Location is approximate by design: a lake is plotted at its OSM centre,
and an access point is matched to a lake by bounding box, not shoreline
geometry (no PostGIS yet — ADR 0001).

Run (needs network access to the Overpass API):
    python -m app.data_import.osm_waterbody_import --state TX
    python -m app.data_import.osm_waterbody_import --state TX --save-raw tx_osm.json
    python -m app.data_import.osm_waterbody_import --state TX --from-file tx_osm.json   # offline re-run
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.models.waterbody import AccessPoint, SpeciesOccurrence, State, Waterbody

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT_SECONDS = 400.0

# States this importer knows how to create a State row for. Adding one is a
# one-line change; the query itself is keyed on the ISO 3166-2 code.
SUPPORTED_STATES: dict[str, tuple[str, str]] = {
    "TX": ("Texas", "https://tpwd.texas.gov"),
}

MIN_LAKE_EXTENT_M = 200.0
# Ponds are small by definition; a named city-park fishing pond can be well
# under 200 m across. Below ~50 m it's a fountain or garden feature.
MIN_POND_EXTENT_M = 50.0
# How far outside a lake's bounding box an access point may sit and still be
# matched to it (ramps are mapped on the shore, which can fall just outside
# the water polygon's bbox).
ACCESS_MATCH_MARGIN_M = 300.0
# How far outside an OSM lake's extent a verified lake's centre may sit and
# still count as the same lake.
VERIFIED_MATCH_MARGIN_M = 5000.0

EXCLUDED_ACCESS_VALUES = {"private", "no", "customers", "agricultural", "forestry", "delivery"}

OSM_LAKE_SUMMARY = (
    "Mapped in OpenStreetMap, a community-edited map. FishMate has no verified "
    "information about the fish or public access here yet. Check with Texas Parks "
    "and Wildlife before you go."
)
OSM_POND_SUMMARY = (
    "Mapped in OpenStreetMap, a community-edited map. Many ponds are on private "
    "land (ranches, neighborhoods, golf courses): make sure this one is open to "
    "the public before you fish it. FishMate has no verified information about "
    "the fish here."
)


@dataclass(frozen=True)
class Bounds:
    south: float
    west: float
    north: float
    east: float

    def expanded(self, margin_m: float) -> Bounds:
        dlat = margin_m / 111_320.0
        mid_lat = math.radians((self.south + self.north) / 2)
        dlng = margin_m / (111_320.0 * max(math.cos(mid_lat), 0.01))
        return Bounds(self.south - dlat, self.west - dlng, self.north + dlat, self.east + dlng)

    def contains(self, lat: float, lng: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lng <= self.east

    def extent_m(self) -> float:
        """Diagonal length of the box in metres (equirectangular, fine at lake scale)."""
        mid_lat = math.radians((self.south + self.north) / 2)
        dy = (self.north - self.south) * 111_320.0
        dx = (self.east - self.west) * 111_320.0 * math.cos(mid_lat)
        return math.hypot(dx, dy)

    def area(self) -> float:
        return (self.north - self.south) * (self.east - self.west)


@dataclass(frozen=True)
class OsmLake:
    osm_ref: str
    name: str
    latitude: float
    longitude: float
    bounds: Bounds
    water_type: str = "lake"  # lake | reservoir | pond


@dataclass(frozen=True)
class OsmAccess:
    osm_ref: str
    name: str | None
    latitude: float
    longitude: float
    access_type: str  # boat_ramp | pier | bank


@dataclass
class ImportSummary:
    lakes_created: int = 0
    lakes_updated: int = 0
    lakes_linked_to_verified: int = 0
    lakes_replaced_by_verified: int = 0
    access_created: int = 0
    access_updated: int = 0
    access_unmatched: int = 0
    skipped: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Query + fetch
# --------------------------------------------------------------------------


def build_overpass_query(state_code: str) -> str:
    iso = f"US-{state_code.upper()}"
    return f"""[out:json][timeout:360];
area["ISO3166-2"="{iso}"][admin_level=4]->.st;
(
  way["natural"="water"]["water"~"^(lake|reservoir|pond)$"]["name"](area.st);
  relation["natural"="water"]["water"~"^(lake|reservoir|pond)$"]["name"](area.st);
  way["landuse"="reservoir"]["name"](area.st);
  relation["landuse"="reservoir"]["name"](area.st);
);
out tags bb;
(
  node["leisure"="slipway"](area.st);
  way["leisure"="slipway"](area.st);
  node["leisure"="fishing"](area.st);
  way["leisure"="fishing"](area.st);
  node["man_made"="pier"]["fishing"~"^(yes|designated)$"](area.st);
  way["man_made"="pier"]["fishing"~"^(yes|designated)$"](area.st);
);
out tags center;
"""


def fetch_overpass(query: str) -> dict[str, Any]:
    settings = get_settings()
    headers = {"User-Agent": settings.nominatim_user_agent}
    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
        resp = client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        return payload


# --------------------------------------------------------------------------
# Parse (pure — everything below until upsert is unit-testable offline)
# --------------------------------------------------------------------------


def _position(el: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in el and "lon" in el:
        return float(el["lat"]), float(el["lon"])
    center = el.get("center")
    if center:
        return float(center["lat"]), float(center["lon"])
    # Lakes are requested with `out bb` only (Overpass allows one geometry
    # modifier per out statement); Overpass's own "center" is exactly this
    # bounding-box midpoint anyway.
    bounds = el.get("bounds")
    if bounds:
        return (
            (float(bounds["minlat"]) + float(bounds["maxlat"])) / 2,
            (float(bounds["minlon"]) + float(bounds["maxlon"])) / 2,
        )
    return None


def _is_excluded_access(tags: dict[str, str]) -> bool:
    return tags.get("access", "").strip().lower() in EXCLUDED_ACCESS_VALUES


def _access_type(tags: dict[str, str]) -> str:
    if tags.get("leisure") == "slipway":
        return "boat_ramp"
    if tags.get("man_made") == "pier":
        return "pier"
    return "bank"


def parse_elements(payload: dict[str, Any]) -> tuple[list[OsmLake], list[OsmAccess], dict[str, int]]:
    lakes: list[OsmLake] = []
    access: list[OsmAccess] = []
    skipped: dict[str, int] = {}

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    seen: set[str] = set()
    for el in payload.get("elements", []):
        ref = f"{el.get('type')}/{el.get('id')}"
        if ref in seen:
            continue
        seen.add(ref)
        tags: dict[str, str] = el.get("tags", {})
        pos = _position(el)
        if pos is None:
            skip("no_position")
            continue

        is_lake = tags.get("natural") == "water" or tags.get("landuse") == "reservoir"
        if is_lake:
            water_type = (
                "reservoir" if tags.get("landuse") == "reservoir" else tags.get("water", "lake")
            )
            if water_type not in {"lake", "reservoir", "pond"}:
                skip("other_water")
                continue
            name = tags.get("name", "").strip()
            if not name:
                skip("unnamed_lake")
                continue
            if _is_excluded_access(tags):
                skip("private_lake")
                continue
            b = el.get("bounds")
            if not b:
                skip("no_bounds")
                continue
            bounds = Bounds(
                float(b["minlat"]), float(b["minlon"]), float(b["maxlat"]), float(b["maxlon"])
            )
            min_extent = MIN_POND_EXTENT_M if water_type == "pond" else MIN_LAKE_EXTENT_M
            if bounds.extent_m() < min_extent:
                skip("too_small")
                continue
            lakes.append(OsmLake(ref, name, pos[0], pos[1], bounds, water_type))
        else:
            if _is_excluded_access(tags):
                skip("private_access")
                continue
            access.append(
                OsmAccess(
                    osm_ref=ref,
                    name=(tags.get("name") or "").strip() or None,
                    latitude=pos[0],
                    longitude=pos[1],
                    access_type=_access_type(tags),
                )
            )
    return lakes, access, skipped


def assign_access_to_lakes(
    lakes: list[OsmLake], access: list[OsmAccess]
) -> tuple[dict[str, list[OsmAccess]], int]:
    """Each access point goes to the *smallest* lake whose (slightly
    expanded) bounding box contains it — smallest, because a cove's own
    named arm and the reservoir around it can both contain the same ramp,
    and the tighter box is the better guess."""
    expanded = [(lake, lake.bounds.expanded(ACCESS_MATCH_MARGIN_M)) for lake in lakes]
    by_lake: dict[str, list[OsmAccess]] = {}
    unmatched = 0
    for point in access:
        containing = [
            (lake, box) for lake, box in expanded if box.contains(point.latitude, point.longitude)
        ]
        if not containing:
            unmatched += 1
            continue
        lake, _ = min(containing, key=lambda pair: pair[0].bounds.area())
        by_lake.setdefault(lake.osm_ref, []).append(point)
    return by_lake, unmatched


_NAME_NOISE = re.compile(r"\b(lake|reservoir|the|of)\b")


def core_name(name: str) -> str:
    """'Lake Somerville' and 'Somerville Lake' and 'Somerville Reservoir'
    all reduce to 'somerville'."""
    lowered = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    return " ".join(_NAME_NOISE.sub(" ", lowered).split())


def _find_verified_twin(lake: OsmLake, verified: list[Waterbody]) -> Waterbody | None:
    """Two ways an OSM lake counts as one of ours:

    1. Same core name, and our centre within VERIFIED_MATCH_MARGIN_M of the
       OSM lake's box ("Somerville Lake" / "Lake Somerville").
    2. One name's words are a subset of the other's, and our centre lies
       inside the OSM lake's own box, no margin. Official and common names
       often differ by a qualifier: TPWD's "Fayette County Reservoir" is
       OSM's "Lake Fayette". The containment requirement is what keeps this
       from matching an unrelated "Fork Creek Pond" near Lake Fork. Checked
       against the full Texas import: it matches only real twins.
    """
    key = core_name(lake.name)
    key_words = set(key.split())
    loose = lake.bounds.expanded(VERIFIED_MATCH_MARGIN_M)
    for wb in verified:
        wb_key = core_name(wb.name)
        if wb_key == key and loose.contains(wb.latitude, wb.longitude):
            return wb
    for wb in verified:
        wb_words = set(core_name(wb.name).split())
        if (
            key_words
            and wb_words
            and (key_words <= wb_words or wb_words <= key_words)
            and lake.bounds.contains(wb.latitude, wb.longitude)
        ):
            return wb
    return None


# --------------------------------------------------------------------------
# Upsert
# --------------------------------------------------------------------------


def _get_or_create_state(db: Session, state_code: str) -> State:
    code = state_code.upper()
    state = db.scalar(select(State).where(State.code == code))
    if state is not None:
        return state
    name, url = SUPPORTED_STATES[code]
    state = State(name=name, code=code, official_source_url=url)
    db.add(state)
    db.flush()
    return state


def upsert(
    db: Session,
    state_code: str,
    lakes: list[OsmLake],
    access_by_lake: dict[str, list[OsmAccess]],
    now: datetime | None = None,
) -> ImportSummary:
    now = now or datetime.now(timezone.utc)
    summary = ImportSummary()
    state = _get_or_create_state(db, state_code)

    verified = list(
        db.scalars(
            select(Waterbody).where(
                Waterbody.state_id == state.id, Waterbody.data_tier == "verified"
            )
        ).all()
    )
    existing_by_ref = {
        wb.osm_ref: wb
        for wb in db.scalars(select(Waterbody).where(Waterbody.osm_ref.is_not(None))).all()
    }
    access_by_ref = {
        ap.osm_ref: ap
        for ap in db.scalars(select(AccessPoint).where(AccessPoint.osm_ref.is_not(None))).all()
    }

    for lake in lakes:
        existing = existing_by_ref.get(lake.osm_ref)

        if existing is not None and existing.data_tier == "verified":
            # Already linked on a previous run — never touch verified data.
            summary.lakes_linked_to_verified += 1
            continue

        twin = _find_verified_twin(lake, verified)
        if twin is not None:
            if existing is not None:
                # Imported as OSM-only on an earlier run, and a verified
                # lake (e.g. added later by the TPWD scraper under a
                # slightly different name) now covers it. Drop the OSM
                # duplicate; its osm_reported access points go with it.
                for ref, ap in list(access_by_ref.items()):
                    if ap.waterbody_id == existing.id:
                        del access_by_ref[ref]
                # Species records (GBIF) found in the duplicate's extent
                # belong to the verified lake now.
                db.execute(
                    update(SpeciesOccurrence)
                    .where(SpeciesOccurrence.waterbody_id == existing.id)
                    .values(waterbody_id=twin.id)
                )
                db.expire(existing, ["occurrences"])
                db.delete(existing)
                db.flush()
                summary.lakes_replaced_by_verified += 1
            # Link only once: OSM sometimes maps one lake as several
            # elements (a way plus a relation, or named arms), and
            # re-pointing the link on every match would churn it run to run.
            if twin.osm_ref is None:
                twin.osm_ref = lake.osm_ref
                existing_by_ref[lake.osm_ref] = twin
            summary.lakes_linked_to_verified += 1
            continue

        if existing is None:
            wb = Waterbody(
                state_id=state.id,
                name=lake.name[:128],
                latitude=lake.latitude,
                longitude=lake.longitude,
                access_summary=OSM_POND_SUMMARY if lake.water_type == "pond" else OSM_LAKE_SUMMARY,
                source_url=f"https://www.openstreetmap.org/{lake.osm_ref}",
                source_updated_at=now,
                field_tested=False,
                public_access_status="unknown",
                data_tier="osm",
                osm_ref=lake.osm_ref,
                water_type=lake.water_type,
            )
            db.add(wb)
            db.flush()
            existing_by_ref[lake.osm_ref] = wb
            summary.lakes_created += 1
        else:
            wb = existing
            wb.name = lake.name[:128]
            wb.latitude = lake.latitude
            wb.longitude = lake.longitude
            wb.water_type = lake.water_type
            wb.access_summary = (
                OSM_POND_SUMMARY if lake.water_type == "pond" else OSM_LAKE_SUMMARY
            )
            wb.source_updated_at = now
            summary.lakes_updated += 1

        for point in access_by_lake.get(lake.osm_ref, []):
            label = {"boat_ramp": "Boat ramp", "pier": "Fishing pier", "bank": "Fishing spot"}[
                point.access_type
            ]
            name = (point.name or f"{label} (OpenStreetMap)")[:128]
            found = access_by_ref.get(point.osm_ref)
            if found is None:
                ap = AccessPoint(
                    waterbody_id=wb.id,
                    name=name,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    access_type=point.access_type,
                    public_status="osm_reported",
                    parking=False,
                    osm_ref=point.osm_ref,
                )
                db.add(ap)
                access_by_ref[point.osm_ref] = ap
                summary.access_created += 1
            else:
                ap = found
                ap.waterbody_id = wb.id
                ap.name = name
                ap.latitude = point.latitude
                ap.longitude = point.longitude
                ap.access_type = point.access_type
                summary.access_updated += 1

    db.flush()
    return summary


def run(state_code: str, payload: dict[str, Any], db: Session) -> ImportSummary:
    lakes, access, skipped = parse_elements(payload)
    access_by_lake, unmatched = assign_access_to_lakes(lakes, access)
    summary = upsert(db, state_code, lakes, access_by_lake)
    summary.access_unmatched = unmatched
    summary.skipped = skipped
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", default="TX", help="two-letter state code (supported: %s)" % ", ".join(SUPPORTED_STATES))
    parser.add_argument("--from-file", type=Path, help="use a previously saved Overpass response instead of fetching")
    parser.add_argument("--save-raw", type=Path, help="also save the raw Overpass response here")
    args = parser.parse_args(argv)

    code = args.state.upper()
    if code not in SUPPORTED_STATES:
        print(f"unsupported state {code!r}; add it to SUPPORTED_STATES first", file=sys.stderr)
        return 2

    if args.from_file:
        payload = json.loads(args.from_file.read_text(encoding="utf-8"))
    else:
        print(f"Querying Overpass for {code} lakes and access points (this can take a few minutes)...")
        payload = fetch_overpass(build_overpass_query(code))
        if args.save_raw:
            args.save_raw.write_text(json.dumps(payload), encoding="utf-8")
            print(f"raw response saved to {args.save_raw}")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        summary = run(code, payload, db)
        db.commit()
    finally:
        db.close()

    print(
        f"lakes: {summary.lakes_created} created, {summary.lakes_updated} updated, "
        f"{summary.lakes_linked_to_verified} matched to verified lakes"
        + (
            f", {summary.lakes_replaced_by_verified} earlier duplicates of verified lakes removed"
            if summary.lakes_replaced_by_verified
            else ""
        )
    )
    print(
        f"access points: {summary.access_created} created, {summary.access_updated} updated, "
        f"{summary.access_unmatched} not inside any imported lake (skipped)"
    )
    if summary.skipped:
        print("filtered out: " + ", ".join(f"{k}={v}" for k, v in sorted(summary.skipped.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
