"""Bait and tackle shops: which OpenStreetMap shops count, the import, the API."""
from app.data_import.tackle_shops import run, shop_fields
from app.models.shop import TackleShop
from app.models.waterbody import SourceRecord


def test_fishing_and_bait_shops_count():
    assert shop_fields({"shop": "fishing", "name": "Rip Tide Bait and Tackle"})["kind"] == "bait"
    assert shop_fields({"shop": "fishing", "name": "Toccoa River Outfitters"})["kind"] == "tackle"
    assert shop_fields({"shop": "bait", "name": "Minnow Hut"})["kind"] == "bait"


def test_a_shop_named_for_bait_or_tackle_counts_whatever_it_is_mapped_as():
    assert shop_fields({"shop": "convenience", "name": "Lake Sinclair Bait And Tackle"})["kind"] == "bait"
    assert shop_fields({"shop": "pawnbroker", "name": "Shepard's Tackle & Pawn"})["kind"] == "tackle"


def test_gear_shops_count_only_when_tagged_or_named_for_fishing():
    assert shop_fields({"shop": "outdoor", "name": "Rock Creek", "fishing": "yes"}) is not None
    assert shop_fields({"shop": "sports", "name": "Big Lake Sports", "sport": "hunting;fishing"}) is not None
    assert shop_fields({"shop": "outdoor", "name": "Delta Fishing Supply"}) is not None
    assert shop_fields({"shop": "outdoor", "name": "Half Moon Outfitters"}) is None
    assert shop_fields({"shop": "sports", "name": "Dick's Sporting Goods", "brand": "Dick's Sporting Goods"}) is None


def test_fishing_retailers_count_by_brand():
    fields = shop_fields({"shop": "outdoor", "name": "Bass Pro Shops", "brand": "Bass Pro Shops"})
    assert fields["kind"] == "store"
    assert shop_fields({"shop": "sports", "name": "Academy", "brand": "Academy Sports + Outdoors"})["kind"] == "store"


def test_never_clothing_or_unnamed_shops():
    assert shop_fields({"shop": "clothes", "name": "Urban Outfitters"}) is None
    assert shop_fields({"shop": "fishing"}) is None
    assert shop_fields({"name": "Bait Shack"}) is None  # not a shop at all


def test_keeps_contact_details_tidy():
    fields = shop_fields(
        {
            "shop": "fishing",
            "name": "Bait Bucket",
            "addr:housenumber": "1198",
            "addr:street": "Hwy 36 E",
            "addr:city": "Jackson",
            "addr:state": "GA",
            "contact:website": "baitbucket.example;https://other.example",
            "opening_hours": "Mo-Su 05:00-19:00",
        }
    )
    assert fields["address"] == "1198 Hwy 36 E, Jackson, GA"
    assert fields["website"] == "https://baitbucket.example"
    assert fields["opening_hours"] == "Mo-Su 05:00-19:00"


def _payload(shops, states=("GA",)):
    return {"extracted_at": "2026-10-27T12:00:00+00:00", "states": list(states), "shops": shops}


def _shop(ref, name="Bait Shack", lat=33.9, lng=-84.2, state="GA"):
    return {"osm_ref": ref, "name": name, "kind": "bait", "lat": lat, "lng": lng, "state": state,
            "address": None, "phone": None, "website": None, "opening_hours": None}


def test_import_is_idempotent_and_drops_shops_no_longer_mapped(db_session):
    assert run(db_session, _payload([_shop("n1"), _shop("w2", "Tackle Box")])) == {"added": 2, "updated": 0, "removed": 0}
    assert run(db_session, _payload([_shop("n1", "Bait Shack II")])) == {"added": 0, "updated": 1, "removed": 1}
    rows = db_session.query(TackleShop).all()
    assert [(r.osm_ref, r.name) for r in rows] == [("n1", "Bait Shack II")]
    record = db_session.get(SourceRecord, rows[0].source_record_id)
    assert record.licence_name == "ODbL 1.0" and record.licence_class == "OPEN"


def test_import_of_one_state_leaves_other_states_alone(db_session):
    run(db_session, _payload([_shop("n1")]))
    run(db_session, _payload([_shop("n9", state="TX", lat=30.2, lng=-97.7)], states=("TX",)))
    assert {r.osm_ref for r in db_session.query(TackleShop)} == {"n1", "n9"}


def test_api_lists_shops_in_the_view_with_a_link_to_osm(client, db_session):
    run(db_session, _payload([_shop("n1"), _shop("w2", "Far Away", lat=40.0, lng=-100.0)]))
    resp = client.get("/api/shops", params={"bbox": "-85,33,-84,34"})
    assert resp.status_code == 200
    body = resp.json()
    assert [s["name"] for s in body] == ["Bait Shack"]
    assert body[0]["osm_url"] == "https://www.openstreetmap.org/node/1"
    assert client.get("/api/shops", params={"bbox": "nonsense"}).status_code == 422


def test_api_names_the_nearest_shops_to_a_lake(client, db_session):
    run(db_session, _payload([
        _shop("n1", "Far Bait", lat=34.20, lng=-84.20),
        _shop("n2", "Near Bait", lat=34.01, lng=-84.00),
        _shop("n3", "Middle Tackle", lat=34.10, lng=-84.10),
        _shop("n4", "Out Of Range", lat=35.5, lng=-84.0),
    ]))
    body = client.get("/api/shops/near", params={"lat": 34.0, "lng": -84.0, "limit": 2}).json()
    assert [s["name"] for s in body] == ["Near Bait", "Middle Tackle"]
    assert 1.0 < body[0]["distance_km"] < 1.6
    assert len(client.get("/api/shops/near", params={"lat": 34.0, "lng": -84.0, "limit": 10}).json()) == 3


def test_api_keeps_to_the_state_on_screen(client, db_session):
    run(db_session, _payload([_shop("n1")]))
    run(db_session, _payload([_shop("n2", "Across The Line", state="AL", lat=33.9, lng=-84.3)], states=("AL",)))
    names = lambda **p: [s["name"] for s in client.get("/api/shops", params={"bbox": "-85,33,-84,34", **p}).json()]  # noqa: E731
    assert names() == ["Bait Shack", "Across The Line"]
    assert names(state_code="ga") == ["Bait Shack"]
