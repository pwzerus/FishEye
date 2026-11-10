"""Ask's answers about particular lakes, from the database and no model.

The guides say how to catch a fish; only the lake data can say whether it's
in Lake Travis, or which lakes near Dallas have crappie. Two kinds of
question get an answer here, shown beside whatever the guides say:

- a lake named in the question: what is on record there (each fish with the
  evidence behind it, on the lake's page), and whether the fish asked about
  is among them;
- where to go: lakes on record for a fish, near a place or in a state.

"No record" is never "not there": most lakes have never been surveyed, so an
answer says what FishEye has and no more. Closed lakes aren't suggested.

Only the place named after "near" leaves the server (services/geocoding.py,
as the map's search does). Nothing here reaches the AI summary, which answers
from guide passages alone (docs/adr/0023).
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.spatial import radius_filter
from app.knowledge import jurisdictions
from app.knowledge.species_guides import get_guide
from app.models.waterbody import Species, Waterbody, WaterbodySpecies
from app.schemas.ask import AskAskedFishOut, AskLakeFishOut, AskLakeOut, AskLakesOut
from app.services import counties, geocoding, lake_search
from app.services.geo import haversine_km
from app.services.reported_species import reported_species

MAX_LAKES = 5
NEAR_RADIUS_KM = 80.0

_WATER_WORDS = frozenset({"lake", "reservoir", "pond"})
# Words around "lake" that aren't its name: "a good crappie lake", "the lake".
_NOT_A_NAME = frozenset(
    """a an the this that these those my our your his her their its any some which what whose each every one
    big small little large huge tiny local nearby near good best better great nice new old private public deep
    shallow muddy clear-water manmade man-made farm neighborhood city community stocked closest nearest favorite
    fishing fish fishes bass crappie catfish trout walleye pike perch bluegill sunfish carp bullhead salmon kokanee
    bait baits lure lures in on at for of to from and or with by about around is are was were do does did can could
    should would will how where when why who have has had there here it they you i we me get got catch caught bite
    biting live lives go going have what's whats whos""".split()
)
# Allowed inside a name, never at its edge: "Lake of the Ozarks", "Lake O' the Pines".
_NAME_GLUE = frozenset({"of", "the", "o'", "o’"})
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’.-]*|O['’]")
_CHUNK = re.compile(r"[A-Za-z0-9'’. -]+")

# "what's in Lake Travis": the lake card is the answer, and guide passages
# found for the words "fish" and "in" would only be in the way.
_ASKS_WHATS_THERE = re.compile(
    r"\b(what|which) (fish|species|kinds?|types?)\b|\bwhat('?s| is| can i catch| lives?| bites?)\b.*\b(in|at|on)\b"
    r"|\bis there (fish|good fishing)\b|\bany fish\b|有什么鱼|什么鱼|有哪些鱼|qu[eé] peces|어떤 물고기|무슨 물고기|どんな魚|何が釣れ",
    re.IGNORECASE,
)
_ASKS_WHERE = re.compile(
    r"\bwhere\b.*\b(catch|fish|find|go|caught)\b|\b(which|what|best|good|top)\b.*\b(lakes?|ponds?|reservoirs?|places?|spots?)\b"
    r"|\blakes?\b.*\b(near|around|with|for|have|has)\b|哪里|哪儿|哪些湖|哪个湖|什么湖|d[oó]nde|어디|どこ",
    re.IGNORECASE,
)
_NEAR = re.compile(r"\b(?:near|around|close to|outside of|outside)\s+(?!me\b)([A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3})", re.IGNORECASE)
_NOT_A_PLACE = _NOT_A_NAME | frozenset(
    "me here home shore shores bank banks bottom surface cover weeds dock docks rocks rock structure dam dams "
    "town spawn spawning dusk dawn night noon sunset sunrise".split()
)


def _named_lakes(question: str) -> list[str]:
    """Names to try, longest first: "Lake Travis crappie" tries that, then
    "Lake Travis"; "good Clear Lake" tries "Clear Lake"."""
    out: list[str] = []
    for chunk in _CHUNK.findall(question):
        tokens = _TOKEN.findall(chunk)
        for i, tok in enumerate(tokens):
            if tok.lower() not in _WATER_WORDS:
                continue
            after: list[str] = []
            for t in tokens[i + 1 : i + 6]:
                if t.lower() in _NAME_GLUE or t.lower() not in _NOT_A_NAME:
                    after.append(t)
                else:
                    break
            for n in range(len(after), 0, -1):
                if after[n - 1].lower() not in _NAME_GLUE:
                    out.append(" ".join([tok, *after[:n]]))
            before: list[str] = []
            for t in reversed(tokens[max(0, i - 4) : i]):
                if t.lower() in _NOT_A_NAME:
                    break
                before.insert(0, t)
            for n in range(len(before)):
                out.append(" ".join([*before[n:], tok]))
    return out[:8]


# A name without the word: "at Toledo Bend", capitalised, verified lakes only.
_BARE_NAME = re.compile(r"\b(?:at|on|in|from)\s+((?:[A-Z][a-z'’]+\s?){1,4})")


def _bare_names(question: str) -> list[str]:
    return [m.group(1).strip() for m in _BARE_NAME.finditer(question)]


def _find_lake(db: Session, question: str, state: str | None) -> list[Waterbody]:
    for name in _named_lakes(question):
        found = lake_search.same_name(db, name, state)
        if found:
            return found
    for name in _bare_names(question):
        if jurisdictions.normalize(name):
            continue
        found = [w for w in lake_search.same_name(db, name, state) if w.data_tier == "verified"]
        if found:
            return found
    return []


def _county(w: Waterbody) -> str | None:
    c = counties.county_at(w.latitude, w.longitude)
    return c.name if c else None


def _shown_name(w: Waterbody) -> str:
    # OpenStreetMap joins a lake's several names with ";".
    return w.name.split(";")[0].strip()


def _fish_out(name: str, confidence: str | None) -> AskLakeFishOut:
    guide = get_guide(name)
    return AskLakeFishOut(name=name, slug=guide.slug if guide else None, confidence=confidence)


_RANK = {"confirmed": 0, "likely": 1, "reported": 2}


def _lake_out(db: Session, wb: Waterbody, asked: tuple[str, ...] = ()) -> AskLakeOut:
    links = sorted(wb.species_links, key=lambda s: (_RANK.get(s.confidence, 3), s.species.common_name))
    species = [_fish_out(s.species.common_name, s.confidence) for s in links]
    on_record = {f.slug for f in species if f.slug}
    reported = reported_species(db, wb.id, confirmed=(s.species.common_name for s in links))
    # Reported only: records of the fish (GBIF, docs/adr/0012), no agency's word.
    named = {s.species.common_name for s in links}
    only_reported = [r.common_name for r in reported if r.common_name not in named and not r.weak]
    also = {g.slug for g in (get_guide(n) for n in only_reported) if g}

    def status(slug: str) -> str:
        return "on_record" if slug in on_record else "reported" if slug in also else "no_record"

    def asked_out(slug: str) -> AskAskedFishOut | None:
        guide = get_guide(slug)
        return AskAskedFishOut(slug=slug, name=guide.common_name, status=status(slug)) if guide else None

    profile = wb.agency_profile
    closed = wb.public_access_status == "closed"
    return AskLakeOut(
        id=wb.id,
        name=_shown_name(wb),
        state_code=wb.state.code,
        county=_county(wb),
        data_tier=wb.data_tier,
        public_access_status=wb.public_access_status,
        species=species,
        reported=only_reported[:12],
        asked=[a for a in map(asked_out, asked) if a],
        access_points=0 if closed else len(wb.access_points),
        fish_attractors=0 if closed else len(wb.fish_attractors),
        agency_url=profile.page_url if profile else None,
        credit=lake_search.AGENCY_CREDITS.get(profile.agency) if profile else None,
    )


_LOADS = (
    selectinload(Waterbody.state),
    selectinload(Waterbody.species_links).selectinload(WaterbodySpecies.species),
    selectinload(Waterbody.access_points),
    selectinload(Waterbody.fish_attractors),
    selectinload(Waterbody.agency_profile),
)


def _load(db: Session, ids: list[int]) -> list[Waterbody]:
    rows = {w.id: w for w in db.scalars(select(Waterbody).where(Waterbody.id.in_(ids)).options(*_LOADS)).all()}
    return [rows[i] for i in ids if i in rows]


def _species_ids(db: Session, slugs: tuple[str, ...]) -> list[int]:
    """The lake data's fish a guide covers: a cutthroat guide is also for the
    Lahontan cutthroat rows, a bullhead guide for all three bullheads."""
    wanted = set(slugs)
    return [
        s.id
        for s in db.scalars(select(Species)).all()
        if (g := get_guide(s.common_name)) is not None and g.slug in wanted
    ]


def _place(question: str, state: str | None) -> tuple[str, geocoding.GeocodeResult] | None:
    m = _NEAR.search(question)
    if not m:
        return None
    words: list[str] = []
    for w in m.group(1).split():
        if w.lower() in _NOT_A_PLACE:
            break
        words.append(w)
    if not words:
        return None
    name = " ".join(words)
    named = jurisdictions.normalize(name)
    if named:  # "near Texas" is just Texas
        return None
    query = f"{name}, {state}" if state else name
    try:
        found = geocoding.geocode(query)
    except geocoding.GeocodingUnavailable:
        return None
    # FishEye's lakes are all in the US, whatever else carries the name.
    if found is None or not (18 <= found.latitude <= 72 and -170 <= found.longitude <= -60):
        return None
    return name, found


def _lakes_for(
    db: Session,
    slugs: tuple[str, ...],
    state: str | None,
    near: geocoding.GeocodeResult | None,
) -> list[Waterbody]:
    stmt = select(Waterbody).join(Waterbody.state).where(Waterbody.public_access_status != "closed")
    if slugs:
        ids = _species_ids(db, slugs)
        if not ids:
            return []
        stmt = stmt.join(Waterbody.species_links).where(WaterbodySpecies.species_id.in_(ids))
    elif near is None:
        return []
    else:
        stmt = stmt.where(Waterbody.species_links.any())
    if near is not None:
        stmt = stmt.where(radius_filter(db, near.latitude, near.longitude, NEAR_RADIUS_KM))
    elif state:
        stmt = stmt.where(Waterbody.state.has(code=state))
    rows = db.scalars(stmt.options(selectinload(Waterbody.state)).order_by((Waterbody.extent_km2 + 0).desc()).limit(400)).unique().all()
    if near is not None:
        rows = [w for w in rows if haversine_km(near.latitude, near.longitude, w.latitude, w.longitude) <= NEAR_RADIUS_KM]
    # Verified lakes first, then the biggest: the water most people can reach.
    rows = sorted(rows, key=lambda w: (w.data_tier != "verified", -w.extent_km2))
    return _load(db, [w.id for w in rows[:MAX_LAKES]])


_NEARBY_EN = re.compile(r"\b(near me|nearby|close to me|around me|around here|near my (?:house|home))\b", re.I)
_WATER_EN = re.compile(r"\b(fish|fishing|lakes?|ponds?|rivers?|spots?)\b", re.I)
_WHERE_EN = re.compile(r"\b(where|any|best|good|find|places?|spots?)\b", re.I)


def asks_where_nearby(question: str) -> bool:
    """"Where can I fish near me": only the map knows where the person is."""
    if any(w in question for w in ("附近", "周围", "周边")):
        return any(w in question for w in ("哪", "有没有", "什么地方", "推荐")) and any(
            w in question for w in ("钓", "鱼", "湖", "水库", "河")
        )
    return bool(_NEARBY_EN.search(question) and _WATER_EN.search(question) and _WHERE_EN.search(question))


def missing_lake(question: str, routed: tuple[str, ...]) -> str | None:
    """The name, when the question asks what's in a lake `answer` didn't find."""
    if routed or not _ASKS_WHATS_THERE.search(question):
        return None
    names = _named_lakes(question)
    return names[0] if names else None


def answer(db: Session, question: str, picked_state: str | None, routed: tuple[str, ...]) -> AskLakesOut | None:
    """What the lake data says to this question, if it says anything."""
    state = jurisdictions.state_in_question(question) or jurisdictions.normalize(picked_state)
    found = _find_lake(db, question, state)
    if found:
        lake, *same = found
        full = _load(db, [lake.id])
        return AskLakesOut(
            kind="lake",
            lakes=[_lake_out(db, full[0], routed)],
            same_name=[
                AskLakeOut(
                    id=w.id, name=_shown_name(w), state_code=w.state.code, county=_county(w), data_tier=w.data_tier,
                    public_access_status=w.public_access_status,
                )
                for w in same[:4]
            ],
            answers_it=not routed and bool(_ASKS_WHATS_THERE.search(question)),
        )
    if not _ASKS_WHERE.search(question):
        return None
    place = _place(question, state)
    if place is None and not (routed and state):
        return None
    near = place[1] if place else None
    lakes = _lakes_for(db, routed, state, near)
    return AskLakesOut(
        kind="list",
        place=place[0] if place else None,
        state=None if place else state,
        fish=[g.common_name for g in (get_guide(s) for s in routed) if g],
        fish_slugs=list(routed),
        lakes=[_lake_out(db, w, routed) for w in lakes],
    )
