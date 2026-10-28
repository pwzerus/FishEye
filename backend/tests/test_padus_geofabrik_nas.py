"""PAD-US public land, Geofabrik extracts and USGS NAS records. Network-free:
small payloads shaped like the services' own, and a tiny OSM file for the
pyosmium extract (skipped where pyosmium isn't installed, as in the API
image: it is a local import tool)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.data_import import geofabrik_lakes as gf
from app.data_import import osm_waterbody_import as osm
from app.data_import import padus_import as padus
from app.data_import import usgs_nas_import as nas
from app.data_import.us_states import STATES, ensure_states
from app.models.waterbody import SourceRecord, SpeciesOccurrence, State, Waterbody, WaterbodySource
from tests.test_osm_import import _lake


def _square(oid, west, south, east, north, access="OA", name="Angeles National Forest", manager="Forest Service", hole=None):
    rings = [[[west, south], [east, south], [east, north], [west, north], [west, south]]]
    if hole:
        w, s, e, n = hole
        rings.append([[w, s], [w, n], [e, n], [e, s], [w, s]])
    return {"attributes": {"OBJECTID": oid, "Unit_Nm": name, "Pub_Access": access, "MngNm_Desc": manager,
                           "MngTp_Desc": "Federal", "DesTp_Desc": "National Forest"},
            "geometry": {"rings": rings}}


# ---------------------------------------------------------------- PAD-US


def test_a_point_in_a_hole_is_outside_the_area():
    [area] = padus.parse_areas([_square(1, -118.5, 34.0, -118.0, 34.5, hole=(-118.3, 34.2, -118.2, 34.3))])
    assert padus.contains(area, 34.1, -118.4)
    assert not padus.contains(area, 34.25, -118.25)
    assert not padus.contains(area, 35.0, -118.25)


def test_open_beats_restricted_and_closed_areas_are_ignored():
    areas = padus.parse_areas([
        _square(1, -119, 34, -118, 35, access="RA", name="Military Reservation"),
        _square(2, -118.6, 34.4, -118.4, 34.6, access="OA", name="County Park"),
        _square(3, -118.6, 34.4, -118.4, 34.6, access="XA", name="Closed Area"),
    ])
    assert [a.name for a in areas] == ["Military Reservation", "County Park"]
    assert padus.best_area(areas, 34.5, -118.5).name == "County Park"
    assert padus.best_area(areas, 34.1, -118.9).access == "restricted"
    assert padus.best_area(areas, 36.0, -118.5) is None


def test_lakes_are_marked_and_cleared_on_a_re_run(db_session):
    osm.run("CA", {"elements": [_lake(1, "Castaic Lake", 34.52, -118.61, 0.02), _lake(2, "Far Lake", 36.0, -119.0, 0.01)]}, db_session)
    payload = {"fetched_at": "2026-10-26T15:00:00+00:00", "features": [_square(7, -118.7, 34.4, -118.5, 34.6)]}
    summary = padus.run(db_session, "CA", payload)
    castaic = db_session.scalars(select(Waterbody).where(Waterbody.name == "Castaic Lake")).one()
    assert (castaic.public_land, castaic.public_land_name, castaic.public_land_manager) == (
        "open", "Angeles National Forest", "Forest Service")
    assert summary.by_access == {"open": 1}
    rec = db_session.scalars(select(SourceRecord).where(SourceRecord.source_key == "padus_4_1")).one()
    assert rec.licence_class == "PD"
    assert db_session.get(WaterbodySource, (castaic.id, rec.id)).source_key == "padus:7"
    padus.run(db_session, "CA", {"features": []})
    db_session.refresh(castaic)
    assert castaic.public_land is None
    assert db_session.get(WaterbodySource, (castaic.id, rec.id)) is None


# ---------------------------------------------------------------- Geofabrik


def test_every_state_and_dc_gets_a_row_once(db_session):
    assert ensure_states(db_session) == 51
    assert ensure_states(db_session) == 0
    assert {s.code for s in db_session.scalars(select(State))} == {s.code for s in STATES}


def test_state_membership_uses_the_outline_with_a_margin():
    ca = gf.load_outline("CA")
    assert gf.in_state(ca, 38.63, -121.21, 38.65, -121.19, "CA")  # Lake Natoma
    assert not gf.in_state(ca, 39.08, -119.75, 39.10, -119.73, "CA")  # Carson City, NV
    # Lake Tahoe straddles the border: it belongs to both.
    assert gf.in_state(ca, 38.93, -120.15, 39.25, -119.93, "CA")


def test_alaskas_outline_holds_lakes_across_the_date_line():
    ak = gf.load_outline("AK")
    assert gf.in_state(ak, 52.83, 173.15, 52.86, 173.20, "AK")  # Attu Island, east of 180
    assert gf.in_state(ak, 61.20, -149.90, 61.22, -149.85, "AK")  # Anchorage
    hi = gf.load_outline("HI")
    assert gf.in_state(hi, 21.36, -157.95, 21.37, -157.94, "HI")  # Oahu


OSM_XML = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6">
  <node id="1" lat="38.630" lon="-121.210"/><node id="2" lat="38.630" lon="-121.190"/>
  <node id="3" lat="38.650" lon="-121.190"/><node id="4" lat="38.650" lon="-121.210"/>
  <node id="5" lat="38.700" lon="-121.300"/><node id="6" lat="38.700" lon="-121.290"/>
  <node id="7" lat="38.710" lon="-121.290"/>
  <node id="8" lat="38.640" lon="-121.205"><tag k="leisure" v="slipway"/></node>
  <node id="9" lat="38.800" lon="-121.400"/><node id="10" lat="38.800" lon="-121.390"/>
  <node id="11" lat="38.810" lon="-121.390"/>
  <way id="100"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
    <tag k="natural" v="water"/><tag k="water" v="reservoir"/><tag k="name" v="Lake Natoma"/></way>
  <way id="101"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="5"/></way>
  <way id="102"><nd ref="9"/><nd ref="10"/><nd ref="11"/><nd ref="9"/>
    <tag k="natural" v="water"/><tag k="name" v="Untyped Water"/></way>
  <relation id="200"><member type="way" ref="101" role="outer"/>
    <tag k="type" v="multipolygon"/><tag k="natural" v="water"/><tag k="water" v="lake"/><tag k="name" v="Relation Lake"/></relation>
</osm>
"""


def test_the_extract_has_the_overpass_shape(tmp_path):
    pytest.importorskip("osmium")
    path = tmp_path / "tiny.osm"
    path.write_text(OSM_XML, encoding="utf-8")
    payload = gf.extract(path, "CA")
    by_ref = {f"{e['type']}/{e['id']}": e for e in payload["elements"]}
    # The untyped water is carried along; the import judges it (untyped_water).
    assert set(by_ref) == {"way/100", "way/102", "relation/200", "node/8"}
    assert payload["extract_version"] == gf.EXTRACT_VERSION
    assert by_ref["way/100"]["bounds"] == {"minlat": 38.63, "minlon": -121.21, "maxlat": 38.65, "maxlon": -121.19}
    assert by_ref["relation/200"]["bounds"]["maxlat"] == 38.71
    lakes, access, skipped = osm.parse_elements(payload)
    # "Untyped Water" doesn't say lake.
    assert {lake.name for lake in lakes} == {"Lake Natoma", "Relation Lake"} and len(access) == 1
    assert skipped == {"untyped_not_lake": 1}


# ---------------------------------------------------------------- USGS NAS


def _nas(key, sci, common, lat, lng, status="established", accuracy="Accurate", year=2015):
    return {"key": key, "scientificName": sci, "commonName": common, "decimalLatitude": lat,
            "decimalLongitude": lng, "latLongAccuracy": accuracy, "year": year, "status": status,
            "recordType": "Specimen", "locality": "", "county": ""}


def test_nas_records_in_lakes_become_reported_occurrences(db_session, tmp_path):
    ca_osm = {"elements": [_lake(1, "Castaic Lake", 34.52, -118.61, 0.02)]}
    osm.run("CA", ca_osm, db_session)
    payload = {"fetched_at": "2026-10-26T15:00:00+00:00", "records": [
        _nas(1, "Micropterus salmoides", "Largemouth Bass", 34.52, -118.61),
        _nas(1, "Micropterus salmoides", "Largemouth Bass", 34.52, -118.61),  # duplicate
        _nas(2, "Morone saxatilis", "Striped Bass", 34.51, -118.60, status="failed"),
        _nas(3, "Pomoxis annularis", "White Crappie", 34.52, -118.61, accuracy="Centroid"),
        _nas(4, "Gambusia affinis", "Western Mosquitofish", 34.52, -118.61),
        _nas(5, "Lepomis macrochirus", "Bluegill", 36.0, -120.0),
    ]}
    summary = nas.run(db_session, "CA", payload, ca_osm, cdfw_cache=tmp_path)
    rows = db_session.scalars(select(SpeciesOccurrence)).all()
    assert [(r.species_name, r.source, r.license, r.source_group) for r in rows] == [
        ("Largemouth Bass", "usgs_nas", "PD", "usgs_nas")]
    assert summary.skipped == {
        "duplicate": 1, "no longer there (failed/extirpated/eradicated)": 1,
        "county or state centroid only": 1, "species not mapped": 1, "not in a lake": 1,
    }
    # Re-running replaces, never duplicates.
    nas.run(db_session, "CA", payload, ca_osm, cdfw_cache=tmp_path)
    assert db_session.query(SpeciesOccurrence).count() == 1


def test_nas_records_show_in_the_lake_panel_with_their_page(client, db_session, tmp_path):
    ca_osm = {"elements": [_lake(1, "Castaic Lake", 34.52, -118.61, 0.02)]}
    osm.run("CA", ca_osm, db_session)
    nas.run(db_session, "CA", {"records": [_nas(77, "Micropterus salmoides", "Largemouth Bass", 34.52, -118.61)]},
            ca_osm, cdfw_cache=tmp_path)
    db_session.commit()
    wb = db_session.scalars(select(Waterbody)).one()
    [rep] = client.get(f"/api/waterbodies/{wb.id}").json()["reported_species"]
    assert rep["sources"] == [{"name": "USGS Nonindigenous Aquatic Species", "records": 1}]
    assert rep["latest_record_url"].endswith("SpecimenID=77")


def test_the_cache_keeps_only_the_fields_we_use(monkeypatch, tmp_path):
    class Resp:
        status_code = 200

        def __init__(self, body):
            self._body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self._body

    pages = [{"results": [dict(_nas(1, "Micropterus salmoides", "Largemouth Bass", 1, 2), references=[{"author": "x"}])],
              "endOfRecords": "false"},
             {"results": [], "endOfRecords": "true"}]

    class Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get(self, url, params=None):
            return Resp(pages.pop(0))

    import httpx

    monkeypatch.setattr(httpx, "Client", Client)
    monkeypatch.setattr(nas, "REQUEST_DELAY_S", 0)
    path = nas.fetch("CA", tmp_path)
    [row] = json.loads(Path(path).read_text())["records"]
    assert set(row) == set(nas.KEEP_FIELDS)
