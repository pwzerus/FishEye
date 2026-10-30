"""Lake reports (services/lake_reports.py, ADR 0039): "something's wrong
with this lake" and "a lake is missing", from anyone, to an admin queue."""
from __future__ import annotations

from sqlalchemy import select

from app.models.community import AuditLog, LakeReport
from tests.conftest import make_admin, signup


def admin_client(make_client, db_session):
    c = make_client()
    signup(c, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    return c


def test_anyone_can_report_a_problem_with_a_lake(make_client, seeded_lake, db_session):
    lake = seeded_lake["waterbody"]
    anon = make_client()
    reasons = anon.get("/api/lake-reports/options").json()["reasons"]
    assert {r["id"] for r in reasons} >= {"wrong_location", "not_public", "wrong_fish", "gone", "other"}

    resp = anon.post("/api/lake-reports", json={"reason": "not_public", "waterbody_id": lake.id, "detail": " Gate locked,  posted sign. "})
    assert resp.status_code == 201, resp.text
    row = db_session.get(LakeReport, resp.json()["id"])
    assert (row.reason, row.waterbody_id, row.state_code, row.detail, row.reporter_id) == (
        "not_public", lake.id, "TX", "Gate locked, posted sign.", None,
    )

    signed_in = make_client()
    me = signup(signed_in)
    resp = signed_in.post("/api/lake-reports", json={"reason": "wrong_fish", "waterbody_id": lake.id})
    assert db_session.get(LakeReport, resp.json()["id"]).reporter_id == me["id"]


def test_a_missing_lake_needs_a_name_and_a_place(make_client, db_session):
    anon = make_client()
    assert anon.post("/api/lake-reports", json={"reason": "missing", "latitude": 29.76, "longitude": -95.37}).status_code == 422
    assert anon.post("/api/lake-reports", json={"reason": "missing", "name": "Mystery Pond"}).status_code == 422
    resp = anon.post(
        "/api/lake-reports",
        json={"reason": "missing", "name": "Mystery Pond", "latitude": 29.760001, "longitude": -95.370001, "detail": "City park pond"},
    )
    assert resp.status_code == 201
    row = db_session.get(LakeReport, resp.json()["id"])
    assert (row.name, row.latitude, row.longitude, row.state_code) == ("Mystery Pond", 29.76, -95.37, "TX")


def test_bad_reports_are_refused(make_client, seeded_lake):
    anon = make_client()
    lake_id = seeded_lake["waterbody"].id
    assert anon.post("/api/lake-reports", json={"reason": "kraken", "waterbody_id": lake_id}).status_code == 422
    assert anon.post("/api/lake-reports", json={"reason": "gone", "waterbody_id": 999999}).status_code == 404
    assert anon.post("/api/lake-reports", json={"reason": "other", "waterbody_id": lake_id}).status_code == 422  # say what


def test_reports_from_one_address_are_limited(make_client, seeded_lake):
    anon = make_client()
    lake_id = seeded_lake["waterbody"].id
    codes = [anon.post("/api/lake-reports", json={"reason": "gone", "waterbody_id": lake_id}).status_code for _ in range(11)]
    assert codes[:10] == [201] * 10 and codes[10] == 429


def test_admins_work_the_queue_and_it_is_audited(make_client, seeded_lake, db_session):
    lake = seeded_lake["waterbody"]
    anon = make_client()
    first = anon.post("/api/lake-reports", json={"reason": "wrong_location", "waterbody_id": lake.id}).json()["id"]
    anon.post("/api/lake-reports", json={"reason": "missing", "name": "New Pond", "latitude": 30.27, "longitude": -97.74})

    user = make_client()
    signup(user)
    assert user.get("/api/admin/lake-reports").status_code == 403

    admin = admin_client(make_client, db_session)
    assert admin.get("/api/admin/stats").json()["lake_reports_open"] == 2
    queue = admin.get("/api/admin/lake-reports").json()
    assert [(r["reason"], r["lake_name"], r["state_code"]) for r in queue] == [
        ("wrong_location", "Lake Fork", "TX"),
        ("missing", "New Pond", "TX"),
    ]
    assert queue[0]["reason_label"] == "It's in the wrong place" and queue[0]["reporter"] is None

    assert admin.post(f"/api/admin/lake-reports/{first}/resolve", json={"resolution": "fixed", "note": "Moved the pin"}).status_code == 204
    assert admin.post(f"/api/admin/lake-reports/{first}/resolve", json={"resolution": "fixed"}).status_code == 409
    assert admin.post(f"/api/admin/lake-reports/{first}/resolve", json={"resolution": "maybe"}).status_code in (409, 422)
    assert [r["id"] for r in admin.get("/api/admin/lake-reports").json()] != [first]
    assert [r["resolution"] for r in admin.get("/api/admin/lake-reports", params={"status": "resolved"}).json()] == ["fixed"]
    entry = db_session.scalar(select(AuditLog).where(AuditLog.action == "lake_report.fixed"))
    assert entry is not None and entry.target_id == first
