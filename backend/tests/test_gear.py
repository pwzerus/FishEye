"""What to buy (app/knowledge/gear.py, GET /api/gear)."""
import re
from pathlib import Path

from app.cli.fish_id_commons import licence_ok
from app.knowledge import gear
from app.knowledge.angling_handbook import TOPICS
from app.knowledge.gear_photos import PHOTOS
from app.knowledge.species_guides import GUIDES

PUBLIC = Path(__file__).resolve().parents[2] / "frontend" / "public"


def test_every_item_links_a_real_topic_and_real_fish():
    topics = {t.id for t in TOPICS}
    slugs = {g.slug for g in GUIDES}
    for i in gear.ITEMS:
        assert i.category in gear.CATEGORIES, i.id
        assert i.topic is None or i.topic in topics, (i.id, i.topic)
        assert set(i.fish) <= slugs, (i.id, set(i.fish) - slugs)
    assert len({i.id for i in gear.ITEMS}) == len(gear.ITEMS)


def test_photos_are_open_licence_and_credited():
    for item, p in PHOTOS.items():
        assert item in gear.ITEM_BY_ID, item
        assert licence_ok(p.licence), (item, p.licence)
        assert p.author and p.author.lower() not in ("own work", "unknown author"), item
        if p.url.startswith("/gear-photos/"):
            # Self-hosted (a Flickr photo or a crop of a Commons one), so the file has to be in the repo.
            assert p.url == f"/gear-photos/{item}.jpg", item
            if p.file.startswith("Flickr:"):
                assert p.page.startswith("https://www.flickr.com/photos/"), item
                assert p.title, item  # CC BY 2.0 wants the work's title shown
            else:
                assert p.file.startswith("Crop:") and p.page.startswith("https://commons.wikimedia.org/wiki/File:"), item
            if PUBLIC.is_dir():  # the frontend isn't there when only the backend is checked out
                assert (PUBLIC / p.url.lstrip("/")).is_file(), item
            continue
        assert p.url.startswith("https://") and "wikimedia.org" in p.url, item
        assert p.page.startswith("https://commons.wikimedia.org/wiki/File:"), item
        # Wikimedia serves only its standard thumbnail widths (or the original).
        width = re.search(r"/(\d+)px-", p.url)
        assert width is None or width.group(1) in ("250", "330", "500", "960", "1280"), item


def test_every_item_has_a_photo_of_its_own():
    assert set(PHOTOS) == set(gear.ITEM_BY_ID)
    for field in ("file", "url", "page"):
        values = [getattr(p, field) for p in PHOTOS.values()]
        assert len(set(values)) == len(values), field


def test_no_brands_or_prices_in_the_text():
    for i in gear.ITEMS:
        text = f"{i.name} {i.what} {i.tip}"
        assert "$" not in text, i.id
        assert not re.search(r"\b(rapala|berkley|zebco|shimano|daiwa|abu garcia|powerbait)\b", text, re.I), i.id


def test_a_first_kit_is_short_and_has_the_basics():
    kit = [i.id for i in gear.ITEMS if i.first_kit]
    assert 6 <= len(kit) <= 12
    for basic in ("hook-j", "bobber", "sinker-split-shot", "bait-nightcrawler", "tool-lifejacket"):
        assert basic in kit


def test_gear_endpoint(client):
    body = client.get("/api/gear").json()
    assert [c["id"] for c in body["categories"]] == list(gear.CATEGORIES)
    assert len(body["items"]) == len(gear.ITEMS)
    order = [c["id"] for c in body["categories"]]
    assert [order.index(i["category"]) for i in body["items"]] == sorted(order.index(i["category"]) for i in body["items"])
    with_photo = [i for i in body["items"] if i["photo"]]
    assert with_photo and all(i["photo"]["author"] and i["photo"]["license"] for i in with_photo)
