"""species_photos.py against a faked Wikipedia API — no network."""
from __future__ import annotations

import httpx
import pytest

from app.services import species_photos as sp

_REAL_GET = httpx.Client.get


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    sp.reset_state()
    monkeypatch.setattr(sp, "RETRY_DELAY_SECONDS", 0.0)
    yield
    sp.reset_state()


def _pageimages(query_titles: str) -> dict:
    pages = []
    for title in query_titles.split("|"):
        page = {"title": title}
        if title == "Bluegill":
            page["pageimage"] = "Lepomis_macrochirus_SI2.jpg"
        elif title == "Largemouth bass":
            page["pageimage"] = "Largemouth_bass_fish.jpg"
        elif title == "Channel catfish":
            page["title"] = "Channel catfish (fish)"
            page["pageimage"] = "Channel_cat.jpg"
        elif title == "White bass":
            page["pageimage"] = "NonFree.jpg"
        pages.append(page)
    return {
        "query": {
            "redirects": [{"from": "Channel catfish", "to": "Channel catfish (fish)"}],
            "pages": pages,
        }
    }


def _imageinfo(query_titles: str) -> dict:
    meta = {
        "File:Lepomis macrochirus SI2.jpg": ("<a href='//x'>Smithsonian</a> &amp; staff", "Public domain"),
        "File:Largemouth bass fish.jpg": ("Jane Doe", "CC BY-SA 4.0"),
        "File:Channel cat.jpg": ("", "CC BY 2.0"),
        "File:NonFree.jpg": ("Someone", "Fair use"),
    }
    pages = []
    for title in query_titles.split("|"):
        artist, lic = meta[title]
        pages.append(
            {
                "title": title,
                "imageinfo": [
                    {
                        "thumburl": f"https://upload.wikimedia.org/thumb/{title}/960px.jpg",
                        "thumbwidth": 960,
                        "thumbheight": 640,
                        "descriptionurl": f"https://commons.wikimedia.org/wiki/{title}",
                        "extmetadata": {
                            "Artist": {"value": artist},
                            "LicenseShortName": {"value": lic},
                            "LicenseUrl": {"value": "https://creativecommons.org/x"},
                        },
                    }
                ],
            }
        )
    return {"query": {"pages": pages}}


def _install(monkeypatch, fail: bool = False):
    calls = {"n": 0}

    def fake_get(self, url, *args, **kwargs):
        if "wikipedia.org" not in str(url):
            return _REAL_GET(self, url, *args, **kwargs)
        calls["n"] += 1
        req = httpx.Request("GET", str(url))
        if fail:
            return httpx.Response(503, request=req)
        params = kwargs["params"]
        assert params["formatversion"] == "2"
        if params["prop"] == "pageimages":
            assert params["pilicense"] == "free"
            return httpx.Response(200, json=_pageimages(params["titles"]), request=req)
        return httpx.Response(200, json=_imageinfo(params["titles"]), request=req)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    return calls


def test_all_species_are_resolved_in_two_batched_requests(monkeypatch):
    calls = _install(monkeypatch)
    photos = sp.get_photos()
    assert calls["n"] == 2
    assert set(photos) == set(sp.WIKIPEDIA_TITLES)


def test_credit_is_plain_text_and_the_licence_is_kept(monkeypatch):
    _install(monkeypatch)
    photos = sp.get_photos()
    bluegill = photos["bluegill"]
    assert bluegill is not None
    assert bluegill.author == "Smithsonian & staff"
    assert bluegill.license == "Public domain"
    assert bluegill.url.startswith("https://upload.wikimedia.org/")
    assert bluegill.file_page.startswith("https://commons.wikimedia.org/")
    lmb = photos["largemouth-bass"]
    assert lmb is not None and lmb.license == "CC BY-SA 4.0" and lmb.author == "Jane Doe"


def test_redirected_articles_still_map_back_to_their_species(monkeypatch):
    _install(monkeypatch)
    photo = sp.get_photos()["channel-catfish"]
    assert photo is not None and photo.author == "Unknown author"


def test_a_non_free_licence_is_dropped_even_if_the_api_returned_it(monkeypatch):
    _install(monkeypatch)
    assert sp.get_photos()["white-bass"] is None


def test_species_without_a_lead_image_get_none(monkeypatch):
    _install(monkeypatch)
    assert sp.get_photos()["threadfin-shad"] is None


def test_results_are_cached(monkeypatch):
    calls = _install(monkeypatch)
    sp.get_photos()
    sp.get_photos()
    assert calls["n"] == 2


def test_an_outage_returns_none_and_is_not_cached(monkeypatch):
    _install(monkeypatch, fail=True)
    assert all(v is None for v in sp.get_photos().values())
    calls = _install(monkeypatch)
    assert sp.get_photos()["bluegill"] is not None
    assert calls["n"] == 2


def test_the_circuit_opens_after_repeated_outages(monkeypatch):
    calls = _install(monkeypatch, fail=True)
    for _ in range(sp.CIRCUIT_FAILURE_THRESHOLD):
        sp.get_photos()
    before = calls["n"]
    sp.get_photos()
    assert calls["n"] == before


def test_disabled_setting_never_calls_wikipedia(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "species_photos_enabled", False)
    calls = _install(monkeypatch)
    assert all(v is None for v in sp.get_photos().values())
    assert calls["n"] == 0


def test_photos_endpoint(client, monkeypatch):
    _install(monkeypatch)
    body = client.get("/api/species/photos").json()
    assert body["bluegill"]["license"] == "Public domain"
    assert body["threadfin-shad"] is None
