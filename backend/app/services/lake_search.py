"""Finding lakes by name: the map's search box (api/waterbodies.py) and Ask's
lake answers (services/rag/lake_facts.py)."""
from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.waterbody import Waterbody
from app.services.geo import haversine_km

# Facts from a state agency are credited to it next to the facts
# (data-sourcing rule 7; docs/data-sources.md).
AGENCY_CREDITS = {
    "tpwd": "Data: Texas Parks and Wildlife Department",
    "ga_wrd": "Data: Georgia DNR Wildlife Resources Division",
    "cdfw": "Data: California Department of Fish and Wildlife",
}

# Words most lake names carry one of. "lanier" means Lake Lanier as much as
# Lanier Lake, so names are also compared without them.
GENERIC_WATER_WORDS = frozenset({"lake", "lakes", "reservoir", "pond", "the", "of"})


def name_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def core_name(words: list[str]) -> str:
    return " ".join(w for w in words if w not in GENERIC_WATER_WORDS)


def _candidates(db: Session, words: list[str]) -> list[Waterbody]:
    stmt = select(Waterbody).join(Waterbody.state).options(selectinload(Waterbody.state))
    for word in words:
        stmt = stmt.where(func.lower(Waterbody.name).contains(word))
    # Enough to rank; a name every lake shares ("lake") is narrowed by the rest.
    # "+ 0" keeps the database from walking the size index in order: cheap
    # for "lake", but a rare name (the usual search) then visits every lake
    # one row at a time (400 ms for "lanier" on the dev DB, 50 ms this way).
    return list(db.scalars(stmt.order_by((Waterbody.extent_km2 + 0).desc()).limit(200)).all())


def search(
    db: Session,
    q: str,
    state_code: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
) -> list[Waterbody]:
    """Best first: the whole name, then the same name give or take "lake" or
    "reservoir", then names that start with the words, then names holding
    them all; within each, the state being looked at, the lakes FishEye
    verified, the nearest to where the map is, the biggest. "lanier" listed
    five ponds and not Lake Lanier (2026-10-30): "Lanier Pond" starts with
    the word, and a pond nearer the map beat the verified reservoir."""
    words = name_words(q)
    if not words:
        return []
    wanted = " ".join(words)
    wanted_core = core_name(words) or wanted
    picked = (state_code or "").upper()

    def rank(w: Waterbody) -> tuple[int, int, int, float, float]:
        mine = name_words(w.name)
        name = " ".join(mine)
        how = 0 if name == wanted else 1 if core_name(mine) == wanted_core else 2 if name.startswith(wanted) else 3
        away = haversine_km(lat, lng, w.latitude, w.longitude) if lat is not None and lng is not None else 0.0
        return (how, w.state.code != picked, w.data_tier != "verified", away, -w.extent_km2)

    return sorted(_candidates(db, words), key=rank)


def same_name(db: Session, name: str, state_code: str | None = None) -> list[Waterbody]:
    """Only the lakes called this, give or take "lake" or "reservoir": what a
    name in a sentence has to match, so "Travis" in passing doesn't bring up
    Travis Pond's neighbours. The state asked about first, then verified
    lakes, then the biggest."""
    words = name_words(name)
    wanted = core_name(words)
    if not wanted:
        return []
    # OpenStreetMap joins a lake's several names with ";": any of them will do.
    return [
        w
        for w in search(db, name, state_code)
        if any(core_name(name_words(part)) == wanted for part in w.name.split(";"))
    ]
