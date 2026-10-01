"""species_photos.py against a faked Wikipedia API — no network."""
from __future__ import annotations

import httpx
import pytest

from app.services import species_photos as sp

# Captured before the fixture below empties it for the live-lookup tests.
CURATED = dict(sp.CURATED_PHOTOS)

_REAL_GET = httpx.Client.get


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    SEARCH.clear()
    monkeypatch.setattr(sp, "PINNED_FILES", {})
    # These tests exercise the live lookup; the curated photos have their own test.
    monkeypatch.setattr(sp, "CURATED_PHOTOS", {})
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


def _info(title: str, artist: str, lic: str, **extra) -> dict:
    return {
        "thumburl": f"https://upload.wikimedia.org/thumb/{title}/960px.jpg",
        "thumbwidth": 960,
        "thumbheight": 640,
        "width": extra.get("width", 3000),
        "mime": extra.get("mime", "image/jpeg"),
        "descriptionurl": f"https://commons.wikimedia.org/wiki/{title}",
        "extmetadata": {
            "Artist": {"value": artist},
            "LicenseShortName": {"value": lic},
            "LicenseUrl": {"value": "https://creativecommons.org/x"},
            "ImageDescription": {"value": extra.get("description", "")},
            "Categories": {"value": extra.get("categories", "")},
        },
    }


# Commons search results, by the scientific name searched for. Anything not
# listed finds nothing.
SEARCH: dict[str, list[dict]] = {}


def _search(gsrsearch: str) -> dict:
    sci = gsrsearch.split('"')[1]
    pages = [
        {"title": r["title"], "index": i + 1, "imageinfo": [r["info"]]} for i, r in enumerate(SEARCH.get(sci, []))
    ]
    return {"query": {"pages": pages}} if pages else {}


def _imageinfo(query_titles: str) -> dict:
    meta = {
        "File:Lepomis macrochirus SI2.jpg": ("<a href='//x'>Smithsonian</a> &amp; staff", "Public domain"),
        "File:Largemouth bass fish.jpg": ("Jane Doe", "CC BY-SA 4.0"),
        "File:Channel cat.jpg": ("", "CC BY 2.0"),
        "File:NonFree.jpg": ("Someone", "Fair use"),
    }
    pages = []
    for title in query_titles.split("|"):
        artist, lic = meta[title][:2]
        extra = meta[title][2] if len(meta[title]) > 2 else {}
        pages.append({"title": title, "imageinfo": [_info(title, artist, lic, **extra)]})
    return {"query": {"pages": pages}}


def _install(monkeypatch, fail: bool = False, search_fails: bool = False):
    calls = {"n": 0, "search": 0}

    def fake_get(self, url, *args, **kwargs):
        if "commons.wikimedia.org" in str(url):
            calls["search"] += 1
            req = httpx.Request("GET", str(url))
            if fail or search_fails:
                return httpx.Response(503, request=req)
            params = kwargs["params"]
            assert params["gsrnamespace"] == "6"
            return httpx.Response(200, json=_search(params["gsrsearch"]), request=req)
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


def test_lead_images_are_resolved_in_two_batched_requests(monkeypatch):
    calls = _install(monkeypatch)
    photos = sp.get_photos()
    assert calls["n"] == 2
    assert set(photos) == set(sp.WIKIPEDIA_TITLES)
    # One Commons search for each species whose lead image wasn't a usable photo.
    usable = {"bluegill", "largemouth-bass", "channel-catfish"}
    assert calls["search"] == len(sp.WIKIPEDIA_TITLES) - len(usable)


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
    searches = calls["search"]
    sp.get_photos()
    assert calls["n"] == 2
    assert calls["search"] == searches


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


# --- a photo, not a drawing ---------------------------------------------------


def test_a_drawing_as_lead_image_is_replaced_by_a_photo_from_commons(monkeypatch):
    SEARCH["Morone chrysops"] = [
        {"title": "File:White bass plate.jpg", "info": _info("File:White bass plate.jpg", "Duane Raver", "Public domain")},
        {"title": "File:Tiny.jpg", "info": _info("File:Tiny.jpg", "A", "CC BY 4.0", width=320)},
        {"title": "File:Range.png", "info": _info("File:Range.png", "B", "CC BY 4.0", mime="image/png")},
        {
            "title": "File:White bass caught.jpg",
            "info": _info("File:White bass caught.jpg", "Angler Ann", "CC BY-SA 4.0", description="A white bass on a dock"),
        },
    ]
    _install(monkeypatch)
    photo = sp.get_photos()["white-bass"]
    assert photo is not None
    assert photo.author == "Angler Ann"


def test_artwork_is_recognised_from_its_description_categories_or_credit():
    photo_like = _info("File:Fish.jpg", "Jane Doe", "CC BY 4.0", description="Caught at Lake Fork")
    assert sp._looks_like_photo("File:Fish.jpg", photo_like)
    for extra in (
        {"description": "Illustration of a bass"},
        {"categories": "Paintings of fish|Micropterus salmoides"},
        {"categories": "Duane Raver"},
        {"description": "Plate 45 from Cuvier & Valenciennes"},
    ):
        assert not sp._looks_like_photo("File:Fish.jpg", _info("File:Fish.jpg", "X", "CC BY 4.0", **extra)), extra
    assert not sp._looks_like_photo("File:Fish.jpg", _info("File:Fish.jpg", "Duane Raver", "Public domain"))
    assert not sp._looks_like_photo("File:Fish.svg", _info("File:Fish.svg", "X", "CC BY 4.0", mime="image/svg+xml"))


def test_a_failed_search_is_retried_later_rather_than_cached(monkeypatch):
    calls = _install(monkeypatch, search_fails=True)
    assert sp.get_photos()["white-bass"] is None
    SEARCH["Morone chrysops"] = [
        {"title": "File:White bass.jpg", "info": _info("File:White bass.jpg", "Ann", "CC BY 4.0")},
    ]
    calls = _install(monkeypatch)
    assert sp.get_photos()["white-bass"] is not None
    assert calls["search"] >= 1


def test_a_pinned_file_wins(monkeypatch):
    monkeypatch.setattr(sp, "PINNED_FILES", {"largemouth-bass": "Lepomis_macrochirus_SI2.jpg"})
    _install(monkeypatch)
    assert sp.get_photos()["largemouth-bass"].author == "Smithsonian & staff"


# --- curated photos -----------------------------------------------------------


def test_every_guide_species_has_a_curated_photo_served_without_network(monkeypatch):
    from app.knowledge.species_guides import GUIDES, slugify

    monkeypatch.setattr(sp, "CURATED_PHOTOS", CURATED)
    calls = _install(monkeypatch, fail=True)
    photos = sp.get_photos()
    for guide in GUIDES:
        photo = photos[slugify(guide.common_name)]
        assert photo is not None, guide.common_name
        assert photo.url.startswith("https://upload.wikimedia.org/")
        assert photo.file_page.startswith("https://commons.wikimedia.org/wiki/File:")
        assert sp._FREE_LICENSE_RE.match(photo.license)
        assert photo.author
    assert calls["n"] == 0 and calls["search"] == 0
