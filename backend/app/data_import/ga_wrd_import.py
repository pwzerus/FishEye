"""Georgia WRD's public water-access sites and fish attractors.

See docs/adr/0033-georgia-wrd-access-and-attractors.md. Georgia's Wildlife
Resources Division publishes two map layers (ArcGIS feature services behind
its fishing forecasts and its "Interactive Map of Fishing Areas"):

- WRD_Water_Access_Points: ~900 public boat ramps, piers and bank-fishing
  sites, each naming its lake and flagging which fish are found there;
- Fish_Attractors_View: ~1,800 brush piles, PVC trees, stake beds and the
  like that WRD has sunk in reservoirs and public fishing areas.

Only facts are taken (where a site is, what kind it is, which species WRD
lists, where an attractor sits and when it was placed). None of WRD's text,
photos or maps is copied; each lake links back to WRD.

WHAT THE IMPORT DOES
--------------------
For each open, public access site on a lake (rivers, trout streams and the
coast are not lakes on this map):

1. finds its lake: an OpenStreetMap lake near the site whose name matches
   WRD's lake name or site name; failing that, the only lake whose extent
   holds the site. Anything else is listed in the summary, never guessed. A
   site with no OpenStreetMap lake near it at all puts its lake on the map
   at WRD's sites ("sites"), as the TPWD import does at its ramps.
2. adds the site as a confirmed public access point, unless the lake
   already has a confirmed one within DUPLICATE_ACCESS_M. An OpenStreetMap
   entrance that close is the same place, now confirmed: it is replaced by
   WRD's. Farther OpenStreetMap entrances stay, labelled unverified.
3. links the guide species WRD lists at the lake's sites (confirmed).
4. marks the lake verified and open, and stores WRD's profile of it (its
   name for the lake, acreage, county, species list, and the fishing
   forecast link for the 31 lakes WRD writes one for).

Attractors are matched to the lake whose extent holds them (a matching name
first), and replaced wholesale on every run.

Run (on a machine with network access; the fetch is two small downloads):
    python -m app.data_import.ga_wrd_import --fetch --osm ga_osm.json
    python -m app.data_import.ga_wrd_import --osm ga_osm.json            # re-import from ga_wrd_cache/
    python -m app.data_import.ga_wrd_import --osm ga_osm.json --dry-run
Run the OpenStreetMap import for Georgia first; this one builds on its lakes.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.data_import.gbif_occurrence_import import lake_targets
from app.data_import.osm_waterbody_import import OsmLake, core_name, merge_pieces, parse_elements
from app.data_import.species_names import species_list
from app.data_import.tpwd_lake_survey_scraper import upsert_species
from app.data_import.tpwd_statewide_import import km_between, search_radius_km
from app.models.waterbody import AccessPoint, AgencyLakeProfile, FishAttractor, State, Waterbody, WaterbodySpecies

AGENCY = "ga_wrd"
SERVICE = "https://services6.arcgis.com/9QlSLDqa0P1cHLhu/arcgis/rest/services"
ACCESS_LAYER = f"{SERVICE}/WRD_Water_Access_Points/FeatureServer/0"
ATTRACTOR_LAYER = f"{SERVICE}/Fish_Attractors_View/FeatureServer/0"
# WRD's "Interactive Map of Fishing Areas", linked from its Angler Resources page.
MAP_PAGE = "https://georgiawildlife.com/locations/fishing"
FORECASTS_PAGE = "https://georgiawildlife.com/fishing-forecasts"
DEFAULT_CACHE = Path("ga_wrd_cache")
ACCESS_FILE = "access_points.json"
ATTRACTOR_FILE = "fish_attractors.json"
PAGE_SIZE = 1000  # both layers' maxRecordCount
REQUEST_DELAY_S = 1.0

# A site counts as the same place as an existing access point within this
# (same rule as the TPWD import).
DUPLICATE_ACCESS_M = 150.0
# How far outside an OpenStreetMap lake's box a shore site may sit.
SITE_MARGIN_M = 300.0
LAKE_TYPES = frozenset({"Major Reservoir", "Small Impoundment"})
ACRES_TO_KM2 = 0.004046856

# WRD species field -> its fish, as WRD names them (the lake's profile lists
# them as species_names.species_list() renders them) and the guide species
# it is (linked as confirmed).
SPECIES_FIELDS: dict[str, tuple[str, str | None]] = {
    "Largemouth": ("Largemouth bass", "Largemouth Bass"),
    "Smallmouth": ("Smallmouth bass", "Smallmouth Bass"),
    "ShoalBass": ("Shoal bass", None),
    "SpotBass": ("Spotted bass", "Spotted Bass"),
    "SuwBass": ("Suwannee bass", None),
    "RedeyeBass": ("Redeye bass", None),
    "ChattBass": ("Chattahoochee bass", None),
    "Bartrams": ("Bartram's bass", None),
    "Tallapoosa": ("Tallapoosa bass", None),
    "AltamahaBass": ("Altamaha bass", None),
    "WhiteBass": ("White bass", "White Bass"),
    "StripBass": ("Striped bass", "Striped Bass"),
    "HybStrpBas": ("Hybrid striped bass", "Hybrid Striped Bass"),
    "YellowBass": ("Yellow bass", None),
    "ChannelCat": ("Channel catfish", "Channel Catfish"),
    "Flathead": ("Flathead catfish", "Flathead Catfish"),
    "BlueCat": ("Blue catfish", "Blue Catfish"),
    "WhiteCat": ("White catfish", None),
    "YellowBull": ("Yellow bullhead", None),
    "BrownBull": ("Brown bullhead", None),
    "WhiteCrap": ("White crappie", "White Crappie"),
    "BlackCrap": ("Black crappie", "Black Crappie"),
    "Bluegill": ("Bluegill", "Bluegill"),
    "RedearSun": ("Redear sunfish", "Redear Sunfish"),
    "Redbreast": ("Redbreast sunfish", None),
    "SpottedSun": ("Spotted sunfish", None),
    "Flier": ("Flier", None),
    "Warmouth": ("Warmouth", None),
    "RockBass": ("Rock bass", None),
    "ShadowBass": ("Shadow bass", None),
    "RbwTrout": ("Rainbow trout", "Rainbow Trout"),
    "BrownTrout": ("Brown trout", None),
    "BrookTrout": ("Brook trout", None),
    "Walleye": ("Walleye", None),
    "Yell_Perch": ("Yellow perch", None),
    "ChainPick": ("Chain pickerel", None),
    "RedfinPick": ("Redfin pickerel", None),
    "FreshDrum": ("Freshwater drum", "Freshwater Drum"),
    "CommonCarp": ("Common carp", "Common Carp"),
    "SM_Buffalo": ("Smallmouth buffalo", None),
    "LN_Gar": ("Longnose gar", None),
    "Bowfin": ("Bowfin", None),
    "AmerShad": ("American shad", None),
    "HickShad": ("Hickory shad", None),
}

# WRD's fishing forecasts (FORECASTS_PAGE), by the lake names WRD may use
# for each. Keys are lake_key() of a name.
_FORECAST_URLS: dict[tuple[str, ...], str] = {
    ("allatoona",): "1c82b6c519b44e858ddd028d1bbf3453",
    ("andrews",): "fc5805e439f4450f8357c034d18eceda",
    ("bartletts ferry", "harding"): "7e01e1a18ced4ec9a6f87c82f2272ab0",
    ("big haynes", "big haynes creek", "randy poynter", "big haynes randy poynter"): "78ba13fb45f9473da55fd158373c13d5",
    ("blackshear",): "264b93843af042e7a7151299976b8c6e",
    ("blue ridge",): "32c7542965e541eca756d51bae4eb1ec",
    ("burton",): "ba62c611af9844d48ae9076c313ae1be",
    ("carters",): "195c66b92a4042ffa4b37ed41fff81e2",
    ("chatuge",): "181a1ddac0604430907644e0c6ba03a8",
    ("chehaw",): "3e6c6f8606064eabba4227c72ea5d26b",
    ("clarks hill", "j strom thurmond", "thurmond", "strom thurmond"): "8442bc9ff43f4b5c96ad11acb9ee3ac6",
    ("goat rock",): "1350b65f93654c819cbc27c959e35abe",
    ("hamburg",): "89e71b9a4123430c8caaaf53b2625bfc",
    ("hartwell",): "ea1839811a2b4c6e83df03bc51b81f7a",
    ("high falls",): "47808a182728419d987c5e973c398abc",
    ("jackson",): "6f492807b19c45c08bd86f7cc8498acf",
    ("juliette",): "9abb6dfa0f8041aba3a8896d428010ea",
    ("lanier", "sidney lanier"): "bf90dbefc6d34795a96fdc0181e746d9",
    ("nottely",): "f138a47e2c4d4cab9a51b3c32058af5d",
    ("oconee",): "e7d44ce4bc054728b6ab131b2b8d98e9",
    ("oliver",): "6e0b57e6dd444e8a97a6e315dcf32d38",
    ("rabun",): "1b23a8aeaa3646ebae427378d828a19c",
    ("richard b russell", "russell", "richard russell"): "bdbfa9d911fe417dacfdd056bbf6783f",
    ("seed",): "a224d457ae9f419282d85a76a5b553b4",
    ("seminole",): "6b329ae238da4c948f36418c9d1ced25",
    ("sinclair",): "5c863ec0b0534e998d3217fd13ac1a62",
    ("tobesofkee",): "bb30deb0d39b442bb5c72f5cbfd1b0ce",
    ("tugalo", "tugaloo"): "6f69ad0336374853ac63dd480d781d0b",
    ("varner",): "78ccc5ee4bd84be6b65c6e3e9ec900b4",
    ("walter f george", "walter george", "eufaula"): "22343e9a63f04e5e95fd0dc8abc2d3af",
    ("west point",): "a019d774757344c5adfc91a3dd5f73db",
    ("yonah",): "e1bd005e7d554223ac7604387456e713",
}
FORECASTS: dict[str, str] = {
    key: f"https://storymaps.arcgis.com/stories/{story}" for keys, story in _FORECAST_URLS.items() for key in keys
}
# Every forecast lake is a major reservoir or at least ~200 acres (Lake
# Hamburg, the smallest, is 225): a pond that happens to be called "Jackson"
# or "Seed" must not be handed Lake Jackson's forecast.
FORECAST_MIN_ACRES = 200

_GENERIC_KEYS = frozenset({"", "pond", "lake", "mill pond", "county", "park", "wetland"})


def lake_key(name: str) -> str:
    """core_name, with apostrophes dropped first: "Carter's" -> "carters"."""
    return core_name(name.replace("'", "").replace("’", ""))


def _names_match(a: str, b: str) -> bool:
    """Same lake key, or one key's words all inside the other's
    ("buncombe" in "a h stephens sp buncombe"). Generic keys never match."""
    ka, kb = lake_key(a), lake_key(b)
    if ka in _GENERIC_KEYS or kb in _GENERIC_KEYS:
        return False
    if ka == kb:
        return True
    wa, wb = set(ka.split()), set(kb.split())
    return bool(wa and wb) and (wa <= wb or wb <= wa)


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------


def fetch_layer(client: httpx.Client, layer_url: str, where: str, order_by: str) -> list[dict[str, Any]]:
    """Every feature of a layer, a page at a time, as WGS84 points."""
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": "*",
            "outSR": "4326",
            "orderByFields": order_by,
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE_SIZE),
            "f": "json",
        }
        for attempt in range(4):
            resp = client.get(f"{layer_url}/query", params=params)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2**attempt)
                continue
            resp.raise_for_status()
            break
        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"{layer_url}: {body['error']}")
        page = body.get("features") or []
        features += page
        time.sleep(REQUEST_DELAY_S)
        if not page or not body.get("exceededTransferLimit"):
            return features
        offset += len(page)


def fetch_all(cache: Path, client: httpx.Client) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    for filename, layer, where, order in (
        (ACCESS_FILE, ACCESS_LAYER, "1=1", "FID"),
        (ATTRACTOR_FILE, ATTRACTOR_LAYER, "activity='attractor'", "objectid"),
    ):
        features = fetch_layer(client, layer, where, order)
        (cache / filename).write_text(json.dumps({"fetched_at": now, "source": layer, "features": features}), encoding="utf-8")
        print(f"{len(features)} features saved to {cache / filename}")


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Site:
    wrd_id: int
    name: str
    waterbody: str
    water_type: str
    county: str
    latitude: float
    longitude: float
    acres: float
    access_type: str  # boat_ramp | pier | bank
    parking: bool
    species: tuple[str, ...]  # WRD's species fields flagged "Y"


@dataclass(frozen=True)
class Attractor:
    record_id: str
    latitude: float
    longitude: float
    attractor_type: str
    units: int | None
    depth_ft: float | None
    placed_year: int | None
    waterbody: str


def _yes(v: Any) -> bool:
    return str(v or "").strip().upper() == "Y"


def _point(feature: dict[str, Any], lat_field: str, lng_field: str) -> tuple[float, float] | None:
    """The feature's own geometry (always present in WRD's layers, in WGS84
    because the query asks for it), else its latitude/longitude fields. The
    fields alone are not enough: WRD leaves a few at 0 or empty."""
    a = feature.get("attributes") or {}
    g = feature.get("geometry") or {}
    for raw_lat, raw_lng in ((g.get("y"), g.get("x")), (a.get(lat_field), a.get(lng_field))):
        try:
            lat, lng = float(raw_lat), float(raw_lng)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if -90 <= lat <= 90 and -180 <= lng <= 180 and not (lat == 0 and lng == 0):
            return lat, lng
    return None


def parse_sites(features: list[dict[str, Any]]) -> tuple[list[Site], Counter[str]]:
    """Open, public lake sites, and a count of what was left out and why."""
    sites: list[Site] = []
    skipped: Counter[str] = Counter()
    for f in features:
        a = f.get("attributes") or {}
        if (a.get("Draw") or "").strip() != "Public":
            skipped["not listed as public"] += 1
            continue
        status = (a.get("Status") or "").strip()
        if status != "Open":
            skipped["closed" if status == "Closed" else "status unknown"] += 1
            continue
        water_type = (a.get("WaterType") or "").strip()
        if water_type not in LAKE_TYPES:
            skipped["river, stream or coast"] += 1
            continue
        pos = _point(f, "Latitude", "Longitude")
        if pos is None:
            skipped["no coordinates"] += 1
            continue
        if _yes(a.get("Ramp")):
            access_type = "boat_ramp"
        elif _yes(a.get("PierFish")):
            access_type = "pier"
        else:
            access_type = "bank"
        sites.append(
            Site(
                wrd_id=int(a["FID"]),  # FID is unique; WRD's ID column is not (0 on many rows)
                name=(a.get("Name") or "").strip() or "Public access",
                waterbody=(a.get("Waterbody") or "").strip(),
                water_type=water_type,
                county=(a.get("County") or "").strip(),
                latitude=pos[0],
                longitude=pos[1],
                acres=float(a.get("Acres") or 0),
                access_type=access_type,
                parking=_yes(a.get("Parking")),
                species=tuple(k for k in SPECIES_FIELDS if _yes(a.get(k))),
            )
        )
    return sites, skipped


def parse_attractors(features: list[dict[str, Any]]) -> list[Attractor]:
    out: list[Attractor] = []
    for f in features:
        a = f.get("attributes") or {}
        if a.get("activity") != "attractor":
            continue
        pos = _point(f, "latitude", "longitude")
        rid = a.get("globalid") or a.get("objectid")
        if pos is None or rid is None:
            continue
        placed = a.get("placement_date")
        year = datetime.fromtimestamp(placed / 1000, tz=timezone.utc).year if isinstance(placed, (int, float)) else None
        kind = (a.get("attractor_name") or "").strip()
        if kind in ("", "Other"):
            kind = (a.get("attractor_code_other") or "").strip() or "Other"
        depth = a.get("deep")
        out.append(
            Attractor(
                record_id=str(rid)[:64],
                latitude=pos[0],
                longitude=pos[1],
                attractor_type=kind[:64],
                units=int(a["units_no"]) if a.get("units_no") else None,
                depth_ft=float(depth) if depth else None,  # 0 means not recorded
                placed_year=year,
                waterbody=(a.get("waterbody") or "").strip()[:128],
            )
        )
    return out


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

CELL_DEG = 0.05


class BoxIndex:
    """OpenStreetMap lakes by grid cell of their (margin-expanded) box."""

    def __init__(self, lakes: list[OsmLake], margin_m: float) -> None:
        self.lakes = lakes
        self.boxes = [lake.bounds.expanded(margin_m) for lake in lakes]
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        for i, b in enumerate(self.boxes):
            for cy in range(math.floor(b.south / CELL_DEG), math.floor(b.north / CELL_DEG) + 1):
                for cx in range(math.floor(b.west / CELL_DEG), math.floor(b.east / CELL_DEG) + 1):
                    self.cells[(cy, cx)].append(i)

    def near(self, lat: float, lng: float) -> list[OsmLake]:
        cell = (math.floor(lat / CELL_DEG), math.floor(lng / CELL_DEG))
        return [self.lakes[i] for i in self.cells.get(cell, []) if self.boxes[i].contains(lat, lng)]


def match_site(site: Site, index: BoxIndex) -> tuple[OsmLake | None, str]:
    """(lake, method). method is osm_name | osm_position | none | ambiguous."""
    near = index.near(site.latitude, site.longitude)
    if not near:
        return None, "none"
    named = [lake for lake in near if _names_match(lake.name, site.waterbody) or _names_match(lake.name, site.name)]
    if named:
        return min(named, key=lambda lake: lake.bounds.area()), "osm_name"
    holding = [lake for lake in near if lake.bounds.contains(site.latitude, site.longitude)]
    if len(holding) == 1 and _plausibly_same(holding[0], site):
        return holding[0], "osm_position"
    return None, "ambiguous"


def _plausibly_same(lake: OsmLake, site: Site) -> bool:
    """A lake matched by position alone (the names differ) must not look
    private, and its box must be about the size WRD gives: a box is never
    much smaller than the water, and rarely more than ~20 times larger."""
    if lake.likely_private:
        return False
    if site.acres <= 0:
        return True
    ratio = lake.bounds.area_km2() / (site.acres * ACRES_TO_KM2)
    return 0.5 <= ratio <= 20


def match_attractor(att: Attractor, index: BoxIndex) -> OsmLake | None:
    holding = [lake for lake in index.near(att.latitude, att.longitude) if lake.bounds.contains(att.latitude, att.longitude)]
    if not holding:
        return None
    named = [lake for lake in holding if att.waterbody and _names_match(lake.name, att.waterbody)]
    return min(named or holding, key=lambda lake: lake.bounds.area())


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------


@dataclass
class ImportSummary:
    sites_read: int = 0
    sites_skipped: dict[str, int] = field(default_factory=dict)
    lakes: dict[str, int] = field(default_factory=lambda: defaultdict(int))  # placement -> lakes
    sites_unplaced: list[tuple[str, str]] = field(default_factory=list)
    access_added: int = 0
    access_updated: int = 0
    access_skipped_duplicate: int = 0
    osm_entrances_confirmed: int = 0
    species_links: int = 0
    forecasts_linked: int = 0
    attractors_read: int = 0
    attractors_saved: int = 0
    attractor_lakes: int = 0
    attractors_not_in_a_lake: int = 0


def forecast_for(sites: list[Site]) -> str | None:
    for s in sites:
        if s.water_type == "Major Reservoir" or s.acres >= FORECAST_MIN_ACRES:
            url = FORECASTS.get(lake_key(s.waterbody))
            if url:
                return url
    return None


def _most_common(values: list[str]) -> str:
    values = [v for v in values if v]
    return Counter(values).most_common(1)[0][0] if values else ""


def _write_access(db: Session, wb: Waterbody, sites: list[Site], summary: ImportSummary) -> None:
    existing = list(wb.access_points)
    for site in sites:
        ref = f"{AGENCY}/{site.wrd_id}"
        mine = next((ap for ap in existing if ap.osm_ref == ref), None)
        if mine is None:
            near = [
                ap for ap in existing
                if km_between(ap.latitude, ap.longitude, site.latitude, site.longitude) * 1000 < DUPLICATE_ACCESS_M
            ]
            if any(ap.public_status == "confirmed_public" for ap in near):
                summary.access_skipped_duplicate += 1
                continue
            for ap in near:  # OpenStreetMap's guess at this place, now confirmed
                wb.access_points.remove(ap)
                existing.remove(ap)
                summary.osm_entrances_confirmed += 1
            db.flush()
            mine = AccessPoint(osm_ref=ref, public_status="confirmed_public")
            wb.access_points.append(mine)
            existing.append(mine)
            summary.access_added += 1
        else:
            summary.access_updated += 1
        mine.name = site.name[:128]
        mine.latitude = site.latitude
        mine.longitude = site.longitude
        mine.access_type = site.access_type
        mine.parking = site.parking
        mine.public_status = "confirmed_public"
    db.flush()


def _write_species(db: Session, wb: Waterbody, sites: list[Site], source_url: str, retrieved_at: datetime) -> int:
    """Replace this lake's WRD-sourced species links; other sources' stay."""
    wrd_urls = {MAP_PAGE, *FORECASTS.values()}
    for link in list(wb.species_links):
        if link.source_url in wrd_urls:
            wb.species_links.remove(link)
    db.flush()
    have = {link.species.common_name for link in wb.species_links}
    at: dict[str, list[str]] = defaultdict(list)
    for site in sites:
        for f in site.species:
            guide = SPECIES_FIELDS[f][1]
            if guide and site.name not in at[guide]:
                at[guide].append(site.name)
    written = 0
    for guide, names in at.items():
        if guide in have:
            continue
        shown = "; ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
        species = upsert_species(db, guide)
        wb.species_links.append(
            WaterbodySpecies(
                species=species,
                confidence="confirmed",
                evidence=f"Georgia WRD's list of public fishing access sites names {SPECIES_FIELDS_BY_GUIDE[guide]} at {shown}.",
                source_url=source_url,
                observed_at=retrieved_at,
            )
        )
        written += 1
    db.flush()
    return written


SPECIES_FIELDS_BY_GUIDE = {guide: label.lower() for label, guide in SPECIES_FIELDS.values() if guide}


def _write_profile(db: Session, wb: Waterbody, sites: list[Site], method: str, forecast: str | None, retrieved_at: datetime) -> None:
    profile = wb.agency_profile
    if profile is not None and profile.agency != AGENCY:
        return  # another agency's profile (TPWD) is not ours to replace
    if profile is None:
        profile = AgencyLakeProfile(agency=AGENCY, agency_lake_id=f"site-{min(s.wrd_id for s in sites)}", placement=method)
        wb.agency_profile = profile
    labels: list[str] = []
    for s in sites:
        for f in s.species:
            if SPECIES_FIELDS[f][0] not in labels:
                labels.append(SPECIES_FIELDS[f][0])
    counties = sorted({s.county for s in sites if s.county})
    acres = max((s.acres for s in sites), default=0)
    profile.agency_name = _most_common([s.waterbody for s in sites]) or wb.name
    profile.page_url = forecast or MAP_PAGE
    profile.access_page_url = MAP_PAGE if forecast else None
    profile.location = (", ".join(counties) + (" County" if len(counties) == 1 else " Counties")) if counties else None
    profile.surface_acres = int(acres) if acres > 0 else None
    profile.predominant_species = species_list(labels)
    profile.ratings = []
    if profile.placement != "sites":  # a lake this import placed keeps that
        profile.placement = method
    profile.retrieved_at = retrieved_at
    db.flush()


def _access_summary(n: int) -> str:
    return (
        f"Georgia WRD lists {n} public access site{'s' if n != 1 else ''} on this lake "
        "(boat ramps, piers or bank fishing). Fees and hours are on WRD's fishing map."
    )


def _find_named_lake(by_key: dict[str, list[Waterbody]], key: str, lat: float, lng: float, radius_km: float) -> Waterbody | None:
    """A lake already in the database under this name, near these sites: one
    an earlier run placed at WRD's sites, or an OpenStreetMap lake whose box
    stops short of the shore the sites are on. Nearest wins."""
    near = [wb for wb in by_key.get(key, []) if km_between(wb.latitude, wb.longitude, lat, lng) <= radius_km]
    return min(near, key=lambda wb: km_between(wb.latitude, wb.longitude, lat, lng)) if near else None


def import_sites(
    db: Session, state: State, lakes: list[OsmLake], sites: list[Site], retrieved_at: datetime, summary: ImportSummary
) -> None:
    index = BoxIndex(lakes, SITE_MARGIN_M)
    targets = lake_targets(db, state, lakes)
    by_lake: dict[int, list[Site]] = defaultdict(list)
    method_of: dict[int, str] = {}
    loose: dict[str, list[Site]] = defaultdict(list)  # no lake near at all

    for site in sites:
        lake, method = match_site(site, index)
        if lake is None:
            if method == "none":
                loose[lake_key(site.waterbody or site.name)].append(site)
            else:
                summary.sites_unplaced.append((site.name, "several lakes here and none has its name"))
            continue
        wb_id = targets.get(lake.osm_ref)
        if wb_id is None:
            summary.sites_unplaced.append((site.name, f"its lake ({lake.name}) is not in the database"))
            continue
        by_lake[wb_id].append(site)
        # A name match anywhere on the lake beats a position-only one.
        if method_of.get(wb_id) != "osm_name":
            method_of[wb_id] = method

    by_key: dict[str, list[Waterbody]] = defaultdict(list)
    if loose:
        for wb in db.scalars(select(Waterbody).where(Waterbody.state_id == state.id)):
            by_key[lake_key(wb.name)].append(wb)
    groups: list[tuple[Waterbody, list[Site], str]] = []
    for wb_id, group in by_lake.items():
        row = db.get(Waterbody, wb_id)
        if row is not None:
            groups.append((row, group, method_of[wb_id]))
    for key, group in loose.items():
        if key in _GENERIC_KEYS:
            for s in group:
                summary.sites_unplaced.append((s.name, "no lake on the map here, and no lake name to place one under"))
            continue
        lat = statistics.median(s.latitude for s in group)
        lng = statistics.median(s.longitude for s in group)
        radius = search_radius_km(int(max(s.acres for s in group)))
        kept = [s for s in group if km_between(s.latitude, s.longitude, lat, lng) <= radius]
        for s in group:
            if s not in kept:
                summary.sites_unplaced.append((s.name, "far from the other sites with its lake name"))
        found = _find_named_lake(by_key, key, lat, lng, radius)
        method = "sites"
        if found is not None and found.id in by_lake:
            next(g for g in groups if g[0].id == found.id)[1].extend(kept)
            continue
        if found is not None:
            lake_row = found
            if not (found.agency_profile and found.agency_profile.placement == "sites"):
                method = "osm_name"
        else:
            name = _most_common([s.waterbody for s in kept]) or kept[0].name
            lake_row = Waterbody(
                state_id=state.id, name=name[:128], latitude=lat, longitude=lng, access_summary="",
                source_url=MAP_PAGE, source_updated_at=retrieved_at, field_tested=False,
                public_access_status="open", data_tier="verified",
                water_type="reservoir" if any(s.water_type == "Major Reservoir" for s in kept) else "lake",
                extent_km2=max(s.acres for s in kept) * ACRES_TO_KM2,
            )
            db.add(lake_row)
            db.flush()
            by_key[key].append(lake_row)
        groups.append((lake_row, kept, method))

    for wb, group, method in groups:
        forecast = forecast_for(group)
        if forecast:
            summary.forecasts_linked += 1
        if wb.public_access_status == "closed":
            summary.sites_unplaced += [(s.name, f"{wb.name} is closed to the public") for s in group]
            continue
        wb.data_tier = "verified"
        wb.public_access_status = "open"  # WRD lists open public access here
        wb.source_url = forecast or MAP_PAGE
        wb.source_updated_at = retrieved_at
        _write_access(db, wb, group, summary)
        summary.species_links += _write_species(db, wb, group, forecast or MAP_PAGE, retrieved_at)
        _write_profile(db, wb, group, method, forecast, retrieved_at)
        wb.access_summary = _access_summary(sum(1 for ap in wb.access_points if ap.public_status == "confirmed_public"))
        summary.lakes[method] += 1
    db.flush()


# An attractor outside every mapped lake outline (a PFA pond too small for
# OpenStreetMap, or a lake plotted only at its access sites) joins the lake
# WRD files it under, if one of that name is within this far; failing that,
# the nearest lake this import placed at WRD's sites within NEAR_SITES_KM.
NAMED_LAKE_KM = 8.0
NEAR_SITES_KM = 2.5


def _lake_for_unmapped_attractor(
    att: Attractor, named: dict[str, list[Waterbody]], sites_lakes: list[Waterbody]
) -> Waterbody | None:
    def near(wbs: list[Waterbody], km: float) -> Waterbody | None:
        close = [(km_between(wb.latitude, wb.longitude, att.latitude, att.longitude), wb) for wb in wbs]
        close = [c for c in close if c[0] <= km]
        return min(close, key=lambda c: c[0])[1] if close else None

    key = lake_key(att.waterbody)
    if key and key not in _GENERIC_KEYS:
        candidates = [wb for k, wbs in named.items() if k == key or _names_match(k, att.waterbody) for wb in wbs]
        found = near(candidates, NAMED_LAKE_KM)
        if found is not None:
            return found
    return near(sites_lakes, NEAR_SITES_KM)


def import_attractors(
    db: Session, state: State, lakes: list[OsmLake], attractors: list[Attractor], now: datetime, summary: ImportSummary
) -> None:
    index = BoxIndex(lakes, 0.0)
    targets = lake_targets(db, state, lakes)
    state_lakes = select(Waterbody.id).where(Waterbody.state_id == state.id)
    db.execute(delete(FishAttractor).where(FishAttractor.source == AGENCY, FishAttractor.waterbody_id.in_(state_lakes)))
    rows = list(db.scalars(select(Waterbody).where(Waterbody.state_id == state.id)))
    named: dict[str, list[Waterbody]] = defaultdict(list)
    for wb in rows:
        named[lake_key(wb.name)].append(wb)
    sites_lakes = [
        wb for wb in rows
        if wb.agency_profile is not None and wb.agency_profile.agency == AGENCY and wb.agency_profile.placement == "sites"
    ]
    summary.attractors_read = len(attractors)
    lakes_with: set[int] = set()
    seen: set[str] = set()
    for att in attractors:
        if att.record_id in seen:
            continue
        seen.add(att.record_id)
        lake = match_attractor(att, index)
        wb_id = targets.get(lake.osm_ref) if lake is not None else None
        if wb_id is None:
            fallback = _lake_for_unmapped_attractor(att, named, sites_lakes)
            wb_id = fallback.id if fallback is not None else None
        if wb_id is None:
            summary.attractors_not_in_a_lake += 1
            continue
        db.add(
            FishAttractor(
                waterbody_id=wb_id, source=AGENCY, source_record_id=att.record_id,
                latitude=att.latitude, longitude=att.longitude, attractor_type=att.attractor_type,
                units=att.units, depth_ft=att.depth_ft, placed_year=att.placed_year,
                agency_waterbody=att.waterbody or None, imported_at=now,
            )
        )
        lakes_with.add(wb_id)
        summary.attractors_saved += 1
    summary.attractor_lakes = len(lakes_with)
    db.flush()


def _fetched_at(payload: dict[str, Any]) -> datetime:
    stamp = payload.get("fetched_at")
    if stamp:
        return datetime.fromisoformat(stamp).astimezone(timezone.utc).replace(tzinfo=None)
    return datetime.now(timezone.utc).replace(tzinfo=None)


def run(
    db: Session,
    osm_payload: dict[str, Any],
    access_payload: dict[str, Any],
    attractor_payload: dict[str, Any] | None,
) -> ImportSummary:
    state = db.scalar(select(State).where(State.code == "GA"))
    if state is None:
        raise ValueError("no Georgia lakes in the database; run the OpenStreetMap import for GA first")
    lakes = merge_pieces(parse_elements(osm_payload)[0])
    summary = ImportSummary()
    sites, skipped = parse_sites(access_payload.get("features") or [])
    summary.sites_read = len(access_payload.get("features") or [])
    summary.sites_skipped = dict(skipped)
    import_sites(db, state, lakes, sites, _fetched_at(access_payload), summary)
    if attractor_payload is not None:
        import_attractors(
            db, state, lakes, parse_attractors(attractor_payload.get("features") or []),
            _fetched_at(attractor_payload), summary,
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    from app.core.config import get_settings
    from app.db.session import Base, SessionLocal, engine

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--osm", type=Path, required=True, help="the Overpass file the Georgia OSM import used (--save-raw)")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help=f"where WRD's layers are saved (default: {DEFAULT_CACHE})")
    ap.add_argument("--fetch", action="store_true", help="download WRD's two layers into --cache first")
    ap.add_argument("--dry-run", action="store_true", help="do everything, then roll back")
    args = ap.parse_args(argv)

    if args.fetch:
        headers = {"User-Agent": get_settings().nominatim_user_agent}
        with httpx.Client(timeout=60, headers=headers) as client:
            fetch_all(args.cache, client)
    access_path = args.cache / ACCESS_FILE
    if not access_path.exists():
        print(f"No {access_path}: run again with --fetch.", file=sys.stderr)
        return 2
    attractor_path = args.cache / ATTRACTOR_FILE
    osm_payload = json.loads(args.osm.read_text(encoding="utf-8"))
    access_payload = json.loads(access_path.read_text(encoding="utf-8"))
    attractor_payload = json.loads(attractor_path.read_text(encoding="utf-8")) if attractor_path.exists() else None

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        try:
            summary = run(db, osm_payload, access_payload, attractor_payload)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        if args.dry_run:
            db.rollback()
        else:
            db.commit()

    print(f"WRD access sites read: {summary.sites_read}{' (dry run, nothing saved)' if args.dry_run else ''}")
    print("  left out: " + ", ".join(f"{k} {v}" for k, v in sorted(summary.sites_skipped.items())))
    print(f"  lakes: {sum(summary.lakes.values())} (" + ", ".join(f"{k} {v}" for k, v in sorted(summary.lakes.items())) + ")")
    print(f"  access points added: {summary.access_added}, updated: {summary.access_updated}, "
          f"already there (within {DUPLICATE_ACCESS_M:.0f} m): {summary.access_skipped_duplicate}, "
          f"OpenStreetMap entrances confirmed: {summary.osm_entrances_confirmed}")
    print(f"  species links: {summary.species_links}; fishing forecasts linked: {summary.forecasts_linked}")
    if attractor_payload is not None:
        print(f"fish attractors: {summary.attractors_saved} saved on {summary.attractor_lakes} lakes "
              f"(of {summary.attractors_read}; not inside a lake on the map: {summary.attractors_not_in_a_lake})")
    if summary.sites_unplaced:
        print(f"{len(summary.sites_unplaced)} sites not placed (left out, not guessed):")
        for name, reason in summary.sites_unplaced[:40]:
            print(f"  - {name}: {reason}")
        if len(summary.sites_unplaced) > 40:
            print(f"  ... and {len(summary.sites_unplaced) - 40} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
