"""Named water with no water=* tag (docs/adr/0036): which is a lake."""
import pytest
from sqlalchemy import select

from app.data_import import geofabrik_lakes as gf
from app.data_import import osm_waterbody_import as osm
from app.data_import.untyped_water import (
    FACILITY_NAMES,
    FACILITY_TAGS,
    Verdict,
    facility_kinds,
    judge,
    named_facilities,
)
from app.models.waterbody import Waterbody


@pytest.mark.parametrize(
    ("name", "water_type"),
    [
        ("Mud Lake", "lake"),
        ("Lake Butler", "lake"),
        ("Lake of the Woods", "lake"),
        ("Fountain Lake", "lake"),  # a lake word last wins over the other word
        ("Storm Lake", "lake"),
        ("Big Lake", "lake"),
        ("Whortleberry Pond", "pond"),
        ("North Pond", "pond"),
        ("Duessen Reservoir", "reservoir"),
        ("Hay Creek Flowage", "lake"),
        ("Jesse McNeel Lake Number 2", "lake"),
        ("Metcalf Chain of Lakes", "lake"),
        ("Argo Lake (Hamilton County)", "lake"),
        ("Eagles Nest Lake Number One", "lake"),
        ("West Lake Ellen", "lake"),
        ("Upper Lake Mary", "lake"),
        ("Loch Sheldrake", "lake"),
        ("Colton Flow", "reservoir"),
    ],
)
def test_lake_names_are_kept_with_their_water_type(name, water_type):
    assert judge(name, {}).water_type == water_type


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("Retention Pond", "not_fishing"),
        ("Stormwater Pond 4", "not_fishing"),
        ("Wastewater Treatment Basin", "not_fishing"),
        ("Eveleth Taconite Tailings Basin", "not_fishing"),
        ("Fire Pond", "not_fishing"),
        ("Golf Course Pond", "not_fishing"),
        ("Clear Lakebed", "not_fishing"),
        ("Argo Lake (historical)", "not_fishing"),
        ("Dry Lake", "not_fishing"),
        ("Acid Mine Drainage Catch Pond", "not_fishing"),
        ("Industrial Waste Ponds", "not_fishing"),
        ("West Lake Creek", "not_lake"),
        ("Demopolis Country Club Lake", "facility"),
        ("Newgate Sportsmens Club Pond No 1", "facility"),
        ("Salisbury School Pond", "facility"),
        ("School Lake", "facility"),
        ("Fishtown Cemetery Pond", "facility"),
        ("Hermann Hospital Lake", "facility"),
        ("Manor Inn Pond", "facility"),
        ("Oakridge Estates Lake", "facility"),
        ("Plaza Lake", "facility"),
        ("Cement Plant Pond", "facility"),
        ("Zoo Lake", "facility"),
        ("The Flow", "generic"),
        ("Pine River", "not_lake"),
        ("Lake Creek", "not_lake"),
        ("Lake Shore Pool", "not_lake"),
        ("Mallard Marsh", "not_lake"),
        ("Seven Seas Lagoon", "not_lake"),
        ("Smith Tank", "not_lake"),
        ("Blue Hole", "not_lake"),
        ("Pond 3", "generic"),
        ("The Pond", "generic"),
        ("Lake A", "generic"),
        ("Reservoir No. 1", "generic"),
    ],
)
def test_other_names_are_left_out_with_a_reason(name, reason):
    verdict = judge(name, {})
    assert verdict.water_type is None and verdict.reason == reason


@pytest.mark.parametrize(
    ("tags", "reason"),
    [
        ({"intermittent": "yes"}, "intermittent"),
        ({"seasonal": "yes"}, "intermittent"),
        ({"salt": "yes"}, "salt_or_tidal"),
        ({"leisure": "swimming_pool"}, "pool_or_fountain"),
        ({"amenity": "fountain"}, "pool_or_fountain"),
        ({"basin": "detention"}, "man_made"),
        ({"man_made": "reservoir_covered"}, "man_made"),
        ({"golf": "water_hazard"}, "golf"),
        ({"covered": "yes"}, "covered"),
        ({"disused:water": "reservoir"}, "disused"),
        ({"wetland": "marsh"}, "wetland"),
        ({"tourism": "zoo"}, "attraction"),
    ],
)
def test_tags_that_say_it_is_something_else_leave_a_lake_name_out(tags, reason):
    verdict = judge("Mud Lake", tags)
    assert verdict.water_type is None and verdict.reason == reason


def test_a_facility_name_is_left_out_only_when_that_facility_is_mapped_near():
    # Nobody checked (an older payload): left out, to be safe.
    assert judge("School Lake", {}).reason == "facility"
    # Checked, and no school near: a place name ("School Lake", a school section).
    assert judge("School Lake", {}, facilities_near=[]) == Verdict("lake", "ok")
    assert judge("Church Lake", {}, facilities_near=[]).water_type == "lake"
    assert judge("Lake Seminary", {}, facilities_near=[]).water_type == "lake"
    # A school next to it: the school's pond.
    assert judge("Salisbury School Pond", {}, facilities_near=["education"]).reason == "facility"
    # Something else near, not what the name says: still a place name.
    assert judge("Cemetery Pond", {}, facilities_near=["education"]).water_type == "pond"
    # The other rules still apply to a place name.
    assert judge("Club Creek", {}, facilities_near=[]).reason == "not_lake"


@pytest.mark.parametrize(
    ("name", "places", "reason"),
    [
        # One particular facility, even if OpenStreetMap hasn't mapped it.
        ("Salisbury School Pond", [], "facility_name"),
        ("Fin and Feathers Club Lake", [], "facility_name"),
        ("Town Creek Country Club Lake", [], "facility_name"),
        ("Lakeside Estates Lake", [], "facility_name"),
        ("Cement Plant Pond", [], "facility_name"),
        # The facility word leads: a place name.
        ("School Lake", [], "ok"),
        ("North School Section Lake", [], "ok"),
        ("Lower Church Lake", [], "ok"),
        ("Club Lake", [], "ok"),
        ("Lake Seminary", [], "ok"),
        ("Hospital Lake Number One", [], "ok"),
        # The words are a town mapped nearby.
        ("Ball Club Lake", ["Ball Club"], "ok"),
        ("Little Ball Club Lake", ["Ball Club"], "ok"),
        ("Ball Club Lake", [], "facility_name"),
        # A nearby place that doesn't hold the facility word doesn't help.
        ("Salisbury School Pond", ["Salisbury"], "facility_name"),
        # A housing estate is its own place: no rescue.
        ("Winter Valley Estates Lake", ["Winter Valley Estates"], "facility_name"),
        # Old mill ponds: "factory" counts only when a factory is mapped near.
        ("Tack Factory Pond", [], "ok"),
        ("Burnt Factory Pond", [], "ok"),
    ],
)
def test_a_facility_word_after_a_proper_name_names_one_facility(name, places, reason):
    assert judge(name, {}, facilities_near=[], places_near=places).reason == reason


def test_facility_words_and_tags_map_to_the_same_kinds():
    assert named_facilities("Athens Country Club Lake") == {"club"}
    assert named_facilities("Georgia State Hospital Lake West") == {"health"}
    assert named_facilities("Mud Lake") == set()
    assert facility_kinds({"amenity": "school"}) == {"education"}
    assert facility_kinds({"leisure": "golf_course"}) == {"club"}
    assert facility_kinds({"office": "company"}) == {"commerce"}
    assert facility_kinds({"amenity": "parking"}) == set()
    assert set(FACILITY_NAMES) == set(FACILITY_TAGS)


def test_the_facility_index_finds_a_facility_within_the_margin_only():
    index = gf.FacilityIndex()
    index.add({"education"}, (33.0, -97.0, 33.001, -96.999))  # a school
    index.add({"housing"}, (30.0, -100.0, 36.0, -94.0))  # a box over many cells
    pond = (33.0025, -97.0, 33.003, -96.999)  # ~170 m north of the school
    assert index.near(pond, {"education"}, 300) == {"education"}
    assert index.near(pond, {"education"}, 100) == set()
    assert index.near(pond, {"cemetery"}, 300) == set()
    assert index.near(pond, {"housing", "education"}, 300) == {"housing", "education"}


FACILITY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="33.000" lon="-97.000"/><node id="2" lat="33.000" lon="-96.998"/>
  <node id="3" lat="33.002" lon="-96.998"/>
  <node id="4" lat="33.0025" lon="-97.000"/><node id="5" lat="33.0025" lon="-96.998"/>
  <node id="6" lat="33.0045" lon="-96.998"/>
  <node id="7" lat="33.100" lon="-97.000"/><node id="8" lat="33.100" lon="-96.998"/>
  <node id="9" lat="33.102" lon="-96.998"/>
  <node id="10" lat="33.2000" lon="-97.000"><tag k="amenity" v="grave_yard"/></node>
  <way id="100"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/>
    <tag k="natural" v="water"/><tag k="name" v="Salisbury School Pond"/></way>
  <way id="101"><nd ref="4"/><nd ref="5"/><nd ref="6"/><nd ref="4"/>
    <tag k="amenity" v="school"/><tag k="name" v="Salisbury School"/></way>
  <way id="102"><nd ref="7"/><nd ref="8"/><nd ref="9"/><nd ref="7"/>
    <tag k="natural" v="water"/><tag k="name" v="School Lake"/></way>
  <node id="11" lat="33.300" lon="-97.000"/><node id="12" lat="33.300" lon="-96.998"/>
  <node id="13" lat="33.302" lon="-96.998"/>
  <node id="14" lat="33.330" lon="-97.000"><tag k="place" v="hamlet"/><tag k="name" v="Ball Club"/></node>
  <way id="103"><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="11"/>
    <tag k="natural" v="water"/><tag k="name" v="Ball Club Lake"/></way>
</osm>
"""


def test_the_extract_records_which_named_facilities_are_mapped_near(tmp_path):
    pytest.importorskip("osmium")
    path = tmp_path / "tiny.osm"
    path.write_text(FACILITY_XML, encoding="utf-8")
    payload = gf.extract(path, "TX")
    by_ref = {f"{e['type']}/{e['id']}": e for e in payload["elements"]}
    assert by_ref["way/100"]["facilities_near"] == ["education"]  # the school is 50 m away
    assert by_ref["way/102"]["facilities_near"] == []  # 11 km from it
    assert by_ref["way/103"]["places_near"] == ["Ball Club"]  # the hamlet, 3 km off
    lakes, _, skipped = osm.parse_elements(payload)
    assert sorted(lake.name for lake in lakes) == ["Ball Club Lake", "School Lake"]
    assert skipped == {"untyped_facility": 1}


def _water(el_id, name, lat=33.0, lng=-97.0, half_deg=0.01, **tags):
    return {
        "type": "way", "id": el_id, "tags": {"natural": "water", "name": name, **tags},
        "bounds": {"minlat": lat - half_deg, "minlon": lng - half_deg,
                   "maxlat": lat + half_deg, "maxlon": lng + half_deg},
    }


def test_the_importer_judges_untyped_water_and_keeps_typed_water_as_before():
    payload = {"elements": [
        _water(1, "Mud Lake"),
        _water(2, "Whortleberry Pond", lat=34.0, half_deg=0.001),
        _water(3, "Pine River", lat=35.0),
        _water(4, "Retention Pond", lat=36.0),
        _water(5, "Tiny Lake", lat=37.0, half_deg=0.0003),  # under 200 m across
        _water(6, "Pine River", lat=38.0, water="lake"),  # tagged: the name is not judged
    ]}
    untyped_refs: set[str] = set()
    lakes, _, skipped = osm.parse_elements(payload, untyped_refs=untyped_refs)
    by_name = {lake.name: lake for lake in lakes}
    assert set(by_name) == {"Mud Lake", "Whortleberry Pond", "Pine River"}
    assert by_name["Mud Lake"].untyped and by_name["Mud Lake"].water_type == "lake"
    assert by_name["Whortleberry Pond"].water_type == "pond"
    assert not by_name["Pine River"].untyped
    assert skipped == {"untyped_not_lake": 1, "untyped_not_fishing": 1, "untyped_too_small": 1}
    assert untyped_refs == {"way/3", "way/4", "way/5"}


def test_a_lake_with_one_tagged_piece_is_not_counted_as_untyped():
    pieces = [_water(1, "Mud Lake", water="lake"), _water(2, "Mud Lake", half_deg=0.02)]
    (lake,) = osm.merge_pieces(osm.parse_elements({"elements": pieces})[0])
    assert not lake.untyped


def test_a_re_import_removes_untyped_water_the_rules_now_leave_out(db_session):
    osm.run("MN", {"elements": [_water(1, "Mud Lake"), _water(2, "Clear Lake", lat=34.0)]}, db_session)
    db_session.flush()
    assert set(db_session.scalars(select(Waterbody.name))) == {"Mud Lake", "Clear Lake"}
    # A CDFW id (an official source naming the lake) keeps a row.
    clear = db_session.scalar(select(Waterbody).where(Waterbody.name == "Clear Lake"))
    clear.dfg_water_id = 123
    db_session.flush()

    # Both now carry a tag that leaves them out.
    summary = osm.run("MN", {"elements": [
        _water(1, "Mud Lake", intermittent="yes"), _water(2, "Clear Lake", lat=34.0, intermittent="yes"),
    ]}, db_session)
    db_session.flush()
    assert summary.lakes_removed_untyped == 1
    assert set(db_session.scalars(select(Waterbody.name))) == {"Clear Lake"}
