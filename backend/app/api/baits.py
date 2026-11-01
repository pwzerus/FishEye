"""Baits and lures as linked terms (knowledge/bait_terms.py): the cards a
tapped word in an answer opens. Static text from the guides and handbook,
so it is cached by the browser for a day."""
from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.species import source_out
from app.knowledge.bait_terms import all_cards
from app.knowledge.species_guides import sources_for

router = APIRouter(prefix="/baits", tags=["baits"])

_CARDS = [
    {**c, "sources": [source_out(s).model_dump() for s in sources_for(tuple(c.pop("source_ids")))]}
    for c in all_cards()
]


@router.get("")
def list_baits(response: Response) -> list[dict]:
    response.headers["Cache-Control"] = "public, max-age=86400"
    return _CARDS
