"""Georgia WRD's access sites and fish attractors (app/data_import/ga_wrd_import.py).

Network-free. The site and attractor records are shaped like the real ones
(the first rows of WRD's two layers, trimmed), on OpenStreetMap lakes built
the way the OSM import builds them.
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest
from sqlalchemy import select

from app.data_import import ga_wrd_import as wrd
from app.data_import import osm_waterbody_import as osm
from app.knowledge.species_guides import GUIDES
from app.models.waterbody import AccessPoint, AgencyLakeProfile, FishAttractor, Waterbody
from tests.test_osm_import import _lake

FETCHED = "2026-10-19T12:00:00+00:00"


def _node(el_id, lat, lng, **tags):
    return {"type": "node", "id": el_id, "lat": lat, "lon": lng, "tags": {"leisure": "slipway", **tags}}


def _site(fid, name, waterbody, lat, lng, *, water_type="Small Impoundment", acres=300, status="Open",
          draw="Public", ramp="Y", species=("Largemouth", "Bluegill", "Redbreast")) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "FID": fid, "ID": fid, "Name": name, "Draw": draw, "Longitude": lng, "Latitude": lat,
        "Waterbody": waterbody, "WaterType": water_type, "County": "Cobb", "Ramp": ramp,
        "PierFish": "N", "BankFish": "Y", "Parking": "Y", "Status": status, "Acres": acres,
    }
    for f in wrd.SPECIES_FIELDS:
        attrs[f] = "Y" if f in species else "N"
    return {"attributes": attrs, "geometry": {"x": lng, "y": lat}}


def _attractor(gid, lat, lng, waterbody="Lake Acworth", kind="Trees/Brush", placed_ms=1488412800000):
    return {
        "attributes": {
            "objectid": 1, "globalid": gid, "latitude": lat, "longitude": lng, "placement_date": placed_ms,
            "waterbody": waterbody, "activity": "attractor", "attractor_name": kind, "units_no": 1, "deep": 12,
        },
        "geometry": {"x": lng, "y": lat},
    }


OSM = {
    "elements": [
        _lake(1, "Lake Acworth", 34.06, -84.68, half_deg=0.02),
        _lake(2, "Lake Buncombe", 33.57, -82.90, half_deg=0.004),
        # An OpenStreetMap entrance 30 m from a WRD ramp, and one 2 km away.
        _node(501, 34.0599, -84.6809),
        _node(502, 34.075, -84.665),
        # A pond whose name suggests private land, alone at its spot.
        _lake(3, "Pine Estates Lake", 33.00, -84.00, half_deg=0.003),
        _lake(4, "Lake Lanier", 34.20, -83.95, half_deg=0.15),
    ]
}


def _payload(features, **extra):
    return {"fetched_at": FETCHED, "features": features, **extra}


def _setup(db):
    osm.run("GA", OSM, db)
    db.flush()


def _lake_named(db, name) -> Waterbody:
    return db.scalars(select(Waterbody).where(Waterbody.name == name)).one()


def test_every_guide_species_wrd_lists_is_a_real_guide():
    guides = {g.common_name for g in GUIDES}
    for label, guide in wrd.SPECIES_FIELDS.values():
        assert guide is None or guide in guides, label


def test_a_site_on_a_lake_of_its_name_confirms_the_lake(db_session):
    _setup(db_session)
    summary = wrd.run(db_session, OSM, _payload([_site(5, "Acworth Beach", "Lake Acworth", 34.05965, -84.68112)]), None)

    wb = _lake_named(db_session, "Lake Acworth")
    assert wb.data_tier == "verified" and wb.public_access_status == "open"
    assert summary.lakes == {"osm_name": 1}
    confirmed = [ap for ap in wb.access_points if ap.public_status == "confirmed_public"]
    assert [(ap.name, ap.access_type, ap.parking) for ap in confirmed] == [("Acworth Beach", "boat_ramp", True)]
    # Guide species become confirmed links; Redbreast sunfish has no guide,
    # so it appears only in WRD's own list on the profile.
    assert sorted(link.species.common_name for link in wb.species_links) == ["Bluegill", "Largemouth Bass"]
    assert all(link.confidence == "confirmed" and "Acworth Beach" in link.evidence for link in wb.species_links)
    profile = wb.agency_profile
    assert profile.agency == "ga_wrd" and profile.agency_name == "Lake Acworth"
    assert profile.predominant_species == ["Bluegill", "Largemouth Bass", "Redbreast Sunfish"]
    assert profile.page_url == wrd.MAP_PAGE and profile.surface_acres == 300


def test_the_site_name_can_name_the_lake(db_session):
    _setup(db_session)
    site = _site(1, "A.H. Stephens SP - Lake Buncombe", "A. H. Stephens Lake", 33.568929, -82.902015, acres=14)
    wrd.run(db_session, OSM, _payload([site]), None)
    assert _lake_named(db_session, "Lake Buncombe").data_tier == "verified"


def test_a_nearby_osm_entrance_is_confirmed_and_a_far_one_is_kept(db_session):
    _setup(db_session)
    summary = wrd.run(db_session, OSM, _payload([_site(5, "Acworth Beach", "Lake Acworth", 34.05965, -84.68112)]), None)
    wb = _lake_named(db_session, "Lake Acworth")
    statuses = sorted((ap.public_status, ap.osm_ref) for ap in wb.access_points)
    assert statuses == [("confirmed_public", "ga_wrd/5"), ("osm_reported", "node/502")]
    assert summary.osm_entrances_confirmed == 1


def test_re_running_adds_nothing_twice_and_a_close_second_site_is_skipped(db_session):
    _setup(db_session)
    sites = _payload([
        _site(5, "Acworth Beach", "Lake Acworth", 34.05965, -84.68112),
        # 50 m from the first: the same place.
        _site(6, "Acworth Beach Pier", "Lake Acworth", 34.06010, -84.68112),
    ])
    first = wrd.run(db_session, OSM, sites, None)
    assert (first.access_added, first.access_skipped_duplicate) == (1, 1)
    second = wrd.run(db_session, OSM, sites, None)
    assert (second.access_added, second.access_updated) == (0, 1)
    wb = _lake_named(db_session, "Lake Acworth")
    assert sum(ap.public_status == "confirmed_public" for ap in wb.access_points) == 1
    assert len(wb.species_links) == 2
    assert db_session.scalar(select(AgencyLakeProfile).where(AgencyLakeProfile.agency == "ga_wrd")) is not None


def test_sites_that_are_not_open_public_lake_access_are_left_out(db_session):
    _setup(db_session)
    summary = wrd.run(db_session, OSM, _payload([
        _site(1, "Closed Ramp", "Lake Acworth", 34.05, -84.69, status="Closed"),
        _site(2, "Maybe Ramp", "Lake Acworth", 34.05, -84.69, status="Unknown"),
        _site(3, "Club Ramp", "Lake Acworth", 34.05, -84.69, draw="No"),
        _site(4, "River Ramp", "Etowah River", 34.05, -84.69, water_type="River"),
    ]), None)
    assert summary.sites_skipped == {
        "closed": 1, "status unknown": 1, "not listed as public": 1, "river, stream or coast": 1,
    }
    assert _lake_named(db_session, "Lake Acworth").data_tier == "osm"


def test_a_lake_with_no_outline_is_placed_at_its_sites_once(db_session):
    _setup(db_session)
    sites = _payload([
        _site(7, "Varner North Ramp", "Lake Varner", 33.60, -83.80, acres=850),
        _site(8, "Varner South Ramp", "Lake Varner", 33.59, -83.80, acres=850),
    ])
    first = wrd.run(db_session, OSM, sites, None)
    assert first.lakes == {"sites": 1}
    wb = _lake_named(db_session, "Lake Varner")
    assert wb.data_tier == "verified" and wb.agency_profile.placement == "sites"
    assert len(wb.access_points) == 2
    # Lake Varner has a WRD fishing forecast.
    assert wb.agency_profile.page_url == wrd.FORECASTS["varner"]
    wrd.run(db_session, OSM, sites, None)
    assert len(db_session.scalars(select(Waterbody).where(Waterbody.name == "Lake Varner")).all()) == 1


def test_a_position_only_match_never_opens_a_private_looking_pond(db_session):
    _setup(db_session)
    summary = wrd.run(db_session, OSM, _payload([_site(9, "Shady Oaks Ramp", "Shady Oaks Lake", 33.0, -84.0, acres=5)]), None)
    assert summary.sites_unplaced and summary.lakes == {}
    pond = _lake_named(db_session, "Pine Estates Lake")
    assert pond.data_tier == "osm" and pond.public_access_status == "likely_private"


def test_a_position_only_match_must_be_about_the_right_size(db_session):
    _setup(db_session)
    # Inside Lake Lanier's box under another name, but WRD says 5 acres.
    site = _site(10, "Some Ramp", "Tiny Lake", 34.20, -83.95, acres=5)
    summary = wrd.run(db_session, OSM, _payload([site]), None)
    assert summary.lakes == {} and summary.sites_unplaced
    # The real Lanier ramp is matched by name and gets Lanier's forecast.
    lanier = _site(11, "Old Federal Park", "Lake Sidney Lanier", 34.21, -83.94, water_type="Major Reservoir", acres=38000)
    wrd.run(db_session, OSM, _payload([lanier]), None)
    assert _lake_named(db_session, "Lake Lanier").agency_profile.page_url == wrd.FORECASTS["lanier"]


def test_a_pond_sharing_a_forecast_lakes_name_gets_no_forecast():
    small = wrd.Site(1, "Jackson Pond Ramp", "Jackson Lake", "Small Impoundment", "Butts", 0, 0, 12, "bank", False, ())
    big = wrd.Site(2, "Ramp", "Jackson Lake", "Major Reservoir", "Butts", 0, 0, 4750, "boat_ramp", True, ())
    assert wrd.forecast_for([small]) is None
    assert wrd.forecast_for([big]) == wrd.FORECASTS["jackson"]


def test_attractors_go_on_the_lake_that_holds_them_and_are_replaced_each_run(db_session, client):
    _setup(db_session)
    attractors = _payload([
        _attractor("a1", 34.061, -84.681),
        _attractor("a2", 34.062, -84.682, kind="PVC Trees"),
        _attractor("far", 31.0, -82.0),  # in no lake on the map
    ])
    sites = _payload([_site(5, "Acworth Beach", "Lake Acworth", 34.05965, -84.68112)])
    summary = wrd.run(db_session, OSM, sites, attractors)
    assert (summary.attractors_saved, summary.attractors_not_in_a_lake, summary.attractor_lakes) == (2, 1, 1)
    wrd.run(db_session, OSM, sites, attractors)
    assert len(db_session.scalars(select(FishAttractor)).all()) == 2
    db_session.commit()

    wb = _lake_named(db_session, "Lake Acworth")
    body = client.get(f"/api/waterbodies/{wb.id}").json()
    assert sorted(a["attractor_type"] for a in body["fish_attractors"]) == ["PVC Trees", "Trees/Brush"]
    assert {a["placed_year"] for a in body["fish_attractors"]} == {2017}
    assert body["agency_profile"]["agency"] == "ga_wrd"


def test_a_closed_lake_shows_no_attractors(db_session, client):
    _setup(db_session)
    wrd.run(db_session, OSM, _payload([]), _payload([_attractor("a1", 34.061, -84.681)]))
    wb = _lake_named(db_session, "Lake Acworth")
    wb.public_access_status = "closed"
    db_session.commit()
    assert client.get(f"/api/waterbodies/{wb.id}").json()["fish_attractors"] == []


class FakeClient:
    def __init__(self, pages: list[list[dict]]):
        self.pages = pages
        self.offsets: list[str] = []

    def get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        params = params or {}
        self.offsets.append(params["resultOffset"])
        i = len(self.offsets) - 1
        body = {"features": self.pages[i], "exceededTransferLimit": i < len(self.pages) - 1}
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))


def test_fetch_pages_until_the_layer_says_it_is_done(monkeypatch):
    monkeypatch.setattr(wrd, "REQUEST_DELAY_S", 0)
    client = FakeClient([[{"attributes": {"FID": 1}}, {"attributes": {"FID": 2}}], [{"attributes": {"FID": 3}}]])
    features = wrd.fetch_layer(client, wrd.ACCESS_LAYER, "1=1", "FID")  # type: ignore[arg-type]
    assert [f["attributes"]["FID"] for f in features] == [1, 2, 3]
    assert client.offsets == ["0", "2"]


def test_an_arcgis_error_stops_the_fetch(monkeypatch):
    monkeypatch.setattr(wrd, "REQUEST_DELAY_S", 0)

    class Err:
        def get(self, url, params=None):
            return httpx.Response(200, json={"error": {"code": 400}}, request=httpx.Request("GET", url))

    with pytest.raises(RuntimeError):
        wrd.fetch_layer(Err(), wrd.ACCESS_LAYER, "1=1", "FID")  # type: ignore[arg-type]


def test_no_georgia_lakes_means_run_the_osm_import_first(db_session):
    with pytest.raises(ValueError):
        wrd.run(db_session, OSM, _payload([]), None)


def test_access_points_are_written_with_the_wrd_ref(db_session):
    _setup(db_session)
    wrd.run(db_session, OSM, _payload([_site(5, "Acworth Beach", "Lake Acworth", 34.05965, -84.68112)]), None)
    ap = db_session.scalars(select(AccessPoint).where(AccessPoint.osm_ref == "ga_wrd/5")).one()
    assert ap.public_status == "confirmed_public"


def test_sites_just_past_a_named_lakes_box_join_that_lake_rather_than_make_a_twin(db_session):
    _setup(db_session)
    # Lake Acworth's box ends at 34.08; this ramp is ~2 km beyond it.
    summary = wrd.run(db_session, OSM, _payload([_site(12, "North Ramp", "Lake Acworth", 34.10, -84.68)]), None)
    assert summary.lakes == {"osm_name": 1}
    assert len(db_session.scalars(select(Waterbody).where(Waterbody.name == "Lake Acworth")).all()) == 1
    assert _lake_named(db_session, "Lake Acworth").data_tier == "verified"


def test_wrds_id_column_repeats_so_the_unique_fid_is_the_key(db_session):
    _setup(db_session)
    a = _site(5, "Acworth Beach", "Lake Acworth", 34.05965, -84.68112)
    b = _site(6, "Far Ramp", "Lake Acworth", 34.10, -84.68)
    a["attributes"]["ID"] = b["attributes"]["ID"] = 0  # as on many real rows
    summary = wrd.run(db_session, OSM, _payload([a, b]), None)
    assert summary.access_added == 2
    refs = sorted(ap.osm_ref for ap in db_session.scalars(select(AccessPoint)) if ap.osm_ref.startswith("ga_wrd/"))
    assert refs == ["ga_wrd/5", "ga_wrd/6"]


def test_a_site_whose_coordinate_fields_are_zero_or_empty_uses_its_geometry():
    zero = _site(7, "Little Ridge Park", "Lake Lanier", 0, 0)
    zero["geometry"] = {"x": -84.09, "y": 34.19}
    empty = _site(8, "No Name", "Lake Lanier", 0, 0)
    empty["attributes"].update({"Latitude": None, "Longitude": None, "Name": None, "Waterbody": None})
    empty["geometry"] = {"x": -83.94, "y": 31.84}
    sites, _ = wrd.parse_sites([zero, empty])
    assert [(s.latitude, s.longitude) for s in sites] == [(34.19, -84.09), (31.84, -83.94)]
    assert sites[1].name == "Public access" and sites[1].waterbody == ""


def test_an_attractor_outside_every_outline_joins_the_lake_its_name_says(db_session):
    _setup(db_session)
    # A PFA lake OpenStreetMap doesn't have: placed at WRD's site, then an
    # attractor 400 m from the site, outside any outline, filed under its name.
    sites = _payload([_site(30, "Fox Lake PFA ramp", "Fox Lake", 33.20, -83.50, acres=95)])
    wrd.run(db_session, OSM, sites, _payload([
        _attractor("p1", 33.2035, -83.5005, waterbody="Fox Lake"),
        _attractor("p2", 33.2035, -83.5005, waterbody="Some Other Pond"),  # no name match: nearest sites-lake
        _attractor("p3", 33.30, -83.50, waterbody="Some Other Pond"),  # 11 km off: left out
    ]))
    fox = _lake_named(db_session, "Fox Lake")
    assert sorted(a.source_record_id for a in db_session.scalars(select(FishAttractor)) if a.waterbody_id == fox.id) == ["p1", "p2"]
    assert len(db_session.scalars(select(FishAttractor)).all()) == 2


def test_a_wetland_is_not_a_lake_name(db_session):
    _setup(db_session)
    summary = wrd.run(db_session, OSM, _payload([_site(31, "Grand Bay WMA", "Wetland", 30.93, -83.19, acres=13000)]), None)
    assert summary.lakes == {} and summary.sites_unplaced
