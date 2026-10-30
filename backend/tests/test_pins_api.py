"""Community pins: creation, photos, visibility, editing, reporting."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import ExifTags, Image
from sqlalchemy import select

from app.core.config import get_settings
from app.models.community import AuditLog, CatchPin, PinPhoto
from tests.conftest import make_admin, signup


def jpeg(width=3000, height=2000, gps=True, orientation=None, color="green") -> bytes:
    img = Image.new("RGB", (width, height), color)
    exif = Image.Exif()
    if gps:
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        gps_ifd[ExifTags.GPS.GPSLatitudeRef] = "N"
        gps_ifd[ExifTags.GPS.GPSLatitude] = (32.0, 48.0, 23.0)
        gps_ifd[ExifTags.GPS.GPSLongitudeRef] = "W"
        gps_ifd[ExifTags.GPS.GPSLongitude] = (95.0, 35.0, 11.0)
    exif[ExifTags.Base.Make] = "PhoneCo"
    if orientation:
        exif[ExifTags.Base.Orientation] = orientation
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif)
    return out.getvalue()


def png_with_alpha() -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", (400, 300), (0, 0, 255, 128)).save(out, format="PNG")
    return out.getvalue()


def create(c, photos=(), **fields):
    data = {"latitude": 32.8065, "longitude": -95.5931, "title": "Dam bank", **fields}
    files = [("photos", (f"p{i}.jpg", b, "image/jpeg")) for i, b in enumerate(photos)]
    return c.post("/api/pins", data=data, files=files or None)


def media_files() -> list[Path]:
    root = Path(get_settings().media_root)
    return sorted(root.rglob("*.jpg")) if root.exists() else []


# ------------------------------------------------------------------ create


def test_creating_a_pin_needs_an_account(make_client):
    assert create(make_client()).status_code == 401


def test_a_pin_is_published_immediately_and_linked_to_a_nearby_lake(make_client, seeded_lake):
    c = make_client()
    signup(c)
    resp = create(c, species_slug="largemouth-bass", caught_on="2026-09-20", note="  Worked a jig by the riprap. ")
    assert resp.status_code == 201, resp.text
    pin = resp.json()
    assert pin["status"] == "published" and pin["visibility"] == "public"
    assert pin["species_label"] == "Largemouth Bass"
    assert pin["note"] == "Worked a jig by the riprap."
    assert pin["lake"] == {"id": seeded_lake["waterbody"].id, "name": "Lake Fork"}
    assert pin["is_mine"] and pin["can_edit"] and not pin["can_report"]
    assert pin["author"]["display_name"] == "Angler"


def test_far_from_any_lake_there_is_no_link(make_client, seeded_lake):
    c = make_client()
    signup(c)
    assert create(c, latitude=31.0, longitude=-97.0).json()["lake"] is None


@pytest.mark.parametrize(
    "fields",
    [
        {"title": "no"},
        {"latitude": 95},
        {"longitude": -200},
        {"species_slug": "kraken"},
        {"visibility": "friends"},
        {"caught_on": "2999-01-01"},
        {"caught_on": "1900-01-01"},
    ],
)
def test_pin_validation(make_client, fields):
    c = make_client()
    signup(c)
    assert create(c, **fields).status_code == 422


def test_free_text_species_when_its_not_in_the_guide(make_client):
    c = make_client()
    signup(c)
    pin = create(c, species_other="Walleye").json()
    assert pin["species_slug"] is None and pin["species_label"] == "Walleye"
    # A guide species typed in is that species (and is photo-checked as one).
    pin = create(c, species_other="freshwater drum").json()
    assert pin["species_slug"] == "freshwater-drum" and pin["species_label"] == "Freshwater Drum"


# ------------------------------------------------------------------ photos


def test_photos_are_re_encoded_resized_and_stripped_of_gps(make_client):
    original = jpeg()
    assert Image.open(io.BytesIO(original)).getexif().get_ifd(ExifTags.IFD.GPSInfo)  # the input really has GPS
    c = make_client()
    signup(c)
    pin = create(c, photos=[original]).json()
    assert pin["photo_count"] == 1
    photo = pin["photos"][0]
    assert (photo["width"], photo["height"]) == (2048, 1365)

    full = c.get(_path(photo["url"]))
    assert full.status_code == 200 and full.headers["content-type"] == "image/jpeg"
    assert full.headers["x-content-type-options"] == "nosniff"
    stored = Image.open(io.BytesIO(full.content))
    assert stored.getexif().get_ifd(ExifTags.IFD.GPSInfo) == {}
    assert len(stored.getexif()) == 0  # no camera make either
    thumb = Image.open(io.BytesIO(c.get(_path(photo["thumb_url"])).content))
    assert max(thumb.size) == 640
    assert len(media_files()) == 2


def _path(url: str) -> str:
    return url[url.index("/api/"):]


def test_exif_orientation_is_applied_before_it_is_dropped(make_client):
    c = make_client()
    signup(c)
    pin = create(c, photos=[jpeg(width=300, height=200, orientation=6)]).json()
    assert (pin["photos"][0]["width"], pin["photos"][0]["height"]) == (200, 300)


def test_transparent_pngs_are_accepted_and_flattened(make_client):
    c = make_client()
    signup(c)
    resp = c.post(
        "/api/pins",
        data={"latitude": 32.8, "longitude": -95.6, "title": "Pond"},
        files=[("photos", ("p.png", png_with_alpha(), "image/png"))],
    )
    assert resp.status_code == 201


def test_a_file_that_isnt_a_photo_is_rejected_and_nothing_is_written(make_client, db_session):
    c = make_client()
    signup(c)
    fake = b"<?php echo 'hi'; ?>" + b"\x00" * 100
    resp = c.post(
        "/api/pins",
        data={"latitude": 32.8, "longitude": -95.6, "title": "Pond"},
        files=[("photos", ("ok.jpg", jpeg(400, 300), "image/jpeg")), ("photos", ("x.jpg", fake, "image/jpeg"))],
    )
    assert resp.status_code == 422
    assert "Photo 2" in resp.json()["detail"]
    assert db_session.scalar(select(CatchPin)) is None
    assert media_files() == []


def test_photo_count_and_size_limits(make_client, monkeypatch):
    c = make_client()
    signup(c)
    small = jpeg(200, 150, gps=False)
    assert create(c, photos=[small] * 5).status_code == 422
    monkeypatch.setattr(get_settings(), "max_photo_bytes", 1000)
    assert create(c, photos=[jpeg(800, 600)]).status_code == 413


def test_a_new_account_shares_a_few_catches_a_day(make_client, db_session, monkeypatch):
    from datetime import timedelta

    from app.db.types import utcnow
    from app.models.community import User

    monkeypatch.setattr(get_settings(), "new_account_pins_per_day", 2)
    c = make_client()
    signup(c)
    assert create(c, title="One").status_code == 201
    assert create(c, title="Two").status_code == 201
    third = create(c, title="Three")
    assert third.status_code == 429
    assert "New accounts can share 2 catches a day" in third.json()["detail"]

    # After its first days the account posts like anyone else.
    user = db_session.scalar(select(User).where(User.email == "angler@example.com"))
    user.created_at = utcnow() - timedelta(days=get_settings().new_account_days, minutes=1)
    db_session.commit()
    assert create(c, title="Three").status_code == 201

    # Admins are never held back.
    admin = make_client()
    signup(admin, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    assert all(create(admin, title=f"Pin {i}").status_code == 201 for i in range(3))


def test_adding_and_deleting_photos_later(make_client):
    c = make_client()
    signup(c)
    pin = create(c).json()
    after = c.post(f"/api/pins/{pin['id']}/photos", files=[("photos", ("a.jpg", jpeg(400, 300), "image/jpeg"))]).json()
    assert after["photo_count"] == 1 and len(media_files()) == 2
    gone = c.delete(f"/api/pins/{pin['id']}/photos/{after['photos'][0]['id']}").json()
    assert gone["photo_count"] == 0 and media_files() == []


# -------------------------------------------------------------- visibility


def test_private_pins_are_invisible_to_everyone_but_the_owner_and_admins(make_client, db_session):
    owner = make_client()
    signup(owner)
    pin = create(owner, visibility="private", photos=[jpeg(400, 300)]).json()
    photo_path = _path(pin["photos"][0]["url"])

    stranger = make_client()
    signup(stranger, email="s@example.com", name="Stranger")
    anon = make_client()
    for c in (stranger, anon):
        assert c.get(f"/api/pins/{pin['id']}").status_code == 404  # not 403: existence is private too
        assert c.get(photo_path).status_code == 404
        assert all(p["id"] != pin["id"] for p in c.get("/api/pins").json())

    assert owner.get(f"/api/pins/{pin['id']}").status_code == 200
    assert owner.get(photo_path).headers["cache-control"].startswith("private")
    assert any(p["id"] == pin["id"] for p in owner.get("/api/pins").json())

    admin = make_client()
    signup(admin, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    assert admin.get(f"/api/pins/{pin['id']}").status_code == 200


def test_public_list_filters(make_client):
    c = make_client()
    signup(c)
    create(c, title="Fork bass", species_slug="largemouth-bass")
    create(c, title="Austin cat", latitude=30.27, longitude=-97.74, species_slug="channel-catfish")
    anon = make_client()
    assert {p["title"] for p in anon.get("/api/pins").json()} == {"Fork bass", "Austin cat"}
    near_austin = anon.get("/api/pins", params={"bbox": "-98,30,-97,31"}).json()
    assert [p["title"] for p in near_austin] == ["Austin cat"]
    assert [p["title"] for p in anon.get("/api/pins", params={"species": "largemouth-bass"}).json()] == ["Fork bass"]
    assert anon.get("/api/pins", params={"mine": True}).json() == []
    assert anon.get("/api/pins", params={"bbox": "nonsense"}).status_code == 422


def test_catches_are_browsed_by_state_then_county_then_lake(make_client, seeded_lake):
    c = make_client()
    signup(c)
    fork = create(c, title="Fork bass").json()  # at Lake Fork, Wood County
    create(c, title="Fork bank", latitude=32.66, longitude=-95.49)  # same county, no lake
    create(c, title="Houston cat", latitude=29.76, longitude=-95.37)
    create(c, title="Atlanta bream", latitude=33.75, longitude=-84.39)
    create(c, title="Secret spot", latitude=29.75, longitude=-95.36, visibility="private")
    assert (fork["state_code"], fork["county_geoid"], fork["county_name"]) == ("TX", "48499", "Wood County")

    anon = make_client()
    states = anon.get("/api/pins/places").json()
    assert states["level"] == "state"
    # A private pin is never counted for anyone else.
    assert [(p["id"], p["name"], p["count"]) for p in states["places"]] == [("TX", "Texas", 3), ("GA", "Georgia", 1)]
    tx = anon.get("/api/pins/places", params={"state": "tx"}).json()
    assert (tx["level"], tx["state_name"]) == ("county", "Texas")
    assert [(p["name"], p["count"]) for p in tx["places"]] == [("Wood County", 2), ("Harris County", 1)]
    lakes = anon.get("/api/pins/places", params={"county": "48499"}).json()
    assert (lakes["level"], lakes["state_name"], lakes["county_name"]) == ("lake", "Texas", "Wood County")
    assert [(p["id"], p["name"], p["count"]) for p in lakes["places"]] == [
        (str(seeded_lake["waterbody"].id), "Lake Fork", 1),
        ("0", "Not on mapped water", 1),
    ]
    # The owner's own private pin counts for them.
    assert [p["count"] for p in c.get("/api/pins/places", params={"state": "TX"}).json()["places"]] == [2, 2]

    def titles(**params):
        return sorted(p["title"] for p in anon.get("/api/pins", params=params).json())

    assert titles(state="TX") == ["Fork bank", "Fork bass", "Houston cat"]
    assert titles(county="48499") == ["Fork bank", "Fork bass"]
    assert titles(county="48499", lake=seeded_lake["waterbody"].id) == ["Fork bass"]
    assert titles(county="48499", lake=0) == ["Fork bank"]
    assert anon.get("/api/pins", params={"county": "Wood"}).status_code == 422


def test_where_names_the_county_a_point_is_in(make_client):
    anon = make_client()
    assert anon.get("/api/pins/where", params={"lat": 29.76, "lng": -95.37}).json() == {
        "state_code": "TX", "state_name": "Texas", "county_geoid": "48201", "county_name": "Harris County",
        "water": None, "water_required": False,
    }
    assert anon.get("/api/pins/where", params={"lat": 0, "lng": 0}).json()["county_geoid"] is None


def test_pins_saved_before_counties_get_one_at_startup(make_client, db_session):
    from app.services.pins import fill_places

    c = make_client()
    signup(c)
    pin_id = create(c).json()["id"]
    pin = db_session.get(CatchPin, pin_id)
    pin.state_code = pin.county_geoid = pin.county_name = None
    db_session.commit()
    assert fill_places(db_session) == 1
    db_session.refresh(pin)
    assert (pin.state_code, pin.county_name) == ("TX", "Wood County")


# ---------------------------------------------------- where others see it


def test_others_see_the_lake_not_the_spot_unless_the_angler_shares_it(make_client, db_session, seeded_lake):
    owner = make_client()
    signup(owner)
    lake = seeded_lake["waterbody"]
    pin = create(owner, latitude=32.8101, longitude=-95.5899).json()  # on Lake Fork, off its centre
    assert (pin["latitude"], pin["longitude"], pin["location_shown"]) == (32.8101, -95.5899, "exact")
    assert (pin["share_exact"], pin["public_place"]) == (False, "lake")

    anon = make_client()
    seen = anon.get(f"/api/pins/{pin['id']}").json()
    assert (seen["latitude"], seen["longitude"], seen["location_shown"]) == (lake.latitude, lake.longitude, "lake")
    assert [(p["latitude"], p["longitude"]) for p in anon.get("/api/pins").json()] == [(lake.latitude, lake.longitude)]
    # A box around the spot that leaves out the lake's centre finds nothing,
    # so the spot can't be narrowed down box by box...
    tight = "-95.5900,32.8100,-95.5898,32.8102"
    assert anon.get("/api/pins", params={"bbox": tight}).json() == []
    stranger = make_client()
    signup(stranger, email="s@example.com", name="Stranger")
    assert stranger.get("/api/pins", params={"bbox": tight}).json() == []
    # ...while the owner finds their own catch there, at the spot.
    mine = owner.get("/api/pins", params={"bbox": tight}).json()
    assert [(p["id"], p["location_shown"]) for p in mine] == [(pin["id"], "exact")]

    admin = make_client()
    signup(admin, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    assert admin.get(f"/api/pins/{pin['id']}").json()["location_shown"] == "exact"

    # Sharing the spot shows it to everyone; un-sharing hides it again.
    shared = owner.patch(f"/api/pins/{pin['id']}", json={"share_exact": True}).json()
    assert (shared["share_exact"], shared["public_place"]) == (True, "exact")
    seen = anon.get(f"/api/pins/{pin['id']}").json()
    assert (seen["latitude"], seen["longitude"], seen["location_shown"]) == (32.8101, -95.5899, "exact")
    assert [p["id"] for p in anon.get("/api/pins", params={"bbox": tight}).json()] == [pin["id"]]
    owner.patch(f"/api/pins/{pin['id']}", json={"share_exact": False})
    assert anon.get(f"/api/pins/{pin['id']}").json()["location_shown"] == "lake"
    assert anon.get("/api/pins", params={"bbox": tight}).json() == []


def test_a_catch_can_be_shared_at_its_spot_from_the_start(make_client, seeded_lake):
    c = make_client()
    signup(c)
    pin = create(c, latitude=32.8101, longitude=-95.5899, share_exact="true").json()
    assert (pin["share_exact"], pin["public_place"]) == (True, "exact")
    seen = make_client().get(f"/api/pins/{pin['id']}").json()
    assert (seen["latitude"], seen["longitude"], seen["location_shown"]) == (32.8101, -95.5899, "exact")


def test_away_from_lakes_others_see_the_county_or_a_rounded_area(make_client):
    from app.services import counties

    c = make_client()
    signup(c)
    houston = create(c, latitude=29.7604, longitude=-95.3698).json()  # Harris County, no lake
    assert houston["public_place"] == "county"
    seen = make_client().get(f"/api/pins/{houston['id']}").json()
    assert seen["location_shown"] == "county"
    assert (seen["latitude"], seen["longitude"]) != (29.7604, -95.3698)
    assert counties.county_at(seen["latitude"], seen["longitude"]).geoid == "48201"  # the county's middle

    # Outside every county: the spot to one decimal (~11 km).
    far = create(c, latitude=10.1234, longitude=20.5678).json()
    assert far["public_place"] == "area"
    seen = make_client().get(f"/api/pins/{far['id']}").json()
    assert (seen["latitude"], seen["longitude"], seen["location_shown"]) == (10.1, 20.6, "area")


def test_pins_saved_before_get_their_public_point_at_startup(make_client, db_session, seeded_lake):
    from app.services.pins import fill_public_points

    c = make_client()
    signup(c)
    pin_id = create(c, latitude=32.8101, longitude=-95.5899).json()["id"]
    pin = db_session.get(CatchPin, pin_id)
    pin.public_latitude = pin.public_longitude = pin.public_place = None
    db_session.commit()
    # Until then others see the rounded spot, never the exact one.
    seen = make_client().get(f"/api/pins/{pin_id}").json()
    assert (seen["latitude"], seen["longitude"], seen["location_shown"]) == (32.8, -95.6, "area")
    assert fill_public_points(db_session) == 1
    db_session.refresh(pin)
    assert (pin.public_latitude, pin.public_longitude, pin.public_place) == (
        seeded_lake["waterbody"].latitude, seeded_lake["waterbody"].longitude, "lake",
    )


# ----------------------------------------------------------------- editing


def test_only_the_owner_can_edit_or_delete(make_client):
    owner = make_client()
    signup(owner)
    pin = create(owner, note="first", species_slug="bluegill", photos=[jpeg(400, 300)]).json()
    other = make_client()
    signup(other, email="o@example.com", name="Other")
    assert other.patch(f"/api/pins/{pin['id']}", json={"title": "Mine now"}).status_code == 403
    assert other.delete(f"/api/pins/{pin['id']}").status_code == 404

    edited = owner.patch(
        f"/api/pins/{pin['id']}", json={"title": "Better title", "visibility": "private", "clear_note": True, "clear_species": True}
    ).json()
    assert edited["title"] == "Better title" and edited["visibility"] == "private"
    assert edited["note"] is None and edited["species_slug"] is None

    assert owner.delete(f"/api/pins/{pin['id']}").status_code == 204
    assert owner.get(f"/api/pins/{pin['id']}").status_code == 404
    assert media_files() == []


# --------------------------------------------------------------- reporting


def _reporters(make_client, n):
    out = []
    for i in range(n):
        c = make_client()
        signup(c, email=f"r{i}@example.com", name=f"Reporter {i}")
        out.append(c)
    return out


def test_reporting_rules(make_client):
    owner = make_client()
    signup(owner)
    pin = create(owner).json()
    assert owner.post(f"/api/pins/{pin['id']}/reports", json={"reason": "spam"}).status_code == 422
    (r,) = _reporters(make_client, 1)
    assert r.post(f"/api/pins/{pin['id']}/reports", json={"reason": "bogus"}).status_code == 422
    first = r.post(f"/api/pins/{pin['id']}/reports", json={"reason": "spam", "detail": "ad for a shop"})
    assert first.status_code == 201 and first.json() == {"received": True, "pin_hidden": False}
    assert r.post(f"/api/pins/{pin['id']}/reports", json={"reason": "spam"}).status_code == 409
    detail = r.get(f"/api/pins/{pin['id']}").json()
    assert detail["reported_by_me"] and not detail["can_report"]
    assert make_client().post(f"/api/pins/{pin['id']}/reports", json={"reason": "spam"}).status_code == 401


def test_enough_distinct_reports_hide_a_pin_until_review(make_client, db_session):
    owner = make_client()
    signup(owner)
    pin = create(owner).json()
    reporters = _reporters(make_client, 3)
    results = [r.post(f"/api/pins/{pin['id']}/reports", json={"reason": "inappropriate"}).json() for r in reporters]
    assert [x["pin_hidden"] for x in results] == [False, False, True]

    assert make_client().get(f"/api/pins/{pin['id']}").status_code == 404
    own_view = owner.get(f"/api/pins/{pin['id']}").json()
    assert own_view["status"] == "hidden" and own_view["status_reason"] == "reports"
    log = db_session.scalar(select(AuditLog).where(AuditLog.action == "pin.auto_hidden"))
    assert log is not None and log.actor_id is None and log.target_id == pin["id"]


def test_options_endpoint_lists_species_and_reasons(make_client):
    body = make_client().get("/api/pins/options").json()
    assert {"slug": "bluegill", "label": "Bluegill"} in body["species"]
    assert any(r["id"] == "private_property" for r in body["report_reasons"])
    assert body["max_photos"] == 4


def test_photo_rows_follow_their_pin(make_client, db_session):
    c = make_client()
    signup(c)
    pin = create(c, photos=[jpeg(400, 300), jpeg(400, 300, color="blue")]).json()
    assert [p["id"] for p in pin["photos"]] == sorted(p["id"] for p in pin["photos"])
    c.delete(f"/api/pins/{pin['id']}")
    assert db_session.scalar(select(PinPhoto)) is None


def test_switching_between_a_guide_species_and_free_text(make_client):
    c = make_client()
    signup(c)
    pin = create(c, species_slug="bluegill").json()
    other = c.patch(f"/api/pins/{pin['id']}", json={"species_other": "Walleye"}).json()
    assert other["species_slug"] is None and other["species_label"] == "Walleye"
    back = c.patch(f"/api/pins/{pin['id']}", json={"species_slug": "white-crappie"}).json()
    assert back["species_slug"] == "white-crappie" and back["species_label"] == "White Crappie"
