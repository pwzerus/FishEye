"""California's official lake and fish data (CDFW), into the lakes we have.

See docs/adr/0034-california-official-data.md and docs/data-sources.md.
California's lakes came only from OpenStreetMap (unverified) and GBIF
records. CDFW publishes what makes a lake "verified" elsewhere:

- California Lakes (CC BY 4.0): every lake, reservoir and pond CDFW maps,
  each with a DFGWATERID, an official name, county and surface acres.
- Recent Stocked Waters, BIOS ds778 (CC BY 4.0): the waters CDFW stocked in
  the last three years, by DFGWATERID, as polygons in California Albers
  (EPSG:3310).
- The Fish Planting Schedule (CDFW site: public domain), from the page's own
  Export button: plantings of the past year and next two weeks, by
  DfgWaterId, as "Trout" or "Catfish".
- The 2026 Provisional Stocking Document (public domain): which trout or
  salmon species CDFW plans to plant where, by water name and county.
- High Mountain Lakes fish surveys, BIOS ds102 (CC BY 4.0): species found
  in Sierra lakes, by CaLakesID (a DFGWATERID).

WHAT IT DOES
------------
1. Matches each CDFW lake to an OpenStreetMap lake: the OSM lake's box (plus
   MATCH_MARGIN_M) holds CDFW's centre point and the names agree; or, when
   CDFW gives no name or the names differ, it is the only lake there and
   its box is 0.5-20x CDFW's acreage. Matched lakes keep their OSM name and
   gain dfg_water_id, CDFW's name (official_name, when different) and a
   CDFW profile (acres, county).
2. Adds named CDFW lakes OpenStreetMap doesn't have, at CDFW's centre point,
   as unverified lakes whose source is CDFW's layer. The private-name rules
   of the OSM import apply (docs/adr/0032).
3. A lake CDFW stocks (ds778 or the planting schedule) becomes verified.
4. Species evidence (provenance.add_evidence), each with our own sentence
   and a link: planting schedule (kind of fish and week), 2026 plan
   (species), ds102 (species and survey year; "fish not present" rows are
   never evidence). Generic "Trout" from the schedule is kept as "Trout"
   unless the 2026 stocking plan names the trout species for that lake.

Rivers, creeks and canals in CDFW's stocking data have no California Lakes
polygon and are counted as "not a lake", never forced onto one.

Run, from backend/:
    python -m app.data_import.cdfw_import --fetch           # network: fills cdfw_cache/
    python -m app.data_import.cdfw_import --osm ca_osm.json  # offline import
The fetch needs pyogrio, pyproj and pypdf (requirements-import.txt); the
import needs nothing beyond the app's own requirements.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_import.osm_waterbody_import import (
    Bounds,
    OsmLake,
    likely_private_by_name,
    merge_pieces,
    parse_elements,
    private_by_name,
)
from app.data_import.ga_wrd_import import lake_key, _names_match
from app.data_import.gbif_occurrence_import import lake_targets
from app.data_import.provenance import (
    USER_AGENT,
    add_evidence,
    link_dataset,
    prune_evidence,
    source_record,
    unlink_dataset,
)
from app.data_import.species_names import canonical
from app.models.waterbody import AgencyLakeProfile, SpeciesEvidence, State, Waterbody, WaterbodySource, WaterbodySpecies

AGENCY = "cdfw"
DEFAULT_CACHE = Path("cdfw_cache")
LAKES_LAYER = "https://services2.arcgis.com/Uq9r85Potqm3MfRV/arcgis/rest/services/CA_Lakes_wm/FeatureServer/0"
DS778_ZIP = "https://filelib.wildlife.ca.gov/Public/BDB/GIS/BIOS/Public_Datasets/700_799/ds778.zip"
DS102_ZIP = "https://filelib.wildlife.ca.gov/Public/BDB/GIS/BIOS/Public_Datasets/100_199/ds102.zip"
PLANTS_PAGE = "https://nrm.dfg.ca.gov/FishPlants/PublicPlantSearch"
PLANTS_EXPORT = "https://nrm.dfg.ca.gov/fishplants/publicplantsearch?Params.PlantTimeFrame=1&submit=Export"
PLAN_2026 = "https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=74004&inline"
DS102_PAGE = "https://wildlife.ca.gov/Conservation/Fishes/High-Mountain-Lakes"
FISHING_GUIDE = "https://wildlife.ca.gov/Fishing/Inland"

ACRES_TO_KM2 = 0.004046856
MATCH_MARGIN_M = 200.0
# An unnamed match must be about the right size: an OSM box is larger than
# its water, so the box may be up to 20x CDFW's surface area.
SIZE_RATIO = (0.5, 20.0)
# CDFW maps thousands of named alpine tarns; a lake smaller than this is
# added only when CDFW also says something about its fish.
MIN_NEW_LAKE_ACRES = 2.0
REQUEST_DELAY_S = 2.0
PAGE_SIZE = 2000

CA_COUNTIES = tuple(c.replace("_", " ") for c in (
    "Alameda Alpine Amador Butte Calaveras Colusa Contra_Costa Del_Norte El_Dorado Fresno Glenn Humboldt "
    "Imperial Inyo Kern Kings Lake Lassen Los_Angeles Madera Marin Mariposa Mendocino Merced Modoc Mono "
    "Monterey Napa Nevada Orange Placer Plumas Riverside Sacramento San_Benito San_Bernardino San_Diego "
    "San_Francisco San_Joaquin San_Luis_Obispo San_Mateo Santa_Barbara Santa_Clara Santa_Cruz Shasta Sierra "
    "Siskiyou Solano Sonoma Stanislaus Sutter Tehama Trinity Tulare Tuolumne Ventura Yolo Yuba"
).split())

PLAN_SPECIES = (
    "McCloud River Redband Trout", "Lahontan Cutthroat Trout", "California Golden Trout", "Eagle Lake Trout",
    "Rainbow Trout", "Brown Trout", "Brook Trout", "Kokanee Salmon", "Chinook Salmon", "Kokanee",
)
_PLAN_ROW = re.compile(r"^R\d\s")
_SIZES = re.compile(r"\b(Fingerling|Sub-catchable|Super-catchable|Catchable|Trophy)\b")


# --------------------------------------------------------------------------
# Fetch (network; run once, then import offline)
# --------------------------------------------------------------------------


def _get(client: Any, url: str, **params: Any) -> Any:
    for attempt in range(4):
        resp = client.get(url, params=params or None)
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            time.sleep(5 * 2**attempt)
            continue
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY_S)
        return resp
    raise RuntimeError(url)


def _ring_bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    pts = [p for ring in geometry.get("rings") or [] for p in ring]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(ys), min(xs), max(ys), max(xs)


def fetch_lakes(client: Any) -> list[dict[str, Any]]:
    """Every California Lakes feature, with a WGS84 bounding box."""
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        body = _get(
            client, f"{LAKES_LAYER}/query", where="1=1",
            outFields="DFGWATERID,NAME,GNIS_NAME,COUNTY,LAT_NAD83,LON_NAD83,sfc_acres,TYPE",
            outSR="4326", returnGeometry="true", maxAllowableOffset="0.0002", geometryPrecision="5",
            orderByFields="FID", resultOffset=str(offset), resultRecordCount=str(PAGE_SIZE), f="json",
        ).json()
        if "error" in body:
            raise RuntimeError(body["error"])
        page = body.get("features") or []
        for f in page:
            a = f.get("attributes") or {}
            box = _ring_bounds(f.get("geometry") or {})
            out.append({
                "id": a.get("DFGWATERID"),
                "name": (a.get("NAME") or "").strip() or (a.get("GNIS_NAME") or "").strip(),
                "county": (a.get("COUNTY") or "").strip(),
                "lat": a.get("LAT_NAD83"), "lng": a.get("LON_NAD83"),
                "acres": a.get("sfc_acres"), "type": (a.get("TYPE") or "").strip(),
                "bbox": box,
            })
        if not page or not body.get("exceededTransferLimit"):
            return out
        offset += len(page)


def _read_gdb(path: Path, with_centroids: bool) -> list[dict[str, Any]]:
    import warnings

    import pyogrio
    import shapely
    from pyproj import Transformer

    warnings.filterwarnings("ignore", message="Measured")
    meta, _fids, geometry, fields = pyogrio.raw.read(str(path), read_geometry=with_centroids)
    names = list(meta["fields"])
    rows = [
        {n: (v.item() if hasattr(v, "item") else v) for n, v in zip(names, values)}
        for values in zip(*fields)
    ]
    if with_centroids:
        to_wgs84 = Transformer.from_crs(meta["crs"], "EPSG:4326", always_xy=True)
        for row, wkb in zip(rows, geometry):
            c = shapely.from_wkb(wkb).centroid
            lng, lat = to_wgs84.transform(c.x, c.y)
            row["lat"], row["lng"] = round(lat, 6), round(lng, 6)
    return rows


def convert_ds778(zip_path: Path) -> list[dict[str, Any]]:
    gdb = _unzip(zip_path)
    return [
        {
            "dfg_water_id": int(r["DFGWATERID"]), "stocking_water_id": int(r["StockingWaterID"]),
            "counties": r["Counties"], "last_year": int(r["last_yr_stkd"]), "lat": r["lat"], "lng": r["lng"],
        }
        for r in _read_gdb(gdb, with_centroids=True)
    ]


def convert_ds102(zip_path: Path) -> list[dict[str, Any]]:
    """Species found per surveyed lake. Rows marked FishNotPresent are
    surveys that found no fish: kept out, never read as presence."""
    return ds102_rows(_read_gdb(_unzip(zip_path), with_centroids=False))


def ds102_rows(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in raw:
        if (r.get("FishNotPresent") or "").upper() == "Y" or not r.get("SpeciesName"):
            continue
        date = r.get("SurveyDate")
        year = int(str(date)[:4]) if date and str(date)[:4].isdigit() else None
        out.append({
            "calakes_id": int(r["CaLakesID"]) if r.get("CaLakesID") else None,
            "hml_id": r.get("HML_ID"), "species": r["SpeciesName"], "scientific_name": r.get("ScientificName"),
            "year": year, "survey_type": r.get("SurveyTypeDesc"),
            "lat": r.get("LatLong_Y"), "lng": r.get("LatLong_X"),
        })
    return out


def _unzip(zip_path: Path) -> Path:
    target = zip_path.with_suffix(".gdb")
    if not target.exists():
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(zip_path.parent)
    return target


def parse_plants_csv(text: str) -> list[dict[str, Any]]:
    rows = []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        try:
            week = datetime.strptime(r["WeekOfPlantStart"].split()[0], "%m/%d/%Y").date().isoformat()
            dfg = int(r["DfgWaterId"])
        except (KeyError, ValueError):
            continue
        rows.append({
            "week_start": week, "dfg_water_id": dfg, "stocking_water_id": int(r.get("StockingWaterID") or 0),
            "water_name": (r.get("WaterName") or "").strip(), "fish_type": (r.get("FishType") or "").strip(),
            "counties": (r.get("Counties") or "").strip(),
        })
    return rows


def parse_plan_text(text: str) -> list[dict[str, str]]:
    """Rows of the stocking plan's tables: region, county, water, species,
    release size. Lines that are not table rows (headings, the narrative
    pages, a month range wrapped onto the next line) are skipped."""
    rows = []
    counties = sorted(CA_COUNTIES, key=len, reverse=True)
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not _PLAN_ROW.match(line):
            continue
        region, rest = line.split(" ", 1)
        county = next((c for c in counties if rest.startswith(c + " ")), None)
        if county is None:
            continue
        rest = rest[len(county) + 1 :]
        hit = None
        for sp in PLAN_SPECIES:
            m = re.search(rf"\b{re.escape(sp)}\b", rest)
            if m and (hit is None or m.start() < hit.start()):
                hit = m
        if hit is None or hit.start() == 0:
            continue
        size = _SIZES.search(rest, hit.end())
        rows.append({
            "region": region, "county": county, "water": rest[: hit.start()].strip(),
            "species": hit.group(0), "size": size.group(1) if size else "",
        })
    return rows


def fetch_all(cache: Path) -> None:
    import httpx
    import pypdf

    cache.mkdir(parents=True, exist_ok=True)
    manifest_path = cache / "manifest.json"
    manifest: dict[str, str] = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    now = datetime.now(timezone.utc).isoformat()

    def save(name: str, rows: list[Any]) -> None:
        (cache / name).write_text(json.dumps(rows), encoding="utf-8")
        manifest[name] = now
        manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        print(f"{len(rows):6d} rows -> {cache / name}")

    with httpx.Client(timeout=120, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        save("ca_lakes.json", fetch_lakes(client))
        for url, name in ((DS778_ZIP, "ds778.zip"), (DS102_ZIP, "ds102.zip")):
            (cache / name).write_bytes(_get(client, url).content)
        save("ds778.json", convert_ds778(cache / "ds778.zip"))
        save("ds102.json", convert_ds102(cache / "ds102.zip"))
        save("fishplants.json", parse_plants_csv(_get(client, PLANTS_EXPORT).text))
        (cache / "plan2026.pdf").write_bytes(_get(client, PLAN_2026).content)
    reader = pypdf.PdfReader(str(cache / "plan2026.pdf"))
    save("plan2026.json", parse_plan_text("\n".join(p.extract_text() or "" for p in reader.pages)))


# --------------------------------------------------------------------------
# Matching (pure)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CdfwLake:
    id: int
    name: str
    county: str
    latitude: float
    longitude: float
    acres: float
    bounds: Bounds | None


def parse_lakes(rows: list[dict[str, Any]]) -> list[CdfwLake]:
    out = []
    for r in rows:
        if r.get("id") is None or r.get("lat") is None or r.get("lng") is None:
            continue
        b = r.get("bbox")
        out.append(CdfwLake(
            int(r["id"]), (r.get("name") or "").strip(), r.get("county") or "", float(r["lat"]), float(r["lng"]),
            float(r.get("acres") or 0.0), Bounds(*b) if b else None,
        ))
    return out


def name_from_schedule(lakes: list[CdfwLake], plants: list[dict[str, Any]]) -> list[CdfwLake]:
    """CDFW's lake layer leaves some stocked ponds unnamed; its planting
    schedule names the same DFGWATERID ("Carrville Pond")."""
    names = {r["dfg_water_id"]: r["water_name"] for r in plants if r.get("water_name")}
    return [replace(c, name=names[c.id]) if not c.name and c.id in names else c for c in lakes]


class _Grid:
    CELL = 0.1

    def __init__(self, lakes: list[OsmLake]) -> None:
        self.cells: dict[tuple[int, int], list[OsmLake]] = defaultdict(list)
        for lake in lakes:
            b = lake.bounds.expanded(MATCH_MARGIN_M)
            for cy in range(math.floor(b.south / self.CELL), math.floor(b.north / self.CELL) + 1):
                for cx in range(math.floor(b.west / self.CELL), math.floor(b.east / self.CELL) + 1):
                    self.cells[(cy, cx)].append(lake)

    def containing(self, lat: float, lng: float) -> list[OsmLake]:
        cell = (math.floor(lat / self.CELL), math.floor(lng / self.CELL))
        return [lake for lake in self.cells.get(cell, []) if lake.bounds.expanded(MATCH_MARGIN_M).contains(lat, lng)]


def match_lake(cdfw: CdfwLake, grid: _Grid) -> tuple[OsmLake | None, str]:
    """(OSM lake, how) for one CDFW lake; how is "name", "overlap", or why not."""
    here = grid.containing(cdfw.latitude, cdfw.longitude)
    if not here:
        return None, "no_osm_lake"
    if cdfw.name:
        named = [lake for lake in here if _names_match(lake.name, cdfw.name)]
        if named:
            return min(named, key=lambda lake: lake.bounds.area()), "name"
    if len(here) == 1 and cdfw.acres > 0:
        ratio = here[0].bounds.area_km2() / (cdfw.acres * ACRES_TO_KM2)
        if SIZE_RATIO[0] <= ratio <= SIZE_RATIO[1] and not here[0].likely_private:
            return here[0], "overlap"
        return None, "size_mismatch"
    return None, "ambiguous" if len(here) > 1 else "no_acreage"


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------


@dataclass
class ImportSummary:
    cdfw_lakes: int = 0
    matched: Counter[str] = field(default_factory=Counter)
    unmatched: Counter[str] = field(default_factory=Counter)
    lakes_added: int = 0
    lakes_verified: int = 0
    stocked_not_a_lake: int = 0
    stocked_lakes_unplaced: list[str] = field(default_factory=list)
    plan_rows: int = 0
    plan_unmatched: list[str] = field(default_factory=list)
    evidence_new: Counter[str] = field(default_factory=Counter)
    evidence_total: Counter[str] = field(default_factory=Counter)
    evidence_pruned: int = 0
    ds102_skipped: Counter[str] = field(default_factory=Counter)
    lakes_with_species: int = 0
    merged_into_osm: int = 0


def _absorb(db: Session, gone: Waterbody, into: Waterbody) -> None:
    """Move a CDFW-added row's evidence and dataset credits to the
    OpenStreetMap row of the same lake, then delete it."""
    have = {link.species_id for link in into.species_links}
    for e in list(gone.species_evidence):
        e.waterbody_id = into.id
    for link in list(gone.species_links):
        if link.species_id not in have:
            into.species_links.append(WaterbodySpecies(
                species_id=link.species_id, confidence=link.confidence, evidence=link.evidence,
                source_url=link.source_url, observed_at=link.observed_at,
            ))
    for ds in list(gone.dataset_links):
        if db.get(WaterbodySource, (into.id, ds.source_record_id)) is None:
            db.add(WaterbodySource(waterbody_id=into.id, source_record_id=ds.source_record_id,
                                   source_key=ds.source_key, url=ds.url))
    if gone.data_tier == "verified":
        into.data_tier = "verified"
    if into.agency_profile is None and gone.agency_profile is not None:
        gone.agency_profile.waterbody_id = into.id
    db.flush()
    db.expire(gone)
    db.delete(gone)
    db.flush()


def _lake_url(dfg_id: int) -> str:
    return f"{LAKES_LAYER}/query?where=DFGWATERID%3D{dfg_id}&outFields=*&f=html"


def _plants_url(stocking_id: int | None) -> str:
    return f"{PLANTS_PAGE}?Params.StockingWaterID={stocking_id}" if stocking_id else PLANTS_PAGE


def _stocked_summary(year: int) -> str:
    return (
        f"California Department of Fish and Wildlife stocked fish here in {year}. FishEye has no official "
        "access information for this lake yet: check with the lake's operator before you go."
    )


def run(db: Session, osm_payload: dict[str, Any], cache: Path, now: datetime | None = None) -> ImportSummary:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    state = db.scalar(select(State).where(State.code == "CA"))
    if state is None:
        raise ValueError("no California lakes in the database; run the OpenStreetMap import for CA first")
    load = lambda name: json.loads((cache / name).read_text(encoding="utf-8"))  # noqa: E731
    manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8")) if (cache / "manifest.json").exists() else {}

    def fetched(name: str) -> datetime:
        stamp = manifest.get(name)
        return datetime.fromisoformat(stamp).astimezone(timezone.utc).replace(tzinfo=None) if stamp else now

    summary = ImportSummary()
    plants = load("fishplants.json")
    cdfw_lakes = name_from_schedule(parse_lakes(load("ca_lakes.json")), plants)
    summary.cdfw_lakes = len(cdfw_lakes)
    by_id = {c.id: c for c in cdfw_lakes}
    ds778 = load("ds778.json")
    plan = load("plan2026.json")
    ds102 = load("ds102.json")
    stocked_ids = {r["dfg_water_id"] for r in ds778} | {r["dfg_water_id"] for r in plants}
    plan_ids = _plan_ids(plan, cdfw_lakes, summary)
    has_fish = stocked_ids | {i for ids in plan_ids.values() for i in ids} | {r["calakes_id"] for r in ds102 if r.get("calakes_id")}

    osm_lakes = merge_pieces(parse_elements(osm_payload)[0])
    targets = lake_targets(db, state, osm_lakes)
    rows_by_id = {wb.id: wb for wb in db.scalars(select(Waterbody).where(Waterbody.state_id == state.id))}
    by_dfg_column = {wb.dfg_water_id: wb for wb in rows_by_id.values() if wb.dfg_water_id is not None}
    grid = _Grid(osm_lakes)

    rec_lakes = source_record(db, "cdfw_ca_lakes", fetched("ca_lakes.json"))
    wb_for: dict[int, Waterbody] = {}  # DFGWATERID -> lake
    for c in sorted(cdfw_lakes, key=lambda c: -c.acres):
        if not c.name and c.id not in has_fish:
            continue  # an unnamed pond CDFW says nothing else about
        lake, how = match_lake(c, grid)
        wb = rows_by_id.get(targets.get(lake.osm_ref, -1)) if lake is not None else None
        if wb is None and lake is not None:
            how = "osm_lake_not_in_database"
        earlier = by_dfg_column.get(c.id)
        if wb is not None and earlier is not None and earlier is not wb and earlier.osm_ref is None:
            # An earlier run added this lake from CDFW's layer; OpenStreetMap
            # has it now. Keep the OpenStreetMap row, fold ours into it.
            _absorb(db, earlier, into=wb)
            rows_by_id.pop(earlier.id, None)
            by_dfg_column[c.id] = wb
            summary.merged_into_osm += 1
        if wb is None:
            wb = earlier
            if wb is not None:
                how = "added_earlier"
        if wb is None:
            summary.unmatched[how] += 1
            if c.name and not private_by_name(c.name) and (c.acres >= MIN_NEW_LAKE_ACRES or c.id in has_fish):
                wb = _add_lake(db, state, c, now)
                rows_by_id[wb.id] = wb
                by_dfg_column[c.id] = wb
                summary.lakes_added += 1
            else:
                continue
        else:
            summary.matched[how] += 1
        wb_for[c.id] = wb
        link_dataset(db, wb, rec_lakes, str(c.id), _lake_url(c.id))
        if wb.dfg_water_id is None or (wb.dfg_water_id != c.id and c.acres > by_id.get(wb.dfg_water_id, c).acres):
            wb.dfg_water_id = c.id
        if c.name and c.name != wb.name and wb.dfg_water_id == c.id:
            wb.official_name = c.name[:128]
        _write_profile(db, wb, c, rec_lakes)

    # 3. Stocked lakes become verified.
    last_year: dict[int, int] = {}
    for r in ds778:
        last_year[r["dfg_water_id"]] = max(last_year.get(r["dfg_water_id"], 0), r["last_year"])
    for r in plants:
        last_year[r["dfg_water_id"]] = max(last_year.get(r["dfg_water_id"], 0), int(r["week_start"][:4]))
    verified_now: set[int] = set()
    for dfg_id, year in sorted(last_year.items()):
        if dfg_id not in by_id:
            summary.stocked_not_a_lake += 1
            continue
        wb = wb_for.get(dfg_id)
        if wb is None:
            summary.stocked_lakes_unplaced.append(f"{by_id[dfg_id].name or 'unnamed'} (DFGWATERID {dfg_id})")
            continue
        if wb.id in verified_now:
            continue
        verified_now.add(wb.id)
        if wb.data_tier != "verified":
            summary.lakes_verified += 1
            wb.data_tier = "verified"
        if wb.agency_profile is not None and wb.agency_profile.agency == AGENCY:
            # A lake whose name looked private is stocked by the state for
            # public fishing: the name rule's warning no longer applies.
            if wb.public_access_status == "likely_private":
                wb.public_access_status = "unknown"
            wb.access_summary = _stocked_summary(year)
            stocking_id = next((r["stocking_water_id"] for r in ds778 if r["dfg_water_id"] == dfg_id), None)
            stocking_id = stocking_id or next((r["stocking_water_id"] for r in plants if r["dfg_water_id"] == dfg_id), None)
            wb.agency_profile.page_url = _plants_url(stocking_id)
            wb.agency_profile.access_page_url = FISHING_GUIDE
        wb.source_updated_at = now

    # 4. Species evidence.
    # Every source is pruned, also one that matched nothing on this run.
    kept: dict[str, set[str]] = {s: set() for s in ("cdfw_plan_2026", "cdfw_ds102", "cdfw_plants")}
    # Lake id -> trout species CDFW's 2026 stocking plan names for it. Only
    # the plan says what CDFW stocks; a survey finding brook trout is not a
    # planting of them, so surveys never decide what a "Trout" planting was.
    planned_trout: dict[int, set[str]] = defaultdict(set)
    # One fact per lake, species and source: CDFW maps some lakes as several
    # polygons, and each can carry the same plan row or survey. The first
    # polygon's id keys it; the others' rows from earlier runs are pruned.
    written: set[tuple[str, int, str]] = set()

    def first(source: str, wb: Waterbody, sp: str) -> bool:
        if (source, wb.id, sp) in written:
            return False
        written.add((source, wb.id, sp))
        return True

    rec_plan = source_record(db, "cdfw_plan_2026", fetched("plan2026.json"))
    for i, r in enumerate(plan):
        ids = plan_ids.get(i, frozenset())
        lakes_here = {wb_for[d].id: (d, wb_for[d]) for d in sorted(ids) if d in wb_for}
        if len(lakes_here) != 1:
            if len(lakes_here) > 1:
                summary.plan_unmatched.append(f"{r['water']} ({r['county']}) - ambiguous")
            continue
        dfg_id, wb = next(iter(lakes_here.values()))
        name = canonical(r["species"])
        if name is None:
            continue
        key = f"{dfg_id}:{name[0]}"
        if key in kept["cdfw_plan_2026"] or not first("cdfw_plan_2026", wb, name[0]):
            continue
        kept["cdfw_plan_2026"].add(key)
        planned_trout[wb.id].add(name[0])
        strain = f" ({r['species']})" if r["species"] != name[0] and r["species"] != "Kokanee" else ""
        _count(summary, "cdfw_plan_2026", add_evidence(
            db, wb, name[0], source="cdfw_plan_2026", source_key=key, kind="stocking_plan", year=2026,
            evidence=f"CDFW's 2026 stocking plan lists {name[0]}{strain} for this water.",
            source_url=PLAN_2026, record=rec_plan, confidence="confirmed", now=now,
        ))

    rec_102 = source_record(db, "cdfw_ds102", fetched("ds102.json"))
    latest_102: dict[tuple[int, str], int | None] = {}
    for r in ds102:
        name = canonical(r["species"])
        if name is None:
            summary.ds102_skipped["species not mapped"] += 1
            continue
        if r.get("calakes_id") not in wb_for:
            summary.ds102_skipped["lake not matched"] += 1
            continue
        k = (r["calakes_id"], name[0])
        if k not in latest_102 or (r.get("year") or 0) > (latest_102[k] or 0):
            latest_102[k] = r.get("year")
    for (dfg_id, sp), year in sorted(latest_102.items(), key=lambda kv: (-(kv[1] or 0), kv[0])):
        wb = wb_for[dfg_id]
        if not first("cdfw_ds102", wb, sp):
            continue  # the newest survey of this lake already said so
        key = f"{dfg_id}:{sp}"
        kept["cdfw_ds102"].add(key)
        when = f" in {year}" if year else ""
        _count(summary, "cdfw_ds102", add_evidence(
            db, wb, sp, source="cdfw_ds102", source_key=key, kind="survey", year=year,
            evidence=f"CDFW's High Mountain Lakes survey recorded {sp} here{when}.",
            source_url=_lake_url(dfg_id), record=rec_102, confidence="confirmed", now=now,
        ))

    rec_plants = source_record(db, "cdfw_plants", fetched("fishplants.json"))
    latest_plant: dict[tuple[int, str], dict[str, Any]] = {}
    for r in plants:
        if r["dfg_water_id"] not in wb_for or not r["fish_type"]:
            continue
        k = (r["dfg_water_id"], r["fish_type"])
        if k not in latest_plant or r["week_start"] > latest_plant[k]["week_start"]:
            latest_plant[k] = r
    trout_like = {"Rainbow Trout", "Brown Trout", "Brook Trout", "Golden Trout", "Lahontan Cutthroat Trout",
                  "Cutthroat Trout", "Lake Trout"}
    # Newest planting first: it is the one kept when two polygons share a lake.
    for (dfg_id, fish_type), r in sorted(latest_plant.items(), key=lambda kv: (kv[1]["week_start"], kv[0]), reverse=True):
        wb = wb_for[dfg_id]
        week = datetime.fromisoformat(r["week_start"])
        when = f"the week of {week.strftime('%B')} {week.day}, {week.year}"
        named = sorted(planned_trout[wb.id] & trout_like) if fish_type == "Trout" else []
        species_list = named or [canonical(fish_type)[0] if canonical(fish_type) else fish_type]
        for sp in species_list:
            if not first("cdfw_plants", wb, sp):
                continue
            key = f"{dfg_id}:{fish_type}:{sp}"
            kept["cdfw_plants"].add(key)
            kind_word = fish_type.lower()
            _count(summary, "cdfw_plants", add_evidence(
                db, wb, sp, source="cdfw_plants", source_key=key, kind="stocking", year=week.year,
                evidence=(
                    f"CDFW's fish planting schedule lists {kind_word} planted here {when}"
                    + (f"; CDFW's 2026 stocking plan for this water names {sp}." if named else
                       "; the schedule does not name the species." if fish_type in ("Trout", "Catfish") else ".")
                ),
                source_url=_plants_url(r.get("stocking_water_id")), record=rec_plants,
                confidence="confirmed", now=now,
            ))

    # ds778 names no species: it is what makes a lake verified (above), and
    # is credited on the lake itself.
    rec_778 = source_record(db, "cdfw_ds778", fetched("ds778.json"))
    credited: set[int] = set()
    for r in ds778:
        wb = wb_for.get(r["dfg_water_id"])
        if wb is not None and wb.id not in credited:
            credited.add(wb.id)
            link_dataset(db, wb, rec_778, str(r["dfg_water_id"]), DS778_ZIP)
    unlink_dataset(db, rec_778, credited)
    unlink_dataset(db, rec_lakes, {wb.id for wb in wb_for.values()})

    for source, keys in kept.items():
        summary.evidence_pruned += prune_evidence(db, source, keys)
        summary.evidence_total[source] = len(keys)
    cdfw_lakes_with_species: set[int] = set()
    for source in kept:
        for e in db.scalars(select(SpeciesEvidence).where(SpeciesEvidence.source == source)):
            cdfw_lakes_with_species.add(e.waterbody_id)
    summary.lakes_with_species = len(cdfw_lakes_with_species)
    db.flush()
    return summary


def _count(summary: ImportSummary, source: str, new: bool) -> None:
    if new:
        summary.evidence_new[source] += 1


def _plan_ids(plan: list[dict[str, str]], lakes: list[CdfwLake], summary: ImportSummary) -> dict[int, frozenset[int]]:
    """Plan row index -> DFGWATERID, by name within the row's county. Only a
    single same-named lake in that county counts; rivers and creeks have no
    lake to match and are listed as unmatched."""
    by_county: dict[str, list[CdfwLake]] = defaultdict(list)
    for c in lakes:
        if c.name:
            for county in c.county.split(","):
                by_county[county.strip().lower()].append(c)
    out: dict[int, int] = {}
    summary.plan_rows = len(plan)
    unmatched: set[str] = set()
    for i, r in enumerate(plan):
        water = re.sub(r"\((lower|upper)\)", r"\1", r["water"], flags=re.I)
        words = sorted(lake_key(water).split())
        in_county = by_county.get(r["county"].lower(), [])
        # Same words in any order ("Angora Lake Lower" = "Lower Angora Lake"),
        # then one name inside the other, both within the county; then the
        # same words anywhere, if only one lake in the state has them (a
        # reservoir CDFW files under a neighbouring county).
        hits = [c for c in in_county if sorted(lake_key(c.name).split()) == words]
        if not hits:
            hits = [c for c in in_county if _names_match(c.name, water)]
        if not hits:
            statewide = [c for c in lakes if c.name and sorted(lake_key(c.name).split()) == words]
            hits = statewide if len({c.id for c in statewide}) == 1 else []
        ids = {c.id for c in hits}
        # Several ids may still be one lake (CDFW maps some as several
        # polygons of one name); run() decides once it knows the lakes.
        if ids:
            out[i] = frozenset(ids)
        else:
            unmatched.add(f"{r['water']} ({r['county']})")
    summary.plan_unmatched = sorted(unmatched)
    return out


def _add_lake(db: Session, state: State, c: CdfwLake, now: datetime) -> Waterbody:
    likely = likely_private_by_name(c.name)
    wb = Waterbody(
        state_id=state.id, name=c.name[:128], latitude=c.latitude, longitude=c.longitude,
        access_summary=(
            "Mapped by the California Department of Fish and Wildlife (California Lakes). FishEye has no "
            "verified information about public access here yet: check before you go."
        ),
        source_url=_lake_url(c.id), source_updated_at=now, field_tested=False,
        public_access_status="likely_private" if likely else "unknown", data_tier="osm",
        osm_ref=None, water_type="pond" if c.acres < 10 else "lake",
        extent_km2=(c.bounds.area_km2() if c.bounds else c.acres * ACRES_TO_KM2), dfg_water_id=c.id,
    )
    db.add(wb)
    db.flush()
    return wb


def _write_profile(db: Session, wb: Waterbody, c: CdfwLake, rec: Any) -> None:
    profile = wb.agency_profile
    if profile is not None and profile.agency != AGENCY:
        return
    if profile is None:
        existing = db.scalar(select(AgencyLakeProfile).where(
            AgencyLakeProfile.agency == AGENCY, AgencyLakeProfile.agency_lake_id == str(c.id)))
        profile = existing or AgencyLakeProfile(agency=AGENCY, agency_lake_id=str(c.id), placement="osm_name")
        profile.waterbody_id = wb.id
        if existing is None:
            db.add(profile)
        wb.agency_profile = profile
    if profile.agency_lake_id != str(c.id) and c.acres <= (profile.surface_acres or 0):
        return  # a larger CDFW polygon of the same lake already wrote it
    profile.agency_lake_id = str(c.id)
    profile.agency_name = (c.name or wb.name)[:128]
    profile.page_url = profile.page_url or _lake_url(c.id)
    if not profile.page_url.startswith(PLANTS_PAGE):
        profile.page_url = _lake_url(c.id)
    profile.location = f"{c.county} County" if c.county and "," not in c.county else (c.county or None)
    profile.surface_acres = int(round(c.acres)) if c.acres else None
    profile.predominant_species = []
    profile.ratings = []
    profile.placement = "osm_name" if wb.osm_ref else "cdfw"
    profile.retrieved_at = rec.retrieved_at
    db.flush()


def main(argv: list[str] | None = None) -> int:
    from app.db.session import SessionLocal, engine
    from app.db.upgrades import prepare_database

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--osm", type=Path, default=Path("ca_osm.json"), help="the California OpenStreetMap file (default ca_osm.json)")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--fetch", action="store_true", help="download CDFW's data into --cache, then stop")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.fetch:
        fetch_all(args.cache)
        return 0
    missing = [n for n in ("ca_lakes.json", "ds778.json", "ds102.json", "fishplants.json", "plan2026.json")
               if not (args.cache / n).exists()]
    if missing:
        print(f"Missing in {args.cache}/: {', '.join(missing)}. Run with --fetch first.", file=sys.stderr)
        return 2
    osm_payload = json.loads(args.osm.read_text(encoding="utf-8"))
    prepare_database(engine)
    with SessionLocal() as db:
        summary = run(db, osm_payload, args.cache)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()

    print(f"CDFW California Lakes read: {summary.cdfw_lakes}")
    print("  matched to OpenStreetMap lakes: " + ", ".join(f"{k}={v}" for k, v in sorted(summary.matched.items())))
    print("  not matched: " + ", ".join(f"{k}={v}" for k, v in sorted(summary.unmatched.items())))
    print(f"  named lakes added from CDFW's layer: {summary.lakes_added}")
    if summary.merged_into_osm:
        print(f"  lakes added by an earlier run, now on OpenStreetMap and merged into it: {summary.merged_into_osm}")
    print(f"lakes newly verified (stocked by CDFW): {summary.lakes_verified}")
    print(f"stocked waters that are not lakes (streams, canals): {summary.stocked_not_a_lake}")
    if summary.stocked_lakes_unplaced:
        print(f"stocked lakes not placed ({len(summary.stocked_lakes_unplaced)}):")
        for s in summary.stocked_lakes_unplaced:
            print(f"  - {s}")
    print(f"2026 plan rows: {summary.plan_rows}, water names not matched to one lake: {len(summary.plan_unmatched)}")
    print("species evidence (new / total): " + ", ".join(
        f"{k} {summary.evidence_new[k]}/{summary.evidence_total[k]}" for k in sorted(summary.evidence_total)))
    print(f"  stale evidence removed: {summary.evidence_pruned}")
    print("  ds102 rows skipped: " + ", ".join(f"{k}={v}" for k, v in summary.ds102_skipped.items()))
    print(f"lakes with a species list from CDFW: {summary.lakes_with_species}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
