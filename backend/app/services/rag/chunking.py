"""Turn app/knowledge/species_guides.py into retrievable passages.

One passage per *semantic unit* of a guide — the diet, the live-bait list,
one tackle setup — rather than fixed-size windows of text. The guides are
already structured that way, and a passage that is exactly "the minnow
under a bobber setup for crappie" is both the right thing to retrieve and
the right thing to cite: the user can follow the citation to one card on
the guide page, not to "somewhere around here".

Every passage's text starts with a short header naming the species and
the section ("Largemouth Bass — Live bait: ..."). Retrieval scores the
header along with the body, so a question about "crappie bait" can match a
passage whose body only says "minnows" — the words that locate a passage
are in the passage. It also means a passage quoted on its own, out of
context, still says which fish it's about.

Tackle-setup passages cite exactly that setup's sources. Every other
passage cites the guide's full source list, because that's the precision
the reviewed content actually has: the guides record sources per setup and
per species, not per sentence, and inventing finer attribution than the
source material supports would be its own kind of fabrication.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.species_guides import BAIT_RULES, GUIDES, SpeciesGuide

SHARED_SLUG = "all-fish"  # passages that apply to every species


@dataclass(frozen=True)
class Passage:
    id: str  # "<species-slug>#<section>", stable across restarts
    species_slug: str
    species_name: str  # "" for shared passages
    section: str  # machine name: "diet", "live_baits", "setup-2", ...
    title: str  # human name: "Live bait", "Setup: Minnow under a bobber"
    text: str  # header + body; what gets retrieved and what the model reads
    source_ids: tuple[str, ...]


def _bullets(items: tuple[str, ...]) -> str:
    return " ".join(item if item.endswith((".", "!", "?")) else f"{item}." for item in items)


def _passage(
    guide: SpeciesGuide, section: str, title: str, body: str, source_ids: tuple[str, ...]
) -> Passage:
    return Passage(
        id=f"{guide.slug}#{section}",
        species_slug=guide.slug,
        species_name=guide.common_name,
        section=section,
        title=title,
        text=f"{guide.common_name} — {title}: {body}",
        source_ids=source_ids,
    )


def passages_for(guide: SpeciesGuide) -> list[Passage]:
    src = guide.source_ids
    out: list[Passage] = []

    kind = "bait fish" if guide.role == "forage" else f"{guide.difficulty or ''} sport fish"
    out.append(
        _passage(
            guide,
            "overview",
            "Overview",
            f"{guide.summary} ({guide.scientific_name}; {kind.strip()}.)",
            src,
        )
    )
    out.append(_passage(guide, "diet", "What it eats", guide.diet, src))
    if guide.identification:
        out.append(
            _passage(guide, "identification", "How to recognise it", _bullets(guide.identification), src)
        )
    if guide.where_and_when:
        out.append(
            _passage(guide, "where_and_when", "Where and when to find it", _bullets(guide.where_and_when), src)
        )
    if guide.live_baits:
        out.append(_passage(guide, "live_baits", "Live and natural bait", _bullets(guide.live_baits), src))
    if guide.lures:
        out.append(_passage(guide, "lures", "Lures", _bullets(guide.lures), src))
    for i, setup in enumerate(guide.setups, start=1):
        body = (
            f"{setup.use_when} Rod: {setup.rod}. Reel: {setup.reel}. Line: {setup.line}. "
            f"Hook and rig: {setup.terminal}"
        )
        out.append(
            _passage(guide, f"setup-{i}", f"Rod and reel setup — {setup.name}", body, setup.source_ids)
        )
    if guide.how_to_get:
        out.append(_passage(guide, "how_to_get", "How to get it for bait", _bullets(guide.how_to_get), src))
    if guide.bait_for:
        out.append(_passage(guide, "bait_for", "Use it as bait for", _bullets(guide.bait_for), src))
    if guide.tips:
        out.append(_passage(guide, "tips", "Tips", _bullets(guide.tips), src))
    return out


def shared_passages() -> list[Passage]:
    """Content that several guides repeat verbatim (the bait rules) is
    indexed once. Indexed per species, the same three sentences would fill
    every slot of a "can I use live bait" answer with duplicates."""
    return [
        Passage(
            id=f"{SHARED_SLUG}#bait_rules",
            species_slug=SHARED_SLUG,
            species_name="",
            section="bait_rules",
            title="Texas bait rules",
            text="Texas bait rules (all fish): " + " ".join(BAIT_RULES),
            source_ids=("tpwd-regs-general",),
        )
    ]


def build_passages(guides: tuple[SpeciesGuide, ...] = GUIDES) -> list[Passage]:
    passages = [p for g in guides for p in passages_for(g)]
    passages.extend(shared_passages())
    ids = [p.id for p in passages]
    if len(ids) != len(set(ids)):
        # A duplicate id would make citations ambiguous; fail at import,
        # not in front of a user.
        raise ValueError("duplicate passage ids in the guide index")
    return passages
