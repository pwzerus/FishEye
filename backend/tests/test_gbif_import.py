"""Tests for the GBIF "reported" tier: fetching and matching
(app/data_import/gbif_occurrence_import.py), what the API shows, and what it
must never do: turn a record into an official confirmation, or leak into
scoring or the AI advisor. Network-free throughout.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.data_import import gbif_occurrence_import as gbif
from app.data_import import osm_waterbody_import as osm
from app.data_import.osm_waterbody_import import Bounds, OsmLake
from app.models.waterbody import SpeciesOccurrence, Waterbody, WaterbodySpecies
from tests.test_osm_import import PAYLOAD, _lake, _snapshot

CC0 = "http://creativecommons.org/publicdomain/zero/1.0/legalcode"
CC_BY_NC = "http://creativecommons.org/licenses/by-nc/4.0/legalcode"


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(gbif, "REQUEST_DELAY_S", 0)


def _box(ref, name, s, w, n, e, water_type="reservoir"):
    return OsmLake(ref, name, (s + n) / 2, (w + e) / 2, Bounds(s, w, n, e), water_type)


def _rec(key, lat, lng, species="Largemouth Bass", **extra: Any) -> dict[str, Any]:
    return {
        "key": key,
        "decimalLatitude": lat,
        "decimalLongitude": lng,
        "species": species,
        "year": 2020,
        "basisOfRecord": "HUMAN_OBSERVATION",
        "license": CC0,
        "datasetName": "Fishes of Texas Project",
        "institutionCode": "University of Texas Biodiversity Collections (UTBC)",
        "coordinateUncertaintyInMeters": 30,
        **extra,
    }


class FakeClient:
    """Serves /species/match from a dict and /occurrence/search from a list
    of records, honouring the year/lat filters, limit and offset."""

    def __init__(self, matches: dict[str, dict] | None = None, records: list[dict] | None = None):
        self.matches = matches or {}
        self.records = records or []
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        params = params or {}
        self.calls.append((url, params))
        if url.endswith("/species/match"):
            body: Any = self.matches.get(params["name"], {"matchType": "NONE"})
        else:
            y0, y1 = (int(x) for x in params["year"].split(","))
            a, b = (float(x) for x in params["decimalLatitude"].split(","))
            hits = [r for r in self.records if y0 <= r["year"] <= y1 and a <= r["decimalLatitude"] <= b]
            limit, offset = int(params["limit"]), int(params.get("offset", 0))
            page = hits[offset : offset + limit] if limit else []
            body = {"count": len(hits), "results": page, "endOfRecords": offset + limit >= len(hits)}
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))


# --- fetching ---------------------------------------------------------------


def test_windows_split_by_year_first_then_by_latitude():
    w = gbif.Window((30.0, 32.0), (-98.0, -96.0), (2000, 2003))
    a, b = w.split()
    assert (a.year, b.year) == ((2000, 2001), (2002, 2003))
    one_year = gbif.Window((30.0, 32.0), (-98.0, -96.0), (2010, 2010))
    c, d = one_year.split()
    assert (c.lat, d.lat) == ((30.0, 31.0), (31.0, 32.0))


def test_an_oversized_window_is_split_and_every_record_is_fetched(monkeypatch):
    monkeypatch.setattr(gbif, "MAX_WINDOW", 5)
    monkeypatch.setattr(gbif, "PAGE_SIZE", 2)
    records = [
        {"key": i, "year": 2000 + (i % 4), "decimalLatitude": 30.0 + (i % 3) * 0.5, "decimalLongitude": -97.0}
        for i in range(23)
    ]
    client = FakeClient(records=records)

    got = gbif._fetch_window(client, 1, gbif.Window((29.0, 33.0), (-98.0, -96.0), (2000, 2003)))

    assert sorted(r["key"] for r in got) == list(range(23))
    # No single paged query ever asked for more than the window cap.
    for _, params in client.calls:
        if params.get("limit"):
            assert int(params["offset"]) < 5


def test_species_resolution_uses_accepted_keys_and_skips_hybrids():
    client = FakeClient(
        matches={
            "Micropterus salmoides": {"usageKey": 10, "matchType": "EXACT", "rank": "SPECIES"},
            # A synonym: records are searched under the accepted key.
            "Micropterus nigricans": {"usageKey": 11, "acceptedUsageKey": 10, "matchType": "EXACT", "rank": "SPECIES"},
            "Micropterus floridanus": {"usageKey": 12, "matchType": "EXACT", "rank": "SPECIES"},
            # Matched only to the genus: not good enough.
            "Pomoxis annularis": {"usageKey": 99, "matchType": "HIGHERRANK", "rank": "GENUS"},
        }
    )

    keys = gbif.resolve_taxon_keys(client)

    assert keys["Largemouth Bass"] == [10, 12]
    assert keys["White Crappie"] == []
    assert keys["Hybrid Striped Bass"] == []
    assert not any(p.get("name", "").count("×") for _, p in client.calls)


# --- matching (pure) --------------------------------------------------------


def test_a_point_goes_to_the_smallest_lake_that_contains_it():
    big = _box("way/1", "Big Reservoir", 30.0, -97.2, 30.4, -96.8)
    cove = _box("way/2", "Cove", 30.10, -97.10, 30.12, -97.08)
    index = gbif.LakeIndex([big, cove])

    assert index.lookup(30.11, -97.09).osm_ref == "way/2"
    assert index.lookup(30.30, -96.90).osm_ref == "way/1"
    assert index.lookup(31.0, -96.0) is None


def test_records_with_poor_coordinate_precision_are_ignored():
    assert gbif.usable({"coordinateUncertaintyInMeters": 30})
    assert gbif.usable({"coordinateUncertaintyInMeters": None})
    assert not gbif.usable({"coordinateUncertaintyInMeters": 5000})


@pytest.mark.parametrize(
    "url,family",
    [
        (CC0, "CC0"),
        ("http://creativecommons.org/licenses/by/4.0/legalcode", "CC BY"),
        (CC_BY_NC, "CC BY-NC"),
        (None, "other/unknown"),
    ],
)
def test_licences_are_grouped_by_what_they_allow(url, family):
    assert gbif.license_family(url) == family


@pytest.mark.parametrize(
    "institution,dataset,group",
    [
        ("University of Texas Biodiversity Collections (UTBC)", "Fishes of Texas Project", "fishes_of_texas"),
        ("iNaturalist", "iNaturalist research-grade observations", "inaturalist"),
        ("TPWD", None, "tpwd"),
        ("TNHC", None, "other"),
        (None, None, "other"),
    ],
)
def test_records_are_grouped_by_who_collected_them(institution, dataset, group):
    assert gbif.source_group({"institutionCode": institution, "datasetName": dataset}) == group


def test_matching_drops_what_cant_be_trusted_and_says_why():
    lake = _box("way/1", "Lake A", 30.0, -97.2, 30.4, -96.8)
    other = _box("way/2", "Lake B, not in the database", 31.0, -97.2, 31.4, -96.8)
    records = [
        _rec(1, 30.2, -97.0),
        _rec(1, 30.2, -97.0),  # the same record twice
        _rec(2, 30.2, -97.0, basisOfRecord="FOSSIL_SPECIMEN"),
        _rec(3, 30.2, -97.0, coordinateUncertaintyInMeters=5_000),
        _rec(4, 30.2, -97.0, species="Walleye"),  # no guide for it
        _rec(5, 35.0, -100.0),  # a river or creek
        _rec(6, 31.2, -97.0),
        _rec(7, 30.3, -96.9, license=CC_BY_NC),
    ]

    matched, summary = gbif.match_records([lake, other], records, {"way/1": 42})

    assert [(wb, r["key"]) for wb, r in matched] == [(42, 1), (42, 7)]
    assert summary.duplicates == 1
    assert summary.skipped == {
        "fossil": 1,
        "coordinates imprecise": 1,
        "not a guide species": 1,
        "not in any lake": 1,
        "lake not in database": 1,
    }
    assert summary.lakes_with_records == 1
    assert summary.by_license == {"CC0": 1, "CC BY-NC": 1}


# --- import into the database ----------------------------------------------

# From test_osm_import.PAYLOAD: "Lake Tawakoni" (OSM-only, centre 32.85,
# -95.95, +-0.02 deg) and "Fork Lake" (OSM's copy of the verified Lake Fork,
# centre 32.80, -95.59, +-0.1 deg). Plus a second OSM element of Lake Fork
# (one of its arms) that the OSM import linked but didn't store.
FORK_ARM = _lake(8, "Lake Fork Reservoir", 32.78, -95.57, half_deg=0.01)
OSM = {"elements": [*PAYLOAD["elements"], FORK_ARM]}

RECORDS = [
    _rec(1, 32.851, -95.951, "Largemouth Bass", year=2023),
    _rec(2, 32.852, -95.952, "Largemouth Bass", year=2010, institutionCode="iNaturalist",
         datasetName="iNaturalist research-grade observations", license=CC_BY_NC),
    _rec(3, 32.853, -95.953, "Channel Catfish", year=1968, basisOfRecord="PRESERVED_SPECIMEN"),
    # Lake Fork: bass is officially confirmed there, striped bass isn't.
    _rec(4, 32.80, -95.59, "Largemouth Bass", year=2019),
    _rec(5, 32.781, -95.571, "Striped Bass", year=2021, institutionCode="TPWD", datasetName=None),
]


@pytest.fixture()
def imported(db_session, seeded_lake):
    osm.run("TX", OSM, db_session)
    summary = gbif.run(db_session, "TX", OSM, RECORDS)
    db_session.commit()
    tawakoni = db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Tawakoni"))
    return {"summary": summary, "tawakoni": tawakoni, "fork": seeded_lake["waterbody"]}


def test_records_are_stored_per_record_with_their_licence(db_session, imported):
    rows = db_session.scalars(select(SpeciesOccurrence).order_by(SpeciesOccurrence.source_record_id)).all()
    assert [(r.source_record_id, r.license, r.source_group) for r in rows] == [
        ("1", "CC0", "fishes_of_texas"),
        ("2", "CC BY-NC", "inaturalist"),
        ("3", "CC0", "fishes_of_texas"),
        ("4", "CC0", "fishes_of_texas"),
        ("5", "CC0", "tpwd"),
    ]


def test_records_in_any_osm_element_of_a_verified_lake_credit_that_lake(db_session, imported):
    fork_records = db_session.scalars(
        select(SpeciesOccurrence.source_record_id).where(SpeciesOccurrence.waterbody_id == imported["fork"].id)
    ).all()
    # Record 5 is in the arm, an OSM element the lake list never stored.
    assert sorted(fork_records) == ["4", "5"]


def test_a_record_never_becomes_an_official_confirmation(db_session, imported):
    links = db_session.scalars(select(WaterbodySpecies)).all()
    # Only the seeded, officially confirmed Lake Fork bass.
    assert [(link.waterbody_id, link.species.common_name) for link in links] == [
        (imported["fork"].id, "Largemouth Bass")
    ]


def test_reimporting_replaces_records_instead_of_duplicating_them(db_session, imported):
    gbif.run(db_session, "TX", OSM, RECORDS[:2])  # GBIF has since dropped 3-5
    db_session.commit()

    keys = db_session.scalars(select(SpeciesOccurrence.source_record_id)).all()
    assert sorted(keys) == ["1", "2"]


def test_detail_summarises_reported_species_apart_from_confirmed_ones(client, imported):
    body = client.get(f"/api/waterbodies/{imported['tawakoni'].id}").json()

    assert body["species"] == []  # nothing official
    bass, catfish = body["reported_species"]
    assert bass == {
        "common_name": "Largemouth Bass",
        "records": 2,
        "last_year": 2023,
        "sources": [
            {"name": "Fishes of Texas (UT Austin)", "records": 1},
            {"name": "iNaturalist", "records": 1},
        ],
        "latest_record_url": "https://www.gbif.org/occurrence/1",
        "weak": False,
        "also_confirmed": False,
    }
    # One 1968 specimen: shown, but flagged as weak evidence.
    assert (catfish["common_name"], catfish["records"], catfish["weak"]) == ("Channel Catfish", 1, True)


def test_a_reported_species_already_confirmed_officially_is_marked(client, imported):
    body = client.get(f"/api/waterbodies/{imported['fork'].id}").json()
    reported = {s["common_name"]: s["also_confirmed"] for s in body["reported_species"]}
    assert reported == {"Largemouth Bass": True, "Striped Bass": False}


def test_the_map_list_counts_reported_species(client, imported):
    body = client.get("/api/waterbodies", params={"bbox": "-96.1,32.7,-95.4,32.9"}).json()
    counts = {w["name"]: w["reported_species_count"] for w in body}
    assert counts["Lake Tawakoni"] == 2
    assert counts["Lake Fork"] == 2


def test_noncommercial_records_can_be_switched_off(client, imported, monkeypatch):
    monkeypatch.setattr(get_settings(), "gbif_exclude_noncommercial", True)

    body = client.get(f"/api/waterbodies/{imported['tawakoni'].id}").json()
    bass = body["reported_species"][0]
    assert (bass["records"], [s["name"] for s in bass["sources"]]) == (1, ["Fishes of Texas (UT Austin)"])


def test_the_advisor_never_sees_reported_species(db_session, imported):
    from app.services import ai_advisor

    facts = ai_advisor.gather_facts(db_session, imported["fork"].id, weather=_snapshot())

    assert [s["common_name"] for s in facts["species_confirmed_here"]] == ["Largemouth Bass"]
    assert "Striped Bass" not in repr(facts)


def test_species_filter_on_the_map_uses_confirmed_species_only(client, imported):
    body = client.get("/api/waterbodies", params={"species": "Striped Bass"}).json()
    assert body == []


def test_an_osm_lake_replaced_by_a_verified_one_hands_over_its_records(db_session, imported):
    tawakoni_id = imported["tawakoni"].id
    verified = Waterbody(
        state_id=imported["tawakoni"].state_id,
        name="Tawakoni Reservoir",
        latitude=32.85,
        longitude=-95.95,
        access_summary="verified",
        source_url="https://tpwd.texas.gov/tawakoni",
        source_updated_at=datetime(2026, 9, 24, tzinfo=timezone.utc),
    )
    db_session.add(verified)
    db_session.flush()

    osm.run("TX", OSM, db_session)
    db_session.commit()

    assert db_session.get(Waterbody, tawakoni_id) is None
    moved = db_session.scalars(
        select(SpeciesOccurrence.source_record_id).where(SpeciesOccurrence.waterbody_id == verified.id)
    ).all()
    assert sorted(moved) == ["1", "2", "3"]


def test_import_refuses_a_state_with_no_lakes(db_session):
    with pytest.raises(ValueError, match="OSM import first"):
        gbif.run(db_session, "TX", OSM, RECORDS)
