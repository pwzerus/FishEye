"""The gear camera on /gear: how a reading becomes an answer, and the endpoint."""
import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.knowledge.gear import ITEM_BY_ID
from app.services import gear_id
from app.services.gear_id import GearCandidate, GearReading, item_probabilities, message
from tests.conftest import signup

MODEL = Path(__file__).resolve().parents[1] / "models" / "gear-id"


def test_item_probabilities_add_up_and_follow_the_groups():
    rng = np.random.default_rng(0)
    d, classes = 8, 5
    text = rng.normal(size=(classes, d))
    text /= np.linalg.norm(text, axis=1, keepdims=True)
    vec = text[1] + 0.1 * rng.normal(size=d)
    vec /= np.linalg.norm(vec)
    # Two groups sharing class 2 (as a spincast combo is a rod and a reel).
    members = np.array([[1, 1, 1, 0, 0], [0, 0, 1, 1, 1]], dtype=np.float32)
    wg = rng.normal(size=(2, d))
    p = item_probabilities(vec, text, wg, np.zeros(2), members, alpha=0.5, fine_scale=100.0)
    assert p.shape == (classes,) and abs(p.sum() - 1) < 1e-6 and (p >= 0).all()
    assert int(np.argmax(p)) == 1  # the photo is most like class 1
    # A head sure of the second group moves nearly everything there.
    sure = item_probabilities(vec, text, np.zeros((2, d)), np.array([-50.0, 50.0]), members, alpha=1.0, fine_scale=100.0)
    assert sure[[2, 3, 4]].sum() > 0.99
    # With alpha 0 the head has no say.
    a = item_probabilities(vec, text, wg, np.zeros(2), members, alpha=0.0, fine_scale=100.0)
    b = item_probabilities(vec, text, -wg, np.ones(2), members, alpha=0.0, fine_scale=100.0)
    assert np.allclose(a, b)


def reading(gear_p, *items, not_gear=None):
    return GearReading(gear_p, tuple(GearCandidate(i, p) for i, p in items), not_gear, "stand-in")


def test_messages():
    assert message(reading(0.9, ("reel-spinning", 0.8), ("reel-baitcasting", 0.1))) == "This looks like: Spinning reel."
    assert message(reading(0.9, ("lure-crankbait", 0.4), ("lure-jerkbait", 0.35))).startswith("It could be one of these")
    assert "fish, not fishing gear" in message(reading(0.2, ("rod-spinning", 0.5), not_gear="x-fish"))
    assert message(reading(0.2, ("rod-spinning", 0.5), not_gear="x-city")).startswith("We couldn't find fishing gear")
    # Gear, maybe, but nothing stands out: nothing is offered.
    blurred = reading(0.8, ("float-slip", 0.09), ("lure-grub", 0.06), not_gear="x-fish")
    assert not blurred.is_gear and message(blurred).startswith("We couldn't tell what gear this is")


class StandIn:
    """Reads the photo's colour: green is a spinning reel, blue one of two
    lures, red not gear (a fish)."""

    name = "stand-in"

    def read(self, photo: bytes) -> GearReading:
        r, g, b = Image.open(io.BytesIO(photo)).convert("RGB").resize((1, 1)).getpixel((0, 0))
        if g > 100 and r < 100:
            return reading(0.95, ("reel-spinning", 0.85), ("reel-baitcasting", 0.1), ("combo-spincast", 0.05))
        if b > 100 and r < 100:
            return reading(0.9, ("lure-crankbait", 0.45), ("lure-jerkbait", 0.4), ("lure-lipless", 0.1),
                           ("lure-popper", 0.05))
        return reading(0.1, ("rod-spinning", 0.6), not_gear="x-fish")


def jpeg(colour: str) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (300, 200), colour).save(out, format="JPEG")
    return out.getvalue()


def ask(c, colour):
    return c.post("/api/gear/identify", files={"photo": ("p.jpg", jpeg(colour), "image/jpeg")})


@pytest.fixture()
def camera(monkeypatch):
    monkeypatch.setattr(gear_id, "get_recognizer", lambda: StandIn())


def test_a_clear_photo_names_the_item(make_client, camera):
    body = ask(make_client(), "green").json()
    assert body["available"] and body["sure"]
    assert [c["id"] for c in body["candidates"]] == ["reel-spinning", "reel-baitcasting", "combo-spincast"]
    assert body["candidates"][0]["name"] == ITEM_BY_ID["reel-spinning"].name
    assert body["message"] == "This looks like: Spinning reel."


def test_an_unsure_photo_offers_three_to_compare(make_client, camera):
    body = ask(make_client(), "blue").json()
    assert not body["sure"] and len(body["candidates"]) == 3
    assert body["message"].startswith("It could be one of these")


def test_a_photo_without_gear_names_nothing(make_client, camera):
    body = ask(make_client(), "red").json()
    assert body["candidates"] == [] and body["gear_probability"] == 0.1
    assert body["not_gear"] == "fish" and "fish, not fishing gear" in body["message"]


def test_signed_out_it_is_a_small_daily_trial(make_client, camera, monkeypatch):
    from app.api import gear as gear_api

    monkeypatch.setattr(gear_api.gear_id_trial_by_ip, "limit", 2)
    c = make_client()
    assert [ask(c, "green").status_code for _ in range(3)] == [200, 200, 429]
    assert ask(c, "green").json()["detail"] == gear_api.TRIAL_USED
    signup(c)  # signed in, the account's own allowance applies
    assert ask(c, "green").status_code == 200


def test_not_a_photo_is_refused(make_client, camera):
    c = make_client()
    resp = c.post("/api/gear/identify", files={"photo": ("p.jpg", b"not a picture", "image/jpeg")})
    assert resp.status_code == 422


def test_switched_off_it_says_so(make_client):
    body = ask(make_client(), "green").json()
    assert body == {"available": False, "model": None, "gear_probability": None, "sure": False,
                    "candidates": [], "not_gear": None, "message": None}


def test_without_its_model_it_asks_to_try_later(make_client, monkeypatch):
    def unavailable():
        raise gear_id.GearIdUnavailable("The gear camera isn't available right now. Try again later.")

    monkeypatch.setattr(gear_id, "get_recognizer", unavailable)
    resp = ask(make_client(), "green")
    assert resp.status_code == 503 and "Try again later" in resp.json()["detail"]


@pytest.mark.skipif(not (MODEL / "SOURCE.json").exists(), reason="gear-id model not built (docs/adr/0048)")
def test_the_built_model_offers_nothing_for_a_plain_picture():
    recognizer = gear_id.GearRecognizer(MODEL)
    out = io.BytesIO()
    Image.new("RGB", (400, 300), (40, 120, 200)).save(out, format="JPEG")
    r = recognizer.read(out.getvalue())
    assert abs(sum(c.probability for c in r.candidates) - 1) < 1e-3
    assert not r.is_gear  # nothing stands out in a flat blue picture


def test_the_page_shows_the_camera_only_when_it_can_answer(make_client, monkeypatch, tmp_path):
    from app.core.config import get_settings

    c = make_client()
    assert c.get("/api/gear").json()["camera"] is False  # GEAR_ID=off in the tests
    monkeypatch.setattr(get_settings(), "gear_id", "on")
    monkeypatch.setattr(get_settings(), "gear_id_model_dir", str(tmp_path))
    assert c.get("/api/gear").json()["camera"] is False  # on, but no model there
    for name in ("image_int8.onnx", "head.npz", "text.npy", "SOURCE.json"):
        (tmp_path / name).write_bytes(b"x")
    assert c.get("/api/gear").json()["camera"] is True
