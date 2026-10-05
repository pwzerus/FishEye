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
    pin = create(c, species_other="Freshwater drum").json()
    assert pin["species_slug"] is None and pin["species_label"] == "Freshwater drum"


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
    other = c.patch(f"/api/pins/{pin['id']}", json={"species_other": "Freshwater drum"}).json()
    assert other["species_slug"] is None and other["species_label"] == "Freshwater drum"
    back = c.patch(f"/api/pins/{pin['id']}", json={"species_slug": "white-crappie"}).json()
    assert back["species_slug"] == "white-crappie" and back["species_label"] == "White Crappie"
