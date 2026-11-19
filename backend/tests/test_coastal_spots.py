"""Saltwater fishing spots: which OpenStreetMap elements count, the coast a
spot is on, CDFW's public piers, folding the two into one list, the import
and the API (data_import/coastal_spots.py, cdfw_piers.py, coastal_spots_db.py)."""
import json

from app.data_import import cdfw_piers
from app.data_import.coastal_spots import coast_of, spot_fields, spot_kind, state_of
from app.data_import.coastal_spots_db import dedupe, merge, run
from app.models.coastal_spot import CoastalSpot
from app.models.waterbody import SourceRecord


def test_piers_marked_for_fishing_or_named_for_it_count():
    assert spot_kind({"man_made": "pier", "fishing": "yes"}) == "pier"
    assert spot_kind({"man_made": "pier", "leisure": "fishing"}) == "pier"
    assert spot_kind({"man_made": "pier", "name": "Seawall Fishing Pier"}) == "pier"
    assert spot_kind({"man_made": "pier", "name": "Hanalei Pier"}) == "pier"
    assert spot_kind({"man_made": "pier", "name": "Waimea State Recreation Pier"}) == "pier"


def test_harbour_berths_and_working_piers_do_not():
    # Named only by a number or a code: a berth in a harbour (Honolulu, 2026-11-18).
    for name in ("38", "K10", "Pier 51A", "29 RBS", "S-20"):
        assert spot_kind({"man_made": "pier", "name": name}) is None, name
    for name in ("Army Wharf", "USS Utah Memorial Pier", "Ferry Terminal Pier", "Harbor Marina Dock", "Patrol Boat Pier"):
        assert spot_kind({"man_made": "pier", "name": name}) is None, name
    assert spot_kind({"man_made": "pier"}) is None  # unnamed and not marked for fishing
    for name in ("NOAA Pier", "NOAA - NMFS Pier", "Marathon Refinery Pier", "USCG and Harbormasters Office Pier"):
        assert spot_kind({"man_made": "pier", "name": name}) is None, name
    # Named for fishing wins over a working-pier word in the name.
    assert spot_kind({"man_made": "pier", "name": "USS Alabama Park Fishing Pier"}) == "pier"
    assert spot_kind({"man_made": "pier", "name": "Fishing Pier & Cleaning Station"}) == "pier"


def test_private_no_fishing_and_businesses_are_left_out():
    assert spot_kind({"man_made": "pier", "fishing": "yes", "access": "private"}) is None
    assert spot_kind({"man_made": "pier", "name": "Main Street Pier", "fishing": "no"}) is None
    assert spot_kind({"leisure": "slipway", "access": "private"}) is None
    # A charter boat tagged for fishing is a business, not a place to walk to.
    assert spot_kind({"leisure": "fishing", "name": "Miss Directed Fishing Charters"}) is None


def test_jetties_fishing_spots_and_boat_ramps():
    assert spot_kind({"man_made": "breakwater", "name": "South Jetty"}) == "jetty"
    assert spot_kind({"man_made": "groyne", "fishing": "yes"}) == "jetty"
    assert spot_kind({"man_made": "breakwater"}) is None
    assert spot_kind({"leisure": "fishing"}) == "fishing_spot"
    assert spot_kind({"leisure": "slipway"}) == "boat_ramp"


def test_jetties_drawn_as_piers_jetty_parks_and_fishing_bridges():
    assert spot_kind({"man_made": "pier", "name": "Bodega Bay North Jetty"}) == "jetty"
    assert spot_kind({"leisure": "park", "name": "Surfside Jetty Park"}) == "jetty"
    assert spot_kind({"leisure": "park", "name": "Jetty View Park"}) is None  # a view of one
    assert spot_kind({"leisure": "park", "name": "Kemah Fishing Pier"}) == "pier"
    assert spot_kind({"leisure": "park", "name": "Sunset Park"}) is None
    assert spot_kind({"bridge": "yes", "highway": "footway", "fishing": "yes"}) == "fishing_spot"
    assert spot_kind({"natural": "beach", "fishing": "yes"}) == "fishing_spot"  # surf fishing
    assert spot_kind({"natural": "water", "fishing": "yes"}) is None  # a lake: the lakes cover it


def test_keeps_what_an_angler_needs():
    f = spot_fields({"man_made": "pier", "fishing": "yes", "name": "Bob Hall Pier", "fee": "yes", "lit": "yes",
                     "opening_hours": "24/7", "operator": "Nueces County"})
    assert f["kind"] == "pier" and f["fishing_tagged"] and f["lit"]
    assert (f["fee"], f["opening_hours"], f["operator"]) == ("yes", "24/7", "Nueces County")


def test_which_coast():
    assert coast_of("TX", 27.6, -97.2) == "gulf"
    assert coast_of("CA", 33.6, -118.0) == "pacific"
    assert coast_of("NJ", 39.9, -74.0) == "atlantic"
    assert coast_of("AK", 61.2, -149.9) == "alaska"
    assert coast_of("HI", 21.3, -157.8) == "hawaii"
    assert coast_of("FL", 27.9, -82.8) == "gulf"  # Clearwater
    assert coast_of("FL", 30.4, -86.6) == "gulf"  # the panhandle
    assert coast_of("FL", 26.7, -80.0) == "atlantic"  # Palm Beach
    assert coast_of("FL", 24.6, -81.8) == "atlantic"  # Key West


def test_the_state_is_where_the_spot_stands():
    # A state's extract reaches past its border; the Census counties say which side.
    assert state_of([(40.7337, -74.0127)]) == "NY"  # Manhattan, Pier 45
    assert state_of([(40.7430, -74.0260)]) == "NJ"  # Hoboken, across the Hudson
    assert state_of([(30.7210, -81.5480)]) == "GA"  # St. Marys, at the Florida line
    assert state_of([(49.0160, -122.8040)]) is None  # White Rock, British Columbia
    assert state_of([(34.0080, -118.4990), (34.0102, -118.4960)]) == "CA"  # Santa Monica Pier: end at sea, foot ashore


def _payload(spots, states=("TX",)):
    return {"extracted_at": "2026-11-18T12:00:00+00:00", "states": list(states), "spots": spots}


def _spot(ref, name="Bob Hall Pier", kind="pier", lat=27.58, lng=-97.22, state="TX", coast="gulf", fishing=True):
    return {"osm_ref": ref, "name": name, "kind": kind, "coast": coast, "lat": lat, "lng": lng, "state": state,
            "fishing_tagged": fishing, "fee": None, "opening_hours": None, "lit": False, "operator": None, "website": None}


def _cdfw_file(tmp_path):
    def pier(oid, name, notes, lng, lat):
        return {"type": "Feature", "properties": {"OBJECTID": oid, "pier": name, "county": "-", "notes": notes},
                "geometry": {"type": "Point", "coordinates": [lng, lat]}}
    rock = "On the adjacent rock wall touching land a fishing license is required"
    features = [
        pier(1, "Huntington Beach Pier", "None", -118.00297, 33.65627),
        pier(2, "Newport Harbor North Jetty", rock, -117.88111, 33.59333),
        pier(3, "Moss Landing Breakwater North",
             "On the adjacent rock wall touching land and on jetty inside the harbor a license is required", -121.7896, 36.8078),
        pier(4, "Veteran's Pier", "On the adjacent walking bridge a fishing license is required", -122.237, 37.748),
    ]
    path = tmp_path / "ds3090.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return path


def test_cdfw_public_piers_need_no_license_and_say_where_one_is(tmp_path):
    spots = {s["name"]: s for s in cdfw_piers.read(_cdfw_file(tmp_path))}
    hb = spots["Huntington Beach Pier"]
    assert hb["ref"] == "cdfw:huntington-beach-pier" and hb["kind"] == "pier"
    assert hb["no_license"] and hb["license_note"] is None and hb["state"] == "CA"
    assert spots["Newport Harbor North Jetty"]["kind"] == "jetty"
    assert spots["Newport Harbor North Jetty"]["license_note"] == "shore_wall"
    assert spots["Moss Landing Breakwater North"]["license_note"] == "shore_wall_and_inner_jetty"
    assert spots["Veteran's Pier"]["license_note"] == "footbridge"


def _ca(ref, name, kind="pier", lat=33.6556, lng=-118.0035, fishing=False, **extra):
    return _spot(ref, name, kind, lat=lat, lng=lng, state="CA", coast="pacific", fishing=fishing) | extra


def test_a_pier_in_both_sources_is_one_spot(tmp_path):
    cdfw = cdfw_piers.read(_cdfw_file(tmp_path))
    osm = [
        _ca("w1", "Huntington Beach Pier", lit=True),
        _ca("n2", None, "fishing_spot", lat=33.6557, lng=-118.0036, fishing=True),  # a fishing node on it
        _ca("w3", None, "boat_ramp", lat=33.6558, lng=-118.0030),
    ]
    spots = {s["ref"]: s for s in merge(osm, cdfw)}
    hb = spots["cdfw:huntington-beach-pier"]
    assert hb["source"] == "cdfw" and hb["osm_ref"] == "w1" and hb["lit"] and hb["no_license"]
    assert (hb["lat"], hb["lng"]) == (33.6556, -118.0035)  # where OpenStreetMap draws the pier
    assert "w1" not in spots and "n2" not in spots  # folded into the one spot
    assert spots["w3"]["kind"] == "boat_ramp"  # a ramp is never taken for a pier
    assert spots["cdfw:newport-harbor-north-jetty"]["osm_ref"] is None  # nothing mapped near it


def test_names_written_differently_still_match():
    cdfw = [
        {"ref": "cdfw:stearns", "name": "Stearn's Wharf", "kind": "pier", "lat": 34.4119, "lng": -119.6888, "state": "CA",
         "coast": "pacific", "no_license": True, "license_note": None},
        {"ref": "cdfw:bodega-s", "name": "Bodega Bay South Jetty", "kind": "jetty", "lat": 38.30455, "lng": -123.05393,
         "state": "CA", "coast": "pacific", "no_license": True, "license_note": None},
        {"ref": "cdfw:pier-45", "name": "Pier 45", "kind": "pier", "lat": 37.81086, "lng": -122.41994, "state": "CA",
         "coast": "pacific", "no_license": True, "license_note": None},
    ]
    osm = [
        _ca("w1", "Stearns Wharf", lat=34.4146, lng=-119.6886),  # 300 m off: CDFW marks the foot
        _ca("w2", "South Jetty", "jetty", lat=38.3027, lng=-123.0525),  # 220 m, the same side
        _ca("w3", "Hyde Street Pier", lat=37.80886, lng=-122.42094),  # 225 m: another pier
    ]
    spots = {s["ref"]: s for s in merge(osm, cdfw)}
    assert spots["cdfw:stearns"]["osm_ref"] == "w1"
    assert spots["cdfw:bodega-s"]["osm_ref"] == "w2"
    assert spots["cdfw:pier-45"]["osm_ref"] is None and "w3" in spots


def test_one_pier_mapped_twice_folds_but_numbered_piers_stay_apart():
    kept = {s["osm_ref"] for s in dedupe([
        _spot("w1", "Fishing Pier", lat=28.2909, lng=-96.8095),
        _spot("w2", "Fishing Pier", lat=28.2909, lng=-96.8093),
        _spot("w3", "Caldwell Pier", lat=27.8259, lng=-97.0506),
        _spot("w4", "Horace Caldwell Pier", lat=27.8272, lng=-97.0522),
        _spot("w5", "Shoreline Village Pier 1", lat=33.7577, lng=-118.1904),
        _spot("w6", "Shoreline Village Pier 2", lat=33.7572, lng=-118.1893),
        _spot("w7", "North Jetty", "jetty", lat=27.8363, lng=-97.0387),
        _spot("w8", "South Jetty", "jetty", lat=27.8304, lng=-97.0370),
    ])}
    assert len(kept & {"w1", "w2"}) == 1 and len(kept & {"w3", "w4"}) == 1
    assert {"w5", "w6", "w7", "w8"} <= kept


def test_import_is_idempotent_and_drops_spots_no_longer_mapped(db_session):
    assert run(db_session, _payload([_spot("w1"), _spot("n2", "South Jetty", "jetty", lat=27.7)])) == {
        "added": 2, "updated": 0, "removed": 0}
    assert run(db_session, _payload([_spot("w1", "Bob Hall Pier (rebuilt)")])) == {"added": 0, "updated": 1, "removed": 1}
    rows = db_session.query(CoastalSpot).all()
    assert [(r.ref, r.osm_ref, r.name, r.source) for r in rows] == [("w1", "w1", "Bob Hall Pier (rebuilt)", "osm")]
    record = db_session.get(SourceRecord, rows[0].source_record_id)
    assert record.licence_name == "ODbL 1.0" and record.licence_class == "OPEN"


def test_import_keeps_cdfw_facts_and_credit(db_session, tmp_path):
    cdfw = cdfw_piers.read(_cdfw_file(tmp_path))
    run(db_session, _payload([_ca("w1", "Huntington Beach Pier", lit=True)], states=("CA",)), cdfw)
    hb = db_session.query(CoastalSpot).filter_by(ref="cdfw:huntington-beach-pier").one()
    assert (hb.source, hb.osm_ref, hb.no_license, hb.lit) == ("cdfw", "w1", True, True)
    jetty = db_session.query(CoastalSpot).filter_by(ref="cdfw:newport-harbor-north-jetty").one()
    assert (jetty.kind, jetty.license_note, jetty.osm_ref) == ("jetty", "shore_wall", None)
    record = db_session.get(SourceRecord, hb.source_record_id)
    assert record.licence_name == "CC BY 4.0" and "Citing-BIOS" in record.citation
    assert db_session.query(CoastalSpot).count() == 4


def test_api_lists_spots_in_view_public_piers_first(client, db_session, tmp_path):
    cdfw = cdfw_piers.read(_cdfw_file(tmp_path))
    run(db_session, _payload([
        _spot("n5", None, "boat_ramp", fishing=False),
        _spot("w1"),
        _spot("w9", "Far Pier", lat=40.0, lng=-100.0),
        _ca("w2", "Huntington Beach Pier", lit=True),
    ], states=("TX", "CA")), cdfw)
    body = client.get("/api/coastal-spots", params={"bbox": "-98,27,-97,28"}).json()
    assert [s["name"] for s in body] == ["Bob Hall Pier", None]
    assert body[0]["osm_url"] == "https://www.openstreetmap.org/way/1" and body[0]["source"] == "osm"
    assert body[0]["source_url"] == body[0]["osm_url"] and not body[0]["no_license"]
    only_piers = client.get("/api/coastal-spots", params={"bbox": "-98,27,-97,28", "kind": "pier"}).json()
    assert [s["kind"] for s in only_piers] == ["pier"]
    ca = client.get("/api/coastal-spots", params={"state_code": "CA"}).json()
    assert all(s["no_license"] for s in ca) and len(ca) == 4
    hb = next(s for s in ca if s["name"] == "Huntington Beach Pier")
    assert hb["source"] == "cdfw" and hb["source_url"] == cdfw_piers.PAGE
    assert hb["osm_url"] == "https://www.openstreetmap.org/way/2" and hb["lit"]
    assert client.get("/api/coastal-spots", params={"bbox": "nonsense"}).status_code == 422
