"""Ask the AI about a photo (POST /api/ask/photo, services/rag/photo.py): the
fallback when FishEye's own fish and gear checks can't name what a photo
shows (the product owner, 2026-11-13). Never the real API: the mock or a
scripted provider stands in."""
from __future__ import annotations

import io

from PIL import Image as PILImage

from app.services import llm
from app.services.llm.base import LLMResponse, LLMUnavailable
from app.services.rag import photo as rag_photo
from tests.conftest import signup


def jpeg() -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (64, 48), "green").save(buf, format="JPEG")
    return buf.getvalue()


def ask(c, question: str = "", lang: str = "en"):
    return c.post("/api/ask/photo", files={"photo": ("reel.jpg", jpeg(), "image/jpeg")},
                  data={"question": question, "lang": lang})


def signed_in(make_client):
    c = make_client()
    signup(c)
    return c


class Scripted(llm.LLMProvider):
    name = "scripted"

    def __init__(self, text: str | None):
        self.text = text
        self.calls: list[tuple[str, str, tuple]] = []

    def complete(self, system_prompt, user_prompt, images=()):
        self.calls.append((system_prompt, user_prompt, tuple(images)))
        if self.text is None:
            raise LLMUnavailable("down")
        return LLMResponse(text=self.text, provider=self.name, model="scripted", prompt_tokens=1,
                           completion_tokens=1, estimated_cost_usd=0.0, latency_ms=0.0)


def use(monkeypatch, provider):
    monkeypatch.setattr(rag_photo, "get_provider", lambda: provider)
    return provider


def test_asking_about_a_photo_needs_an_account(make_client):
    assert ask(make_client()).status_code == 401


def test_an_answer_uses_one_of_the_days_ai_answers_and_sees_the_photo(make_client, monkeypatch):
    c = signed_in(make_client)
    model = use(monkeypatch, Scripted('{"answer": "A spinning reel, filled with braided line nearly to the lip."}'))
    body = ask(c, "is this too much line?", "en").json()
    assert body["answer_source"] == "llm"
    assert body["answer"].startswith("A spinning reel")
    assert body["ai"]["remaining"] == 2

    system, prompt, images = model.calls[0]
    assert "Never identify or describe a person" in system
    assert "is this too much line?" in prompt and "Answer in English." in prompt
    assert len(images) == 1 and images[0].media_type == "image/jpeg"
    assert images[0].data[:3] == b"\xff\xd8\xff"  # re-encoded as a JPEG by clean_photo


def test_the_answer_comes_in_the_sites_language(make_client, monkeypatch):
    c = signed_in(make_client)
    model = use(monkeypatch, Scripted('{"answer": "这是一个纺车轮。"}'))
    ask(c, "", "zh")
    assert "Answer in Simplified Chinese." in model.calls[0][1]


def test_a_photo_that_isnt_about_fishing_is_given_back(make_client, monkeypatch):
    c = signed_in(make_client)
    use(monkeypatch, Scripted('{"off_topic": true}'))
    body = ask(c).json()
    assert body["answer_source"] == "off_topic" and body["answer"] is None
    assert body["ai"]["remaining"] == 3


def test_a_failed_or_unusable_answer_is_given_back(make_client, monkeypatch):
    c = signed_in(make_client)
    for provider in (Scripted(None), Scripted("not json"), Scripted('{"answer": "See https://example.com"}')):
        use(monkeypatch, provider)
        body = ask(c).json()
        assert body["answer_source"] == "fallback" and body["answer"] is None
        assert body["ai"]["remaining"] == 3


def test_the_days_answers_are_shared_with_text_questions(make_client, monkeypatch):
    c = signed_in(make_client)
    use(monkeypatch, Scripted('{"answer": "A bobber."}'))
    for _ in range(3):
        assert ask(c).status_code == 200
    refused = ask(c)
    assert refused.status_code == 429 and "today's free AI answers" in refused.json()["detail"]


def test_a_file_that_isnt_a_photo_is_refused_before_anything_is_used(make_client, monkeypatch):
    c = signed_in(make_client)
    use(monkeypatch, Scripted('{"answer": "x"}'))
    resp = c.post("/api/ask/photo", files={"photo": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 422
    assert c.get("/api/ask/allowance").json()["remaining"] == 3
