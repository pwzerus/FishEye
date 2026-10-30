"""Catches are on named water (ADR 0040): the shapes, the lookup, and what
pins do with it."""
from __future__ import annotations

import io
import json
import math

import pytest
from PIL import ExifTags, Image
from sqlalchemy import select

from app.models.community import CatchPin
from app.models.water import River, RiverReach, WaterPiece, cell_of
from app.models.waterbody import Waterbody
from app.services import water
from tests.conftest import signup

# Lake Fork (the seeded lake) drawn as a box 0.02° on a side around its
# centre, and a river ("Sabine River") running east-west 3 km south of it,
# in Wood County, Texas.
FORK = (32.8065, -95.5931)
LAKE_RING = [(32.7965, -95.6031), (32.7965, -95.5831), (32.8165, -95.5831), (32.8165, -95.6031), (32.7965, -95.6031)]
RIVER_LINE = [(32.7790, -95.6200), (32.7790, -95.5800)]
REACH = (32.7790, -95.6000)
M_PER_DEG_LAT = 110_574.0


def north_of_lake(metres: float) -> tuple[float, float]:
    return 32.8165 + metres / M_PER_DEG_LAT, FORK[1]


def add_lake_outline(db, waterbody_id: int, ring=LAKE_RING, state="TX") -> None:
    lat = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
    lng = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
    db.add(WaterPiece(state_code=state, waterbody_id=waterbody_id, shape="area", cell=cell_of(lat, lng),
                      geometry=json.dumps([[water.encode(ring)]])))


def add_river(db, state_id: int, name="Sabine River", line=RIVER_LINE, reach=REACH, state="TX") -> River:
    river = River(state_id=state_id, name=name, waterway="river", osm_ref=f"way/{name}", latitude=reach[0],
                  longitude=reach[1], length_km=4.0, source_url="https://www.openstreetmap.org/relation/1")
    db.add(river)
    db.flush()
    db.add(RiverReach(river_id=river.id, county_geoid="48499", county_name="Wood County",
                      latitude=reach[0], longitude=reach[1]))
    mid = ((line[0][0] + line[-1][0]) / 2, (line[0][1] + line[-1][1]) / 2)
    db.add(WaterPiece(state_code=state, river_id=river.id, shape="line", cell=cell_of(*mid),
                      geometry=json.dumps([water.encode(line)])))
    return river


@pytest.fixture()
def shaped(db_session, seeded_lake):
    """Texas with its shapes imported: Lake Fork's outline and one river."""
    add_lake_outline(db_session, seeded_lake["waterbody"].id)
    river = add_river(db_session, seeded_lake["state"].id)
    db_session.commit()
    return {**seeded_lake, "river": river}


def create(c, lat, lng, photos=(), **fields):
    data = {"latitude": lat, "longitude": lng, "title": "Evening bite", **fields}
    files = [("photos", (f"p{i}.jpg", b, "image/jpeg")) for i, b in enumerate(photos)]
    return c.post("/api/pins", data=data, files=files or None)


def photo_taken_at(lat: float, lng: float) -> bytes:
    def dms(value: float) -> tuple[float, float, float]:
        value = abs(value)
        d = int(value)
        m = int((value - d) * 60)
        return float(d), float(m), round((value - d - m / 60) * 3600, 3)

    exif = Image.Exif()
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N" if lat >= 0 else "S"
    gps[ExifTags.GPS.GPSLatitude] = dms(lat)
    gps[ExifTags.GPS.GPSLongitudeRef] = "E" if lng >= 0 else "W"
    gps[ExifTags.GPS.GPSLongitude] = dms(lng)
    out = io.BytesIO()
    Image.new("RGB", (800, 600), "green").save(out, format="JPEG", exif=exif)
    return out.getvalue()


# ----------------------------------------------------------- the geometry


def test_encoded_polylines_round_trip_to_a_metre():
    points = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453), (-33.86785, 151.20732)]
    decoded = water.decode(water.encode(points))
    assert len(decoded) == len(points)
    assert all(abs(a - b) <= 1e-5 for p, q in zip(points, decoded) for a, b in zip(p, q))
    # Google's documented example.
    assert water.encode([(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]) == "_p~iF~ps|U_ulLnnqC_mqNvxq`@"


def test_distance_is_zero_inside_an_outline_and_metres_outside():
    geometry = json.dumps([[water.encode(LAKE_RING)]])
    assert water.piece_distance("area", geometry, *FORK) == 0.0
    assert water.piece_distance("area", geometry, *north_of_lake(100)) == pytest.approx(100, abs=2)
    line = json.dumps([water.encode(RIVER_LINE)])
    assert water.piece_distance("line", line, 32.7790 + 50 / M_PER_DEG_LAT, -95.6) == pytest.approx(50, abs=2)


def test_an_island_is_not_on_the_water_but_its_shore_is_near_it():
    island = [(32.8040, -95.5960), (32.8040, -95.5900), (32.8090, -95.5900), (32.8090, -95.5960), (32.8040, -95.5960)]
    geometry = json.dumps([[water.encode(LAKE_RING), water.encode(island)]])
    assert water.piece_distance("area", geometry, *FORK) > 0
    assert water.piece_distance("area", geometry, 32.8020, -95.5931) == 0.0  # between island and shore


# ------------------------------------------------------------- the lookup


def test_on_the_water_or_its_bank_counts_further_out_does_not(db_session, shaped):
    lake_id = shaped["waterbody"].id
    assert water.find_water(db_session, *FORK) == water.WaterMatch("lake", lake_id, "Lake Fork", 0.0)
    bank = water.find_water(db_session, *north_of_lake(60))
    assert bank is not None and bank.kind == "lake" and bank.distance_m == pytest.approx(60, abs=2)
    assert water.find_water(db_session, *north_of_lake(water.SNAP_M + 50)) is None


def test_a_named_river_is_water_too(db_session, shaped):
    match = water.find_water(db_session, 32.7790 + 30 / M_PER_DEG_LAT, -95.6050)
    assert match is not None and (match.kind, match.name) == ("river", "Sabine River")


def test_inside_a_lake_beats_a_river_line_running_through_it(db_session, shaped):
    through = [(FORK[0], -95.6100), (FORK[0], -95.5700)]
    add_river(db_session, shaped["state"].id, name="Lake Fork Creek", line=through)
    db_session.commit()
    assert water.find_water(db_session, *FORK).kind == "lake"


def test_a_verified_lake_beats_its_openstreetmap_double(db_session, shaped):
    double = Waterbody(state_id=shaped["state"].id, name="Lake Fork Reservoir", latitude=FORK[0], longitude=FORK[1],
                       access_summary="", source_url="", source_updated_at=shaped["waterbody"].source_updated_at,
                       data_tier="osm")
    db_session.add(double)
    db_session.flush()
    add_lake_outline(db_session, double.id)
    db_session.commit()
    assert water.find_water(db_session, *FORK).id == shaped["waterbody"].id


def test_a_lake_with_no_outline_is_matched_by_its_box_or_near_its_centre(db_session, seeded_lake):
    wb = seeded_lake["waterbody"]
    assert water.find_water(db_session, FORK[0] + 0.002, FORK[1]).id == wb.id  # ~220 m: within 300 m
    assert water.find_water(db_session, FORK[0] + 0.01, FORK[1]) is None  # ~1.1 km
    wb.bbox_south, wb.bbox_west, wb.bbox_north, wb.bbox_east = 32.79, -95.61, 32.83, -95.57
    db_session.commit()
    assert water.find_water(db_session, 32.825, -95.60).id == wb.id


def test_a_state_is_held_to_the_rule_once_its_shapes_are_in(db_session, shaped):
    assert water.data_ready(db_session, "TX") and water.data_ready(db_session, "tx")
    assert not water.data_ready(db_session, "GA") and not water.data_ready(db_session, None)


# ------------------------------------------------------------------- pins


def test_a_catch_off_the_water_is_refused_where_the_shapes_are_in(make_client, shaped):
    c = make_client()
    signup(c)
    resp = create(c, 32.86, -95.50)  # fields east of the lake
    assert resp.status_code == 422
    assert "on the water" in resp.json()["detail"]


def test_without_shapes_a_catch_anywhere_is_still_allowed(make_client, seeded_lake):
    c = make_client()
    signup(c)
    resp = create(c, 32.86, -95.50)
    assert resp.status_code == 201, resp.text
    assert resp.json()["water"] is None


def test_a_catch_on_the_bank_is_on_the_lake(make_client, db_session, shaped):
    c = make_client()
    signup(c)
    pin = create(c, *north_of_lake(40)).json()
    assert pin["water"] == {"kind": "lake", "id": shaped["waterbody"].id, "name": "Lake Fork"}
    assert pin["lake"]["name"] == "Lake Fork"
    row = db_session.get(CatchPin, pin["id"])
    assert row.water_distance_m == pytest.approx(40, abs=2) and row.river_id is None


def test_others_see_a_river_catch_at_the_rivers_point_in_its_county(make_client, shaped):
    owner = make_client()
    signup(owner)
    spot = (32.7790 + 20 / M_PER_DEG_LAT, -95.5870)
    pin = create(owner, *spot).json()
    assert pin["water"] == {"kind": "river", "id": shaped["river"].id, "name": "Sabine River"}
    assert (pin["latitude"], pin["longitude"]) == pytest.approx(spot)  # the owner sees the spot
    other = make_client().get(f"/api/pins/{pin['id']}").json()
    assert other["location_shown"] == "river" and other["public_place"] == "river"
    assert (other["latitude"], other["longitude"]) == pytest.approx(REACH)


def test_where_says_which_water_a_catch_there_would_be_on(make_client, shaped):
    anon = make_client()
    on = anon.get("/api/pins/where", params={"lat": FORK[0], "lng": FORK[1]}).json()
    assert on["water"] == {"kind": "lake", "id": shaped["waterbody"].id, "name": "Lake Fork", "distance_m": 0.0}
    assert on["water_required"] is True
    off = anon.get("/api/pins/where", params={"lat": 32.86, "lng": -95.50}).json()
    assert off["water"] is None and off["water_required"] is True


def test_a_catch_can_be_moved_onto_other_water_but_not_onto_land(make_client, db_session, shaped):
    c = make_client()
    signup(c)
    pin = create(c, *FORK).json()
    moved = c.patch(f"/api/pins/{pin['id']}", json={"latitude": 32.7790, "longitude": -95.6100})
    assert moved.status_code == 200, moved.text
    assert moved.json()["water"]["kind"] == "river"
    assert moved.json()["public_place"] == "river"
    refused = c.patch(f"/api/pins/{pin['id']}", json={"latitude": 32.86, "longitude": -95.50})
    assert refused.status_code == 422
    row = db_session.get(CatchPin, pin["id"])
    db_session.refresh(row)
    assert (row.latitude, row.longitude) == (32.779, -95.61) and row.river_id == shaped["river"].id
    assert c.patch(f"/api/pins/{pin['id']}", json={"latitude": 32.8}).status_code == 422


def test_the_map_counts_other_peoples_catches_per_water(make_client, shaped):
    a, b, me = make_client(), make_client(), make_client()
    signup(a, "a@example.com", "Ann")
    signup(b, "b@example.com", "Bo")
    signup(me, "me@example.com", "Me")
    assert create(a, *FORK, species_slug="largemouth-bass").status_code == 201
    assert create(b, *north_of_lake(30), species_slug="largemouth-bass").status_code == 201
    assert create(b, 32.7790, -95.6100, species_other="Gar").status_code == 201
    assert create(me, *FORK).status_code == 201  # mine: drawn one by one, not counted here
    bbox = "-95.7,32.7,-95.5,32.9"
    groups = {g["kind"]: g for g in me.get("/api/pins/waters", params={"bbox": bbox}).json()}
    assert groups["lake"]["count"] == 2 and groups["lake"]["name"] == "Lake Fork"
    assert (groups["lake"]["latitude"], groups["lake"]["longitude"]) == pytest.approx(FORK)
    assert groups["lake"]["species"] == ["Largemouth Bass"]
    assert groups["river"]["count"] == 1 and groups["river"]["county_name"] == "Wood County"
    assert (groups["river"]["latitude"], groups["river"]["longitude"]) == pytest.approx(REACH)
    anon_lake = next(g for g in make_client().get("/api/pins/waters", params={"bbox": bbox}).json() if g["kind"] == "lake")
    assert anon_lake["count"] == 3
    # A water's catches, as the map's list opens them.
    river_titles = make_client().get("/api/pins", params={"river": shaped["river"].id}).json()
    assert [p["water"]["name"] for p in river_titles] == ["Sabine River"]


def test_a_county_lists_its_rivers_beside_its_lakes(make_client, shaped):
    c = make_client()
    signup(c)
    create(c, *FORK)
    create(c, 32.7790, -95.6100)
    places = make_client().get("/api/pins/places", params={"county": "48499"}).json()["places"]
    assert [(p["id"], p["name"]) for p in places] == [
        (str(shaped["waterbody"].id), "Lake Fork"), (f"r{shaped['river'].id}", "Sabine River"),
    ] or [(p["id"], p["name"]) for p in places] == [
        (f"r{shaped['river'].id}", "Sabine River"), (str(shaped["waterbody"].id), "Lake Fork"),
    ]


def test_a_photo_taken_at_the_spot_earns_a_badge(make_client, shaped):
    c = make_client()
    signup(c)
    here = create(c, *FORK, photos=[photo_taken_at(FORK[0] + 0.001, FORK[1])]).json()
    assert here["photo_at_spot"] is True
    elsewhere = create(c, *FORK, photos=[photo_taken_at(30.27, -97.74)]).json()  # Austin
    assert elsewhere["photo_at_spot"] is False
    # Moving the catch away from where its photo was taken loses the badge.
    moved = c.patch(f"/api/pins/{here['id']}", json={"latitude": 32.7790, "longitude": -95.6100}).json()
    assert moved["photo_at_spot"] is False
    # The photo's own location is never sent, not even to its owner.
    assert "gps" not in json.dumps(c.get(f"/api/pins/{here['id']}").json()).lower()


def test_pins_saved_before_are_checked_against_the_shapes_at_startup(make_client, db_session, shaped):
    from app.services.pins import fill_water

    c = make_client()
    signup(c)
    on_lake = create(c, *north_of_lake(20)).json()["id"]
    on_land = create(c, *north_of_lake(20)).json()["id"]
    # As they were before ADR 0040: never checked, linked by the old 3 km rule.
    for pin_id, spot in ((on_lake, north_of_lake(20)), (on_land, (32.83, -95.5931))):
        row = db_session.get(CatchPin, pin_id)
        row.latitude, row.longitude = spot
        row.water_distance_m, row.waterbody_id, row.river_id = None, shaped["waterbody"].id, None
    db_session.commit()
    assert fill_water(db_session) == 2
    lake_pin, land_pin = db_session.get(CatchPin, on_lake), db_session.get(CatchPin, on_land)
    assert lake_pin.waterbody_id == shaped["waterbody"].id and lake_pin.water_distance_m == pytest.approx(20, abs=2)
    assert land_pin.waterbody_id is None and land_pin.water_distance_m == -1.0
    assert land_pin.public_place == "county"
    assert fill_water(db_session) == 0  # once only


# ----------------------------------------------------------------- import


def _payload(lake_ref: str, rivers: list[dict]) -> dict:
    ring = json.dumps([[water.encode(LAKE_RING)]])
    return {
        "lakes": {lake_ref: [[cell_of(*FORK), "area", json.loads(ring)]]},
        "orphans": {},
        "rivers": rivers,
    }


def _river(ref: str, name: str) -> dict:
    return {"ref": ref, "name": name, "waterway": "river", "lat": REACH[0], "lng": REACH[1], "length_km": 4.0,
            "reaches": [["48499", "Wood County", REACH[0], REACH[1]]],
            "pieces": [[cell_of(*REACH), "line", [water.encode(RIVER_LINE)]]]}


def test_an_import_replaces_the_states_shapes_and_keeps_river_ids(db_session, seeded_lake):
    from app.data_import.water_shapes import import_payload

    wb = seeded_lake["waterbody"]
    wb.osm_ref = "relation/77"
    db_session.commit()
    counts = import_payload(db_session, "TX", _payload("relation/77", [_river("relation/1", "Sabine River")]))
    db_session.commit()
    assert counts["lakes"] == 1 and counts["rivers"] == 1 and counts["pieces"] == 2
    sabine = db_session.scalar(select(River.id).where(River.name == "Sabine River"))
    assert water.find_water(db_session, *FORK).id == wb.id

    again = _payload("relation/77", [_river("relation/1", "Sabine River"), _river("way/9", "Big Sandy Creek")])
    import_payload(db_session, "TX", again)
    db_session.commit()
    assert db_session.scalar(select(River.id).where(River.name == "Sabine River")) == sabine
    assert db_session.query(WaterPiece).count() == 3
    assert db_session.query(RiverReach).count() == 2

    import_payload(db_session, "TX", _payload("relation/77", []))
    db_session.commit()
    assert db_session.query(River).count() == 0 and db_session.query(RiverReach).count() == 0


def test_an_import_gives_verified_lakes_without_a_twin_their_outline(db_session, seeded_lake):
    from app.data_import.water_shapes import import_payload, orphan_key

    payload = {"lakes": {}, "rivers": [], "orphans": {orphan_key(*FORK): [[cell_of(*FORK), "area", [[water.encode(LAKE_RING)]]]]}}
    counts = import_payload(db_session, "TX", payload)
    db_session.commit()
    assert counts["verified_outlines"] == 1
    assert db_session.scalar(select(WaterPiece.waterbody_id)) == seeded_lake["waterbody"].id


# ---------------------------------------------------------------- extract


OSM_XML = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6" generator="test">
  {nodes}
  <way id="100"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
    <tag k="natural" v="water"/><tag k="water" v="reservoir"/><tag k="name" v="Lake Fork"/></way>
  <way id="200"><nd ref="10"/><nd ref="11"/><tag k="waterway" v="river"/><tag k="name" v="Sabine River"/></way>
  <way id="201"><nd ref="11"/><nd ref="12"/><tag k="waterway" v="river"/><tag k="name" v="Sabine River"/></way>
  <way id="300"><nd ref="20"/><nd ref="21"/><tag k="waterway" v="stream"/><tag k="name" v="Tiny Branch"/></way>
  <way id="400"><nd ref="30"/><nd ref="31"/><nd ref="32"/><nd ref="33"/><nd ref="30"/>
    <tag k="natural" v="water"/></way>
</osm>
"""
NODES = {
    1: LAKE_RING[0], 2: LAKE_RING[1], 3: LAKE_RING[2], 4: LAKE_RING[3],
    10: (32.7790, -95.6400), 11: (32.7790, -95.6000), 12: (32.7790, -95.5600),
    20: (32.7500, -95.6000), 21: (32.7520, -95.6000),  # ~220 m: under MIN_STREAM_KM
    # An unnamed pond around a verified lake with no OpenStreetMap twin.
    30: (32.7000, -95.7000), 31: (32.7000, -95.6980), 32: (32.7020, -95.6980), 33: (32.7020, -95.7000),
}


def test_the_extract_joins_a_rivers_ways_and_outlines_lakes(tmp_path):
    pytest.importorskip("osmium")
    pytest.importorskip("shapely")
    from app.data_import.water_shapes import extract, orphan_key

    nodes = "\n  ".join(f'<node id="{i}" lat="{lat}" lon="{lng}" version="1"/>' for i, (lat, lng) in NODES.items())
    osm = tmp_path / "tiny.osm"
    osm.write_text(OSM_XML.format(nodes=nodes), encoding="utf-8")
    lakes_payload = {"elements": [{"type": "way", "id": 100, "bounds": {
        "minlat": LAKE_RING[0][0], "minlon": LAKE_RING[0][1], "maxlat": LAKE_RING[2][0], "maxlon": LAKE_RING[2][1]},
        "tags": {"natural": "water", "water": "reservoir", "name": "Lake Fork"}}]}
    payload = extract(osm, "TX", lakes_payload, orphans=[(32.7010, -95.6990)])

    assert list(payload["lakes"]) == ["way/100"]
    [river] = payload["rivers"]  # the short stream is left out
    assert (river["name"], river["waterway"], river["ref"]) == ("Sabine River", "river", "way/200")
    assert river["length_km"] == pytest.approx(7.5, rel=0.05)
    assert [r[:2] for r in river["reaches"]] == [["48499", "Wood County"]]
    assert orphan_key(32.7010, -95.6990) in payload["orphans"]
    # Every piece fits one grid cell, and decodes.
    for cell, shape, parts in payload["lakes"]["way/100"] + river["pieces"]:
        flat = [pt for part in parts for ring in (part if shape == "area" else [part]) for pt in water.decode(ring)]
        lats, lngs = [p[0] for p in flat], [p[1] for p in flat]
        assert max(lats) - min(lats) <= 0.05 + 1e-6 and max(lngs) - min(lngs) <= 0.05 + 1e-6
        assert not math.isnan(sum(lats))
