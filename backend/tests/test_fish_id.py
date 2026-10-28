"""The photo check on catches: the policy, the class list, and the API with a
stand-in recognizer (the real model is 300 MB and not in the test suite)."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from app.knowledge.species_guides import GUIDES
from app.services import fish_id
from app.services.fish_id import CONFIRMED, GROUP, MISMATCH, NO_FISH, OTHER, UNSURE, Candidate, Identification, check_claim
from app.services.fish_id_classes import BY_SLUG, CLAIM_GROUPS, CLASSES, GUIDE
from tests.conftest import signup


def ident(**probs: float) -> Identification:
    """An identification giving these classes these probabilities (slugs
    with underscores for dashes); the rest share what is left."""
    probs = {k.replace("_", "-"): v for k, v in probs.items()}
    rest = [c for c in CLASSES if c.slug not in probs]
    left = max(0.0, 1.0 - sum(probs.values())) / len(rest)
    cands = [Candidate(c.slug, c.common, c.kind, probs.get(c.slug, left)) for c in CLASSES]
    return Identification(tuple(sorted(cands, key=lambda c: -c.probability)), "stand-in")


# ---------------------------------------------------------------- policy


def test_the_species_shown_is_confirmed():
    v = check_claim(ident(largemouth_bass=0.9), "largemouth-bass")
    assert v.status == CONFIRMED and v.accepted


def test_a_catfish_posted_as_a_bass_is_refused_and_named():
    v = check_claim(ident(channel_catfish=0.8), "largemouth-bass")
    assert v.status == MISMATCH and not v.accepted
    assert v.detected == "channel-catfish"
    assert "Channel Catfish, not a Largemouth Bass" in v.message


def test_a_look_alike_is_accepted_as_its_group_not_as_the_species():
    v = check_claim(ident(spotted_bass=0.55, largemouth_bass=0.3), "largemouth-bass")
    assert v.status == GROUP and v.accepted
    assert "a black bass" in v.message and "your call" in v.message


def test_a_fish_with_no_guide_is_named_and_refused():
    v = check_claim(ident(walleye=0.9), "largemouth-bass")
    assert v.status == OTHER and not v.accepted
    assert "Walleye" in v.message and "Other" in v.message


def test_an_angler_holding_the_fish_still_counts():
    # The person may fill most of a catch photo; which fish is decided among fish.
    v = check_claim(ident(person=0.4, largemouth_bass=0.55), "largemouth-bass")
    assert v.status == CONFIRMED and v.accepted


def test_no_fish_is_refused():
    v = check_claim(ident(dog=0.9), "bluegill")
    assert v.status == NO_FISH and not v.accepted


def test_a_photo_that_says_too_little_asks_for_another():
    v = check_claim(ident(largemouth_bass=0.25, bluegill=0.2, walleye=0.2, common_carp=0.2), "bluegill")
    assert v.status == UNSURE and not v.accepted


def test_the_hybrid_is_checked_as_a_white_or_striped_bass():
    assert check_claim(ident(striped_bass=0.7, white_bass=0.2), "hybrid-striped-bass").status == GROUP
    assert check_claim(ident(channel_catfish=0.9), "hybrid-striped-bass").status == MISMATCH


def test_other_needs_a_fish_and_not_plainly_a_guide_species():
    assert check_claim(ident(walleye=0.9), None).accepted
    plain = check_claim(ident(bluegill=0.9), None)
    assert plain.status == MISMATCH and "Bluegill" in plain.message
    assert not check_claim(ident(person=0.95), None).accepted


# ---------------------------------------------------------------- classes


def test_every_guide_species_can_be_checked():
    for g in GUIDES:
        assert (g.slug in BY_SLUG and BY_SLUG[g.slug].kind == GUIDE) or g.slug in CLAIM_GROUPS, g.slug


def test_every_look_alike_group_says_what_it_is():
    for c in CLASSES:
        if c.kind == GUIDE and sum(1 for o in CLASSES if o.group == c.group) > 1:
            assert c.group_label, c.slug


# ---------------------------------------------------------------- API

COLOURS = {"green": "largemouth-bass", "blue": "channel-catfish", "gray": "spotted-bass", "red": "dog"}


class StandIn:
    """Reads the photo's colour: green is a largemouth bass, blue a channel
    catfish, grey a black bass of unclear kind, red no fish at all."""

    name = "stand-in"

    def identify(self, photo: bytes) -> Identification:
        r, g, b = Image.open(io.BytesIO(photo)).convert("RGB").resize((1, 1)).getpixel((0, 0))
        colour = "green" if g > 100 and r < 100 else "blue" if b > 100 and r < 100 else "red" if r > 150 and g < 100 else "gray"
        slug = COLOURS[colour]
        if colour == "gray":
            return ident(spotted_bass=0.5, largemouth_bass=0.35)
        return ident(**{slug.replace("-", "_"): 0.9})


def jpeg(colour: str) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (300, 200), colour).save(out, format="JPEG")
    return out.getvalue()


@pytest.fixture()
def checking(monkeypatch):
    monkeypatch.setattr(fish_id, "get_recognizer", lambda: StandIn())


def create(c, photos=(), **fields):
    data = {"latitude": 32.8, "longitude": -95.6, "title": "Dam bank", **fields}
    files = [("photos", (f"p{i}.jpg", b, "image/jpeg")) for i, b in enumerate(photos)]
    return c.post("/api/pins", data=data, files=files or None)


def test_a_catch_whose_photo_shows_the_fish_is_saved_as_checked(make_client, checking):
    c = make_client()
    signup(c)
    resp = create(c, photos=[jpeg("green")], species_slug="largemouth-bass")
    assert resp.status_code == 201, resp.text
    pin = resp.json()
    assert pin["species_check"] == "confirmed" and pin["species_check_label"] is None


def test_a_catch_whose_photo_shows_another_fish_is_refused(make_client, checking):
    c = make_client()
    signup(c)
    resp = create(c, photos=[jpeg("blue")], species_slug="largemouth-bass")
    assert resp.status_code == 422
    assert "Channel Catfish" in resp.json()["detail"]
    assert c.get("/api/pins", params={"mine": True}).json() == []


def test_a_look_alike_is_saved_with_the_group_it_showed(make_client, checking):
    c = make_client()
    signup(c)
    pin = create(c, photos=[jpeg("gray")], species_slug="smallmouth-bass").json()
    assert pin["species_check"] == "group" and pin["species_check_label"] == "a black bass"


def test_naming_a_species_needs_a_photo(make_client, checking):
    c = make_client()
    signup(c)
    resp = create(c, species_slug="bluegill")
    assert resp.status_code == 422 and "photo" in resp.json()["detail"]
    # A spot with no fish named needs none.
    assert create(c, title="Quiet cove").status_code == 201


def test_other_naming_a_guide_species_is_checked_as_it(make_client, checking):
    c = make_client()
    signup(c)
    resp = create(c, photos=[jpeg("blue")], species_other="Largemouth bass")
    assert resp.status_code == 422
    pin = create(c, photos=[jpeg("green")], species_other="largemouth bass").json()
    assert pin["species_slug"] == "largemouth-bass" and pin["species_check"] == "confirmed"


def test_a_changed_species_is_checked_against_the_catch_photo(make_client, checking):
    c = make_client()
    signup(c)
    pin = create(c, photos=[jpeg("green")], species_slug="largemouth-bass").json()
    refused = c.patch(f"/api/pins/{pin['id']}", json={"species_slug": "blue-catfish"})
    assert refused.status_code == 422
    assert c.get(f"/api/pins/{pin['id']}").json()["species_slug"] == "largemouth-bass"
    cleared = c.patch(f"/api/pins/{pin['id']}", json={"clear_species": True}).json()
    assert cleared["species_slug"] is None and cleared["species_check"] is None


def test_the_catch_photo_stays_while_a_species_is_named(make_client, checking):
    c = make_client()
    signup(c)
    pin = create(c, photos=[jpeg("green"), jpeg("red")], species_slug="largemouth-bass").json()
    first, second = (p["id"] for p in pin["photos"])
    assert c.delete(f"/api/pins/{pin['id']}/photos/{first}").status_code == 409
    assert c.delete(f"/api/pins/{pin['id']}/photos/{second}").status_code == 200


def test_catches_wait_while_the_check_is_unavailable(make_client, monkeypatch):
    def unavailable():
        raise fish_id.FishIdUnavailable("The photo check isn't available right now. Try again later.")

    monkeypatch.setattr(fish_id, "get_recognizer", unavailable)
    c = make_client()
    signup(c)
    assert create(c, photos=[jpeg("green")], species_slug="largemouth-bass").status_code == 503


def test_the_form_can_ask_before_saving(make_client, checking):
    c = make_client()
    assert c.post("/api/fish-id", files={"photo": ("p.jpg", jpeg("blue"), "image/jpeg")}).status_code == 401
    signup(c)
    body = c.post(
        "/api/fish-id",
        data={"species_slug": "largemouth-bass"},
        files={"photo": ("p.jpg", jpeg("blue"), "image/jpeg")},
    ).json()
    assert body["available"] and body["candidates"][0]["slug"] == "channel-catfish"
    assert body["candidates"][0]["in_guides"] is True
    assert body["verdict"]["status"] == "mismatch" and body["verdict"]["detected_label"] == "Channel Catfish"
    # No species given: just what it looks like.
    plain = c.post("/api/fish-id", files={"photo": ("p.jpg", jpeg("green"), "image/jpeg")}).json()
    assert plain["verdict"] is None and plain["candidates"][0]["label"] == "Largemouth Bass"


def test_the_form_hears_when_the_check_is_off(make_client):
    c = make_client()
    signup(c)
    body = c.post("/api/fish-id", files={"photo": ("p.jpg", jpeg("green"), "image/jpeg")}).json()
    assert body == {"available": False, "model": None, "fish_probability": None, "candidates": [], "verdict": None}


# ------------------------------------------------------- the real model

MODEL = Path("models/fish-id")


@pytest.mark.skipif(not (MODEL / "SOURCE.json").exists(), reason="fish-id model not built (app/cli/build_fish_id_model.py)")
def test_the_installed_model_loads_and_answers():
    recognizer = fish_id.FishRecognizer(MODEL)
    result = recognizer.identify(jpeg("green"))
    assert abs(sum(c.probability for c in result.candidates) - 1.0) < 1e-4
    assert {c.slug for c in result.candidates} >= {c.slug for c in CLASSES}


@pytest.mark.skipif(not (MODEL / "SOURCE.json").exists(), reason="fish-id model not built (app/cli/build_fish_id_model.py)")
def test_a_photo_checked_twice_is_read_once():
    recognizer = fish_id.FishRecognizer(MODEL)
    reads = []
    embed = recognizer.embed
    recognizer.embed = lambda img: reads.append(1) or embed(img)
    first = recognizer.identify(jpeg("green"))
    again = recognizer.identify(jpeg("green"))
    assert len(reads) == 1 and first.candidates == again.candidates
