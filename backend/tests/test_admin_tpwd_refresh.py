"""Tests for the admin TPWD manual-refresh endpoint. Network-free — the
real scraper is monkeypatched out, same philosophy as
test_tpwd_lake_survey_scraper.py (no live HTTP in a suite that runs on
every commit)."""
import pytest

from app.core.config import get_settings
from app.data_import.tpwd_lake_survey_scraper import IngestSummary, LakeResult
from app.services import tpwd_refresh_job as job_module

ADMIN_TOKEN = "test-admin-token"


@pytest.fixture(autouse=True)
def _reset_job_singleton():
    # The job tracker is a module-level singleton shared across the whole
    # test process — reset it before and after every test so state from
    # one test can't leak into the next.
    job_module.tpwd_refresh_job.reset()
    yield
    job_module.tpwd_refresh_job.reset()


@pytest.fixture()
def admin_token_configured(monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", ADMIN_TOKEN)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_refresh_returns_503_when_token_not_configured(client, monkeypatch):
    # Explicitly force "unconfigured" rather than relying on the ambient
    # environment having no ADMIN_API_TOKEN — a developer's own local
    # .env (which pydantic-settings reads regardless of monkeypatch env
    # vars set here) can otherwise make this test's premise false.
    monkeypatch.setenv("ADMIN_API_TOKEN", "")
    get_settings.cache_clear()
    resp = client.post("/api/admin/tpwd-refresh")
    assert resp.status_code == 503
    get_settings.cache_clear()


def test_refresh_returns_401_without_header(client, admin_token_configured):
    resp = client.post("/api/admin/tpwd-refresh")
    assert resp.status_code == 401


def test_refresh_returns_401_with_wrong_token(client, admin_token_configured):
    resp = client.post("/api/admin/tpwd-refresh", headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 401


def test_refresh_returns_409_when_already_running(client, admin_token_configured):
    started = job_module.tpwd_refresh_job.try_start()
    assert started is True  # sanity check on the fixture's own setup

    resp = client.post("/api/admin/tpwd-refresh", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert resp.status_code == 409


def test_refresh_triggers_job_and_status_reflects_result(client, admin_token_configured, monkeypatch):
    fake_summary = IngestSummary(
        lake_results=[
            LakeResult("Lake Somerville", "written", species_written=3),
            LakeResult("Lake Livingston", "skipped_no_url", detail="no survey_index_url resolved yet"),
        ],
        total_written=3,
        total_access_points_written=2,
        dry_run=True,
    )
    monkeypatch.setattr(job_module, "run_scraper", lambda dry_run=False: fake_summary)

    trigger_resp = client.post("/api/admin/tpwd-refresh?dry_run=true", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert trigger_resp.status_code == 202
    assert trigger_resp.json()["status"] == "running"

    # TestClient runs BackgroundTasks synchronously as part of the request
    # cycle, so by the time the POST above returns, the fake job has
    # already completed — the status endpoint should reflect that.
    status_resp = client.get("/api/admin/tpwd-refresh/status", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] == "done"
    assert body["total_written"] == 3
    assert body["dry_run"] is True
    names = {r["name"] for r in body["lake_results"]}
    assert names == {"Lake Somerville", "Lake Livingston"}


def test_refresh_status_reports_error_without_leaving_job_stuck_running(
    client, admin_token_configured, monkeypatch
):
    def boom(dry_run=False):
        raise RuntimeError("network exploded")

    monkeypatch.setattr(job_module, "run_scraper", boom)

    trigger_resp = client.post("/api/admin/tpwd-refresh", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert trigger_resp.status_code == 202

    status_resp = client.get("/api/admin/tpwd-refresh/status", headers={"X-Admin-Token": ADMIN_TOKEN})
    body = status_resp.json()
    assert body["status"] == "error"
    assert "network exploded" in body["error"]

    # A failed run must not leave the job wedged in RUNNING forever — a
    # second trigger should be accepted, not rejected with 409.
    monkeypatch.setattr(
        job_module,
        "run_scraper",
        lambda dry_run=False: IngestSummary(
            lake_results=[], total_written=0, total_access_points_written=0, dry_run=dry_run
        ),
    )
    retry_resp = client.post("/api/admin/tpwd-refresh", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert retry_resp.status_code == 202
