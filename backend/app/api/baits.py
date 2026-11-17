"""Baits and lures as linked terms (knowledge/bait_terms.py): the cards a
tapped word in an answer opens. Static text from the guides and handbook,
in the reader's language where the tables have it (`lang`, as the handbook
takes it), so it is cached by the browser for a day."""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Response

from app.api.species import source_out
from app.knowledge.bait_terms import all_cards
from app.knowledge.species_guides import sources_for
from app.knowledge.translations import LANGUAGES

router = APIRouter(prefix="/baits", tags=["baits"])


@lru_cache(maxsize=None)
def _cards(lang: str) -> list[dict]:
    return [
        {**c, "sources": [source_out(s).model_dump() for s in sources_for(tuple(c.pop("source_ids")))]}
        for c in all_cards(lang)
    ]


@router.get("")
def list_baits(response: Response, lang: str = "en") -> list[dict]:
    response.headers["Cache-Control"] = "public, max-age=86400"
    return _cards(lang if lang in LANGUAGES else "en")
