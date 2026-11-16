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

from app.knowledge.angling_handbook import CATEGORIES, TOPICS, HandbookTopic
from app.knowledge.species_guides import GUIDES, SpeciesGuide
from app.knowledge.translations import OTHER_LANGUAGES, table

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
    # A state code for a passage that states that state's rules, else "all"
    # (knowledge/jurisdictions.py, docs/adr/0027).
    region: str = "all"
    # The Chinese version where there is one (knowledge/translations/,
    # knowledge/angling_qa.py): the answer alone, no header.
    title_zh: str = ""
    text_zh: str = ""
    basis: str = ""  # "guide", "official", "maker" or "general"; "" for the guides
    # Spanish, Japanese and Korean, as (lang, text) pairs, built from the same
    # kind of tables (added 2026-11-16, ADR 0058).
    title_tr: tuple[tuple[str, str], ...] = ()
    text_tr: tuple[tuple[str, str], ...] = ()

    def text_in(self, lang: str | None) -> str:
        """The passage in `lang` without its header, or "" if not translated."""
        if lang == "zh":
            return self.text_zh
        return dict(self.text_tr).get(lang or "", "")

    def title_in(self, lang: str | None) -> str:
        if lang == "zh":
            return self.title_zh
        return dict(self.title_tr).get(lang or "", "")


def _bullets(items: tuple[str, ...]) -> str:
    return " ".join(item if item.endswith((".", "!", "?")) else f"{item}." for item in items)


def _zh_sentences(parts: list[str | None]) -> str:
    """Chinese sentences run together, or "" if any isn't translated."""
    if not parts or not all(parts):
        return ""
    return "".join(p if p.endswith(("。", "！", "？")) else f"{p}。" for p in parts)


def _zh_guide(guide: SpeciesGuide, field: str, items: tuple[str, ...] | None = None) -> str:
    """A guide field in Chinese: one string, or its list of bullets (`items`)."""
    words = table("guides", "zh")
    if items is None:
        return words.get(f"{guide.slug}.{field}", "")
    return _zh_sentences([words.get(f"{guide.slug}.{field}#{i}") for i in range(len(items))])


def _zh_setup(guide: SpeciesGuide, index: int) -> tuple[str, str]:
    """A setup's name and body in Chinese, or two empty strings."""
    words = table("guides", "zh")
    key = f"{guide.slug}.setups#{index}"
    parts = {f: words.get(f"{key}.{f}") for f in ("name", "use_when", "rod", "reel", "line", "terminal")}
    if not all(parts.values()):
        return "", ""
    body = _zh_sentences([parts["use_when"], f"竿：{parts['rod']}", f"轮：{parts['reel']}", f"线：{parts['line']}",
                          f"钩和钓组：{parts['terminal']}"])
    return parts["name"] or "", body


def join_sentences(parts: list[str | None], lang: str) -> str:
    """Sentences run together in `lang`, or "" if any isn't translated:
    Chinese and Japanese end each with 。 and need no space, Spanish and
    Korean end with a full stop and a space."""
    if not parts or not all(parts):
        return ""
    if lang in ("zh", "ja"):
        return "".join(p if p.endswith(("。", "！", "？")) else f"{p}。" for p in parts)
    return " ".join(p if p.endswith((".", "!", "?", "…")) else f"{p}." for p in parts)


# The labels a setup's body uses in each language, as its card on the page.
_SETUP_LABELS = {
    "es": ("Caña: ", "Carrete: ", "Línea: ", "Anzuelo y aparejo: "),
    "ja": ("竿：", "リール：", "ライン：", "針と仕掛け："),
    "ko": ("낚싯대: ", "릴: ", "낚싯줄: ", "바늘과 채비: "),
}
_SINGLE_FIELDS = {"overview": "summary", "diet": "diet"}


def _tr_guide(guide: SpeciesGuide, section: str) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    """A guide section in Spanish, Japanese and Korean: (texts, titles) as
    (lang, text) pairs. A language missing any sentence of it is left out,
    so the passage stays English there rather than half translated."""
    texts: list[tuple[str, str]] = []
    titles: list[tuple[str, str]] = []
    for lang in OTHER_LANGUAGES:
        words = table("guides", lang)
        if section.startswith("setup-"):
            key = f"{guide.slug}.setups#{int(section.removeprefix('setup-')) - 1}"
            parts = {f: words.get(f"{key}.{f}") for f in ("name", "use_when", "rod", "reel", "line", "terminal")}
            if not all(parts.values()):
                continue
            rod, reel, line, rig = _SETUP_LABELS[lang]
            body = join_sentences([parts["use_when"], f"{rod}{parts['rod']}", f"{reel}{parts['reel']}",
                                   f"{line}{parts['line']}", f"{rig}{parts['terminal']}"], lang)
            texts.append((lang, body))
            titles.append((lang, f"Rod and reel setup — {parts['name']}"))
        elif section in _SINGLE_FIELDS:
            text = words.get(f"{guide.slug}.{_SINGLE_FIELDS[section]}")
            if text:
                texts.append((lang, text))
        else:
            items = getattr(guide, section, ()) or ()
            text = join_sentences([words.get(f"{guide.slug}.{section}#{i}") for i in range(len(items))], lang)
            if text:
                texts.append((lang, text))
    return tuple(texts), tuple(titles)


# A state's bait-rules passage title, as the rules card on the page says it.
_BAIT_TITLE = {
    "es": lambda state: f"Reglas de carnada de {state}",
    "ja": lambda state: f"{state}のエサの規則",
    "ko": lambda state: f"{state} 미끼 규정",
}


def _tr_sentences(name: str, prefix: str, count: int) -> tuple[tuple[str, str], ...]:
    """`count` sentences of table `name` under `prefix` ("bait-worms#"), in
    each other language that has all of them."""
    out = []
    for lang in OTHER_LANGUAGES:
        words = table(name, lang)
        text = join_sentences([words.get(f"{prefix}{i}") for i in range(count)], lang)
        if text:
            out.append((lang, text))
    return tuple(out)


def _passage(
    guide: SpeciesGuide, section: str, title: str, body: str, source_ids: tuple[str, ...],
    text_zh: str = "", title_zh: str = "",
) -> Passage:
    text_tr, title_tr = _tr_guide(guide, section)
    return Passage(
        id=f"{guide.slug}#{section}",
        species_slug=guide.slug,
        species_name=guide.common_name,
        section=section,
        title=title,
        text=f"{guide.common_name} — {title}: {body}",
        source_ids=source_ids,
        title_zh=title_zh,
        text_zh=text_zh,
        title_tr=title_tr,
        text_tr=text_tr,
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
            text_zh=_zh_guide(guide, "summary"),
        )
    )
    out.append(_passage(guide, "diet", "What it eats", guide.diet, src, text_zh=_zh_guide(guide, "diet")))
    if guide.identification:
        out.append(
            _passage(guide, "identification", "How to recognise it", _bullets(guide.identification), src,
                     text_zh=_zh_guide(guide, "identification", guide.identification))
        )
    if guide.habitat:
        out.append(_passage(guide, "habitat", "Habitat: where it lives", _bullets(guide.habitat), src,
                            text_zh=_zh_guide(guide, "habitat", guide.habitat)))
    if guide.habits:
        out.append(
            _passage(guide, "habits", "Habits: behavior, spawning and growth", _bullets(guide.habits), src,
                     text_zh=_zh_guide(guide, "habits", guide.habits))
        )
    if guide.where_and_when:
        out.append(
            _passage(guide, "where_and_when", "Where and when to find it", _bullets(guide.where_and_when), src,
                     text_zh=_zh_guide(guide, "where_and_when", guide.where_and_when))
        )
    if guide.live_baits:
        out.append(_passage(guide, "live_baits", "Live and natural bait", _bullets(guide.live_baits), src,
                            text_zh=_zh_guide(guide, "live_baits", guide.live_baits)))
    if guide.lures:
        out.append(_passage(guide, "lures", "Lures", _bullets(guide.lures), src,
                            text_zh=_zh_guide(guide, "lures", guide.lures)))
    if guide.why_these_baits:
        out.append(
            _passage(guide, "why_these_baits", "Why these baits work", _bullets(guide.why_these_baits), src,
                     text_zh=_zh_guide(guide, "why_these_baits", guide.why_these_baits))
        )
    for i, setup in enumerate(guide.setups, start=1):
        body = (
            f"{setup.use_when} Rod: {setup.rod}. Reel: {setup.reel}. Line: {setup.line}. "
            f"Hook and rig: {setup.terminal}"
        )
        name_zh, body_zh = _zh_setup(guide, i - 1)
        out.append(
            _passage(guide, f"setup-{i}", f"Rod and reel setup — {setup.name}", body, setup.source_ids,
                     text_zh=body_zh, title_zh=f"Rod and reel setup — {name_zh}" if name_zh else "")
        )
    if guide.how_to_get:
        out.append(_passage(guide, "how_to_get", "How to get it for bait", _bullets(guide.how_to_get), src,
                            text_zh=_zh_guide(guide, "how_to_get", guide.how_to_get)))
    if guide.bait_for:
        out.append(_passage(guide, "bait_for", "Use it as bait for", _bullets(guide.bait_for), src,
                            text_zh=_zh_guide(guide, "bait_for", guide.bait_for)))
    if guide.tips:
        out.append(_passage(guide, "tips", "Tips", _bullets(guide.tips), src,
                            text_zh=_zh_guide(guide, "tips", guide.tips)))
    if guide.eating:
        out.append(_passage(guide, "eating", "On the table: cleaning and cooking it", _bullets(guide.eating), src,
                            text_zh=_zh_guide(guide, "eating", guide.eating)))
    return out


def handbook_passage(topic: HandbookTopic) -> Passage:
    """One per handbook topic (app/knowledge/angling_handbook.py). Shared,
    like the bait rules: a topic is about fishing in general, so it may
    answer a question about any fish, and fills slots a routed question's
    own fish left empty (retriever._interleave)."""
    return Passage(
        id=f"{SHARED_SLUG}#{topic.id}",
        species_slug=SHARED_SLUG,
        species_name="",
        section=topic.id,
        title=topic.title,
        text=f"{topic.title} ({CATEGORIES[topic.category]}): {' '.join(topic.body)}",
        source_ids=topic.source_ids,
        region=topic.region,
        text_zh=_zh_sentences([table("handbook", "zh").get(f"{topic.id}#{i}") for i in range(len(topic.body))]),
        text_tr=_tr_sentences("handbook", f"{topic.id}#", len(topic.body)),
    )


def shared_passages() -> list[Passage]:
    """Content that several guides repeat verbatim (the bait rules) is
    indexed once. Indexed per species, the same three sentences would fill
    every slot of a "can I use live bait" answer with duplicates.

    Bait rules are a state's (knowledge/jurisdictions.py, docs/adr/0027):
    one passage per state FishEye has written rules for, tagged with it."""
    from app.knowledge import jurisdictions  # imports species_guides; kept local
    from app.services.rag.replies import _state_name as state_name

    bait = [
        Passage(
            id=f"{SHARED_SLUG}#{jurisdictions.bait_rules_section(j.code)}",
            species_slug=SHARED_SLUG,
            species_name="",
            section=jurisdictions.bait_rules_section(j.code),
            title=f"{j.name} bait rules",
            text=f"{j.name} bait rules (all fish): " + " ".join(j.bait_rules),
            source_ids=j.bait_rules_source_ids,
            region=j.code,
            title_zh=f"{jurisdictions.ZH_STATE_NAMES.get(j.code, j.name)}的饵料规定",
            text_zh=_zh_sentences([table("bait_rules", "zh").get(f"{j.code}#{i}") for i in range(len(j.bait_rules))]),
            title_tr=tuple((lang, _BAIT_TITLE[lang](state_name(j.code, lang))) for lang in OTHER_LANGUAGES),
            text_tr=_tr_sentences("bait_rules", f"{j.code}#", len(j.bait_rules)),
        )
        for j in jurisdictions.covered()
        if j.bait_rules
    ]
    return bait + [handbook_passage(t) for t in TOPICS]


def build_passages(guides: tuple[SpeciesGuide, ...] = GUIDES) -> list[Passage]:
    passages = [p for g in guides for p in passages_for(g)]
    passages.extend(shared_passages())
    ids = [p.id for p in passages]
    if len(ids) != len(set(ids)):
        # A duplicate id would make citations ambiguous; fail at import,
        # not in front of a user.
        raise ValueError("duplicate passage ids in the guide index")
    return passages
