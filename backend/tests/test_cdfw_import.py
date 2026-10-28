"""California's official data (app/data_import/cdfw_import.py). Network-free:
a cache folder of small JSON files shaped like the real ones, on
OpenStreetMap lakes built the way the OSM import builds them."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.data_import import cdfw_import as cdfw
from app.data_import import osm_waterbody_import as osm
from app.models.waterbody import (
    AgencyLakeProfile,
    SourceRecord,
    SpeciesEvidence,
    Waterbody,
    WaterbodySource,
    WaterbodySpecies,
)
from tests.test_osm_import import _lake

NOW = datetime(2026, 10, 26)

OSM = {"elements": [
    _lake(1, "Lake Natoma", 38.64, -121.20, half_deg=0.02),
    _lake(2, "Mather Lake", 38.55, -121.25, half_deg=0.004),
    _lake(3, "Twin Lakes", 37.60, -119.00, half_deg=0.01),
]}

LAKES = [
    # Same name as an OSM lake, centre inside its box.
    {"id": 2700, "name": "Lake Natoma", "county": "Sacramento", "lat": 38.641, "lng": -121.201, "acres": 500,
     "type": "perennial", "bbox": [38.63, -121.21, 38.65, -121.19]},
    # No name in CDFW's layer (the planting schedule names it); the only OSM
    # lake there.
    {"id": 2753, "name": "", "county": "Sacramento", "lat": 38.5501, "lng": -121.2501, "acres": 60,
     "type": "", "bbox": [38.548, -121.252, 38.552, -121.248]},
    # Named, no OSM lake: added from CDFW's layer.
    {"id": 9001, "name": "Frog Lake", "county": "Alpine", "lat": 38.70, "lng": -119.90, "acres": 12,
     "type": "", "bbox": [38.699, -119.901, 38.701, -119.899]},
    # Too small to add, and CDFW says nothing else about it.
    {"id": 9002, "name": "Tiny Tarn", "county": "Alpine", "lat": 38.80, "lng": -119.80, "acres": 0.5,
     "type": "", "bbox": [38.799, -119.801, 38.801, -119.799]},
    # Its name says private: never added.
    {"id": 9003, "name": "Private Pond", "county": "Alpine", "lat": 38.90, "lng": -119.70, "acres": 20,
     "type": "", "bbox": [38.899, -119.701, 38.901, -119.699]},
]
DS778 = [{"dfg_water_id": 2753, "stocking_water_id": 2753, "counties": "Sacramento", "last_year": 2025,
          "lat": 38.55, "lng": -121.25}]
PLANTS = [
    {"week_start": "2025-11-02", "dfg_water_id": 2753, "stocking_water_id": 2753, "water_name": "Mather Lake",
     "fish_type": "Trout", "counties": "Sacramento"},
    {"week_start": "2026-01-04", "dfg_water_id": 2700, "stocking_water_id": 2700, "water_name": "Lake Natoma",
     "fish_type": "Trout", "counties": "Sacramento"},
    # A river planting: no lake polygon, counted, never forced onto a lake.
    {"week_start": "2026-01-04", "dfg_water_id": 146068081, "stocking_water_id": 500763,
     "water_name": "Kern River, Section 6", "fish_type": "Trout", "counties": "Tulare"},
]
PLAN = [
    {"region": "R2", "county": "Sacramento", "water": "Lake Natoma", "species": "Rainbow Trout", "size": "Catchable"},
    {"region": "R2", "county": "Sacramento", "water": "American River Lower", "species": "Rainbow Trout", "size": "Catchable"},
]
DS102 = [
    {"calakes_id": 9001, "hml_id": "1", "species": "Brook trout", "scientific_name": "Salvelinus fontinalis",
     "year": 2019, "survey_type": "BaseLine", "lat": 38.70, "lng": -119.90},
    {"calakes_id": 9001, "hml_id": "1", "species": "Brook trout", "scientific_name": "Salvelinus fontinalis",
     "year": 2023, "survey_type": "Monitoring", "lat": 38.70, "lng": -119.90},
    {"calakes_id": 9001, "hml_id": "1", "species": "Minnow, golden shiner", "scientific_name": None,
     "year": 2023, "survey_type": "Monitoring", "lat": 38.70, "lng": -119.90},
]


def _cache(tmp_path: Path, **overrides) -> Path:
    files = {"ca_lakes.json": LAKES, "ds778.json": DS778, "fishplants.json": PLANTS,
             "plan2026.json": PLAN, "ds102.json": DS102, **overrides}
    for name, rows in files.items():
        (tmp_path / name).write_text(json.dumps(rows), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({n: "2026-10-26T14:19:00+00:00" for n in files}))
    return tmp_path


def _run(db, tmp_path, **overrides):
    osm.run("CA", OSM, db)
    return cdfw.run(db, OSM, _cache(tmp_path, **overrides), now=NOW)


def _lake_named(db, name) -> Waterbody:
    return db.scalars(select(Waterbody).where(Waterbody.name == name)).one()


def test_matching_by_name_and_by_size_records_cdfws_id(db_session, tmp_path):
    summary = _run(db_session, tmp_path)
    # The unnamed polygon took the planting schedule's name for it, so both
    # match by name.
    assert summary.matched == {"name": 2}
    assert _lake_named(db_session, "Lake Natoma").dfg_water_id == 2700
    mather = _lake_named(db_session, "Mather Lake")
    assert mather.dfg_water_id == 2753
    # The unnamed polygon took its name from the planting schedule.
    assert mather.official_name is None


def test_a_stocked_lake_becomes_verified_and_credits_ds778(db_session, tmp_path):
    summary = _run(db_session, tmp_path)
    mather = _lake_named(db_session, "Mather Lake")
    assert mather.data_tier == "verified"
    assert "stocked fish here in 2025" in mather.access_summary
    assert mather.agency_profile.agency == "cdfw"
    assert mather.agency_profile.page_url.endswith("Params.StockingWaterID=2753")
    keys = {db_session.get(SourceRecord, ds.source_record_id).source_key for ds in mather.dataset_links}
    assert keys == {"cdfw_ca_lakes", "cdfw_ds778"}
    # Both stocked lakes (ds778 or the schedule); the river is counted, not placed.
    assert summary.lakes_verified == 2
    assert summary.stocked_not_a_lake == 1


def test_named_lakes_missing_from_osm_are_added_unless_tiny_or_private(db_session, tmp_path):
    summary = _run(db_session, tmp_path)
    frog = _lake_named(db_session, "Frog Lake")
    assert (frog.data_tier, frog.osm_ref, frog.dfg_water_id) == ("osm", None, 9001)
    assert "California Department of Fish and Wildlife" in frog.access_summary
    assert "DFGWATERID%3D9001" in frog.source_url
    names = set(db_session.scalars(select(Waterbody.name)))
    assert "Tiny Tarn" not in names and "Private Pond" not in names
    assert summary.lakes_added == 1


def test_species_evidence_is_our_sentence_with_a_link(db_session, tmp_path):
    _run(db_session, tmp_path)
    natoma = _lake_named(db_session, "Lake Natoma")
    by_source = {e.source: e for e in natoma.species_evidence}
    plan = by_source["cdfw_plan_2026"]
    assert plan.evidence == "CDFW's 2026 stocking plan lists Rainbow Trout for this water."
    assert plan.source_url == cdfw.PLAN_2026 and plan.kind == "stocking_plan"
    # The schedule says only "Trout"; the plan names the species for this
    # lake, so the planting is filed under it.
    plants = by_source["cdfw_plants"]
    assert plants.species.common_name == "Rainbow Trout"
    assert "the week of January 4, 2026" in plants.evidence
    link = db_session.get(WaterbodySpecies, (natoma.id, plants.species_id))
    assert link.confidence == "confirmed"


def test_a_schedule_that_names_no_species_stays_generic(db_session, tmp_path):
    _run(db_session, tmp_path)
    mather = _lake_named(db_session, "Mather Lake")
    names = {e.species.common_name for e in mather.species_evidence}
    assert names == {"Trout"}
    assert "does not name the species" in mather.species_evidence[0].evidence


def test_ds102_gives_the_latest_survey_year_and_skips_unmapped_fish(db_session, tmp_path):
    summary = _run(db_session, tmp_path)
    frog = _lake_named(db_session, "Frog Lake")
    [e] = frog.species_evidence
    assert (e.species.common_name, e.year) == ("Brook Trout", 2023)
    assert e.evidence == "CDFW's High Mountain Lakes survey recorded Brook Trout here in 2023."
    assert summary.ds102_skipped["species not mapped"] == 1


def test_fish_not_present_rows_are_never_evidence():
    rows = cdfw.ds102_rows([
        {"FishNotPresent": "Y", "SpeciesName": "Brook trout", "CaLakesID": 1.0},
        {"FishNotPresent": "Y", "SpeciesName": None, "CaLakesID": 2.0},
        {"FishNotPresent": "N", "SpeciesName": "Golden trout", "CaLakesID": 3.0, "SurveyDate": "2021-07-01"},
    ])
    assert [(r["calakes_id"], r["species"], r["year"]) for r in rows] == [(3, "Golden trout", 2021)]


def test_re_running_adds_nothing_twice_and_drops_what_the_source_dropped(db_session, tmp_path):
    _run(db_session, tmp_path)
    before = db_session.query(SpeciesEvidence).count()
    summary = cdfw.run(db_session, OSM, _cache(tmp_path), now=NOW)
    assert db_session.query(SpeciesEvidence).count() == before
    assert sum(summary.evidence_new.values()) == 0
    # The plan no longer lists Lake Natoma: its plan evidence goes.
    summary = cdfw.run(db_session, OSM, _cache(tmp_path, **{"plan2026.json": PLAN[1:]}), now=NOW)
    assert summary.evidence_pruned >= 1
    db_session.expire_all()
    natoma = _lake_named(db_session, "Lake Natoma")
    assert "cdfw_plan_2026" not in {e.source for e in natoma.species_evidence}


def test_a_lake_added_from_cdfw_merges_into_osm_once_osm_has_it(db_session, tmp_path):
    _run(db_session, tmp_path)
    frog_id = _lake_named(db_session, "Frog Lake").id
    later = {"elements": OSM["elements"] + [_lake(9, "Frog Lake", 38.70, -119.90, half_deg=0.003)]}
    osm.run("CA", later, db_session)
    summary = cdfw.run(db_session, later, _cache(tmp_path), now=NOW)
    assert summary.merged_into_osm == 1
    frog = _lake_named(db_session, "Frog Lake")
    assert frog.osm_ref == "way/9" and frog.id != frog_id and frog.dfg_water_id == 9001
    assert {e.species.common_name for e in frog.species_evidence} == {"Brook Trout"}
    assert db_session.get(Waterbody, frog_id) is None
    assert db_session.scalars(select(WaterbodySource).where(WaterbodySource.waterbody_id == frog_id)).first() is None


def test_plan_rows_match_by_county_and_word_order():
    lakes = cdfw.parse_lakes([
        {"id": 1, "name": "Lower Angora Lake", "county": "El Dorado", "lat": 38.8, "lng": -120.0, "acres": 10},
        {"id": 2, "name": "Silver Lake", "county": "Amador", "lat": 38.6, "lng": -120.1, "acres": 100},
        {"id": 3, "name": "Silver Lake", "county": "Mono", "lat": 37.7, "lng": -119.1, "acres": 80},
    ])
    plan = [
        {"county": "El Dorado", "water": "Angora Lake Lower", "species": "Rainbow Trout"},
        {"county": "Mono", "water": "Silver Lake", "species": "Brown Trout"},
        {"county": "Shasta", "water": "Hat Creek Upper", "species": "Rainbow Trout"},
    ]
    summary = cdfw.ImportSummary()
    assert cdfw._plan_ids(plan, lakes, summary) == {0: frozenset({1}), 1: frozenset({3})}
    assert summary.plan_unmatched == ["Hat Creek Upper (Shasta)"]


def test_the_plan_pdfs_table_rows_are_read_and_prose_is_not():
    text = "\n".join([
        "Kokanee (non-native): land locked Sockeye Salmon planted as fingerlings",
        "R1 Del Norte Dry Lake Rainbow Trout Catchable Put and Take March",
        "R6 San Bernardino Big Bear Lake Brown Trout Sub-catchable Put and Grow January-December",
        "R1 Shasta McCloud Reservoir McCloud River Redband Trout Catchable Put and Take April-October",
        "November-December",
    ])
    assert [(r["county"], r["water"], r["species"], r["size"]) for r in cdfw.parse_plan_text(text)] == [
        ("Del Norte", "Dry Lake", "Rainbow Trout", "Catchable"),
        ("San Bernardino", "Big Bear Lake", "Brown Trout", "Sub-catchable"),
        ("Shasta", "McCloud Reservoir", "McCloud River Redband Trout", "Catchable"),
    ]


def test_the_planting_export_is_read_by_its_columns():
    csv_text = (
        "﻿WeekOfPlantStart,WeekOfPlantEnd,Counties,DfgWaterId,Lat,Lon,WaterName,StockingWaterID,FishType,CountyName\r\n"
        '"11/2/2025 12:00:00 AM","11/8/2025 12:00:00 AM","Los Angeles","7115","34.26","-118.39","Hansen Dam Lake","7115","Trout",""\r\n'
    )
    assert cdfw.parse_plants_csv(csv_text) == [{
        "week_start": "2025-11-02", "dfg_water_id": 7115, "stocking_water_id": 7115,
        "water_name": "Hansen Dam Lake", "fish_type": "Trout", "counties": "Los Angeles",
    }]


def test_every_source_record_carries_its_licence(db_session, tmp_path):
    _run(db_session, tmp_path)
    rows = {r.source_key: r for r in db_session.scalars(select(SourceRecord))}
    assert rows["cdfw_ds778"].licence_name == "CC BY 4.0" and rows["cdfw_ds778"].licence_class == "OPEN"
    assert "Citing-BIOS" in rows["cdfw_ds102"].citation
    assert rows["cdfw_plants"].licence_class == "PD"
    assert db_session.query(AgencyLakeProfile).filter_by(agency="cdfw").count() == 3


def test_the_lake_panel_lists_each_fact_with_its_link_and_the_datasets(client, db_session, tmp_path):
    _run(db_session, tmp_path)
    natoma = _lake_named(db_session, "Lake Natoma")
    natoma.public_land, natoma.public_land_name = "open", "Folsom Lake State Recreation Area"
    db_session.commit()
    body = client.get(f"/api/waterbodies/{natoma.id}").json()
    [trout] = body["species"]
    assert trout["common_name"] == "Rainbow Trout"
    # Newest first; both are from 2026.
    assert [(i["kind"], i["source_url"]) for i in trout["evidence_items"]] == [
        ("stocking", f"{cdfw.PLANTS_PAGE}?Params.StockingWaterID=2700"),
        ("stocking_plan", cdfw.PLAN_2026),
    ]
    assert body["data_credit"] == "Data: California Department of Fish and Wildlife"
    assert body["public_land"] == "open" and body["public_land_name"] == "Folsom Lake State Recreation Area"
    titles = [s["title"] for s in body["sources"]]
    assert "California Lakes" in titles and "Fish Planting Schedule" in titles
    assert all(s["licence"] for s in body["sources"])


def test_two_cdfw_polygons_of_one_lake_give_one_fact_each(db_session, tmp_path):
    # A second Lake Natoma polygon (an arm), and a plan row for each id.
    lakes = LAKES + [{"id": 2701, "name": "Lake Natoma", "county": "Sacramento", "lat": 38.645, "lng": -121.195,
                      "acres": 40, "type": "", "bbox": [38.644, -121.196, 38.646, -121.194]}]
    plan = PLAN + [{"region": "R2", "county": "Sacramento", "water": "Lake Natoma", "species": "Rainbow Trout",
                    "size": "Fingerling"}]
    _run(db_session, tmp_path, **{"ca_lakes.json": lakes, "plan2026.json": plan})
    natoma = _lake_named(db_session, "Lake Natoma")
    sources = [e.source for e in natoma.species_evidence]
    assert sources.count("cdfw_plan_2026") == 1 and sources.count("cdfw_plants") == 1
    assert natoma.dfg_water_id == 2700  # the larger polygon's id
