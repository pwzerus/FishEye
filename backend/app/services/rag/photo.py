"""Ask the AI about a photo (Ask's camera, when FishEye's own checks can't say).

FishEye reads a photo itself first: the fish check (services/fish_id.py), then
the gear check (services/gear_id.py). Only when neither can say what it shows
does Ask offer this, on a signed-in account, as one of the day's AI answers
(services/ai_quota.py): FishEye's own models are free for everyone, and
Claude is the fallback (the product owner, 2026-11-13).

The photo is already cleaned (services/media.clean_photo: re-encoded, its
metadata and location gone) and is not kept. The model answers about fishing
only, never describes people, and never states a regulation.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.services.llm import LLMUnavailable, get_provider
from app.services.llm.base import Image

MAX_ANSWER_CHARS = 1200
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)

LANGUAGE_NAMES = {
    "en": "English", "zh": "Simplified Chinese", "zht": "Traditional Chinese",
    "es": "Spanish", "ja": "Japanese", "ko": "Korean",
}

SYSTEM_PROMPT = """You are FishEye's fishing helper. A beginner angler in the \
United States sent a photo, maybe with a question.

Rules:
- Say plainly what the photo shows that matters for fishing: a fish (which \
kind, if you can tell), tackle (a rod, reel, line, lure, hook, rig or knot) or \
a place to fish. Then give one to three practical points about it, or answer \
the question if there is one. If you can't tell, say so; don't guess with \
false confidence.
- Fishing only. If the photo has nothing to do with fishing, reply with \
{"off_topic": true} and nothing more.
- Never identify or describe a person in the photo.
- Never state a size limit, bag limit, license price, season date or any other \
regulation; say the state's fish and wildlife agency has the current rules.
- Never write a URL.
- Voice: plain and professional, 2-5 sentences. Start with the answer. No \
greetings, praise or sign-offs, no em dashes. Write the language as a native \
speaker writes it, in standard written form.

Reply with ONLY a JSON object, no prose around it: {"answer": str}"""

ANSWER_LLM = "llm"
ANSWER_OFF_TOPIC = "off_topic"
ANSWER_FALLBACK = "fallback"


@dataclass(frozen=True)
class PhotoAnswer:
    answer: str | None
    source: str  # ANSWER_LLM | ANSWER_OFF_TOPIC | ANSWER_FALLBACK
    provider: str = "none"


def user_prompt(question: str, lang: str | None) -> str:
    language = LANGUAGE_NAMES.get(lang or "en", "English")
    asked = " ".join(question.split())[:300]
    said = f"<question>{asked}</question>" if asked else "<question>What is this?</question>"
    return f"{said}\nAnswer in {language}."


def parse(raw: str) -> PhotoAnswer:
    """The model's reply, checked: JSON of the right shape, not too long, no
    links. Anything else is a fallback, and the answer is given back."""
    match = _JSON_OBJECT_RE.search(raw or "")
    try:
        payload = json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        payload = None
    if not isinstance(payload, dict):
        return PhotoAnswer(None, ANSWER_FALLBACK)
    if payload.get("off_topic") is True:
        return PhotoAnswer(None, ANSWER_OFF_TOPIC)
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_ANSWER_CHARS or _URL_RE.search(answer):
        return PhotoAnswer(None, ANSWER_FALLBACK)
    return PhotoAnswer(answer.strip(), ANSWER_LLM)


def ask_about_photo(jpeg: bytes, question: str = "", lang: str | None = None) -> PhotoAnswer:
    """Never raises on a model failure: that is a fallback, which the caller
    gives back to the day's allowance."""
    llm = get_provider()
    try:
        response = llm.complete(SYSTEM_PROMPT, user_prompt(question, lang), [Image("image/jpeg", jpeg)])
    except LLMUnavailable:
        return PhotoAnswer(None, ANSWER_FALLBACK, getattr(llm, "name", "unknown"))
    result = parse(response.text)
    return PhotoAnswer(result.answer, result.source, response.provider)
