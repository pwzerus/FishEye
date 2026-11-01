"""Baits and lures as linked terms: tap one in an answer to see what it is,
why a fish takes it, and which fish it catches.

Nothing here is new writing. Each term is a handbook topic (its card text:
what it is, why it works, how to hook it) and the fish whose guides list it
among their baits or lures, each with the guide's own sentence on why that
fish takes it (`why_these_baits`). The words a term is recognised by are
per language: the guides and handbook are in English, AI summaries in the
reader's language. Order matters where one name holds another: "plastic
worm" is a soft plastic, not a worm; "wax worm" a grub.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.knowledge.angling_handbook import TOPICS
from app.knowledge.species_guides import GUIDES


@dataclass(frozen=True)
class BaitTerm:
    id: str
    topic: str  # its handbook topic, which is its card
    # The words it is recognised by in text, per language. English ones are
    # matched as whole words, singular or plural as listed.
    names: dict[str, tuple[str, ...]] = field(default_factory=dict)


TERMS: tuple[BaitTerm, ...] = (
    BaitTerm("soft-plastics", "lure-soft-plastics", {
        "en": ("plastic worm", "plastic worms", "soft plastic", "soft plastics", "soft-plastic", "soft-plastics"),
        "zh": ("软饵", "软虫"), "es": ("gusano de plástico", "gusanos de plástico"),
        "ko": ("소프트베이트", "웜"), "ja": ("ワーム", "ソフトルアー"),
    }),
    BaitTerm("grubs", "bait-grubs", {
        "en": ("mealworm", "mealworms", "wax worm", "wax worms", "waxworm", "waxworms"),
        "zh": ("面包虫", "蜡虫"), "es": ("gusano de harina", "gusanos de harina"),
        "ko": ("밀웜",), "ja": ("ミルワーム",),
    }),
    BaitTerm("worms", "bait-worms", {
        "en": ("worm", "worms", "nightcrawler", "nightcrawlers", "redworm", "redworms", "earthworm", "earthworms"),
        "zh": ("蚯蚓",), "es": ("lombriz", "lombrices"), "ko": ("지렁이",), "ja": ("ミミズ",),
    }),
    BaitTerm("minnows", "bait-minnows", {
        "en": ("minnow", "minnows", "shiner", "shiners"),
        "zh": ("活小鱼", "小活鱼"), "es": ("pececillo", "pececillos"), "ko": ("피라미",), "ja": ("小魚",),
    }),
    BaitTerm("insects", "bait-insects", {
        "en": ("cricket", "crickets", "grasshopper", "grasshoppers"),
        "zh": ("蟋蟀", "蚱蜢"), "es": ("grillo", "grillos", "saltamontes"),
        "ko": ("귀뚜라미", "메뚜기"), "ja": ("コオロギ", "バッタ"),
    }),
    BaitTerm("crayfish", "bait-crayfish", {
        "en": ("crayfish", "crawfish", "crawdad", "crawdads"),
        "zh": ("小龙虾",), "es": ("acocil", "acociles", "cangrejo de río"), "ko": ("가재",), "ja": ("ザリガニ",),
    }),
    BaitTerm("cut-bait", "bait-shad-cut", {
        "en": ("cut bait", "shad"),
        "zh": ("切块饵",), "es": ("carnada cortada",), "ko": ("토막 미끼",), "ja": ("切り身",),
    }),
    BaitTerm("liver", "bait-liver-soft", {
        "en": ("chicken liver", "chicken livers", "hot dog", "hot dogs"),
        "zh": ("鸡肝",), "es": ("hígado de pollo",), "ko": ("닭 간",), "ja": ("鶏レバー",),
    }),
    BaitTerm("stink-bait", "bait-stink", {
        "en": ("stink bait", "stink baits", "punch bait", "dip bait"),
        "zh": ("臭饵",), "es": ("carnada apestosa",), "ko": ("냄새 미끼",), "ja": ("臭いエサ",),
    }),
    BaitTerm("dough", "bait-dough-corn", {
        "en": ("dough bait", "dough baits", "PowerBait", "corn"),
        "zh": ("面饵", "玉米"), "es": ("masa", "maíz"), "ko": ("떡밥", "옥수수"), "ja": ("練りエサ", "トウモロコシ"),
    }),
    BaitTerm("shrimp", "bait-shrimp", {
        "en": ("shrimp",), "zh": ("虾",), "es": ("camarón", "camarones"), "ko": ("새우",), "ja": ("エビ",),
    }),
    BaitTerm("crankbaits", "lure-crankbaits", {
        "en": ("crankbait", "crankbaits"), "zh": ("曲柄饵",), "es": ("crankbait", "crankbaits"),
        "ko": ("크랭크베이트",), "ja": ("クランクベイト",),
    }),
    BaitTerm("spinnerbaits", "lure-spinnerbaits", {
        "en": ("spinnerbait", "spinnerbaits", "spinner", "spinners"), "zh": ("复合亮片",),
        "es": ("spinnerbait", "spinnerbaits"), "ko": ("스피너베이트",), "ja": ("スピナーベイト",),
    }),
    BaitTerm("jigs", "rig-jigs", {
        "en": ("jig", "jigs", "jighead", "jigheads"), "zh": ("铅头钩",), "es": ("jig", "jigs"),
        "ko": ("지그",), "ja": ("ジグ",),
    }),
    BaitTerm("spoons", "lure-spoons", {
        "en": ("spoon", "spoons"), "zh": ("勺型亮片",), "es": ("cucharilla", "cucharillas"),
        "ko": ("스푼",), "ja": ("スプーン",),
    }),
    BaitTerm("topwater", "lure-topwater", {
        "en": ("topwater", "topwaters", "popper", "poppers", "buzzbait", "buzzbaits"), "zh": ("水面系",),
        "es": ("señuelo de superficie", "señuelos de superficie"), "ko": ("탑워터",), "ja": ("トップウォーター",),
    }),
)

_TOPICS = {t.id: t for t in TOPICS}
# Shad baits aren't a "bait" on a shad's own page; the term is skipped there.
SKIP_ON = {"cut-bait": ("gizzard-shad", "threadfin-shad")}


def _english_re(term: BaitTerm) -> re.Pattern[str]:
    names = sorted(term.names["en"], key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(n) for n in names) + r")\b", re.I)


def _covered_by_longer(text: str, term: BaitTerm) -> str:
    """`text` without the names of the terms listed before `term` (the
    longer ones): "plastic worm" mustn't count as a worm."""
    for other in TERMS:
        if other is term:
            break
        text = _english_re(other).sub(" ", text)
    return text


def _sentence(topic_id: str, *starts: str) -> str | None:
    for s in _TOPICS[topic_id].body:
        if s.startswith(starts):
            return s
    return None


@dataclass(frozen=True)
class FishLink:
    slug: str
    name: str
    why: str | None  # the guide's sentence on why this fish takes it


def fish_for(term: BaitTerm) -> list[FishLink]:
    """The guide fish whose baits or lures include `term`, best reason first."""
    pattern = _english_re(term)
    out: list[FishLink] = []
    for g in GUIDES:
        if g.role != "sport" or g.slug in SKIP_ON.get(term.id, ()):
            continue
        listed = " ".join((*g.live_baits, *g.lures, *(s.terminal for s in g.setups)))
        if not pattern.search(_covered_by_longer(listed, term)):
            continue
        why = next((w for w in g.why_these_baits if pattern.search(_covered_by_longer(w, term))), None)
        out.append(FishLink(g.slug, g.common_name, why))
    return out


def card(term: BaitTerm) -> dict:
    topic = _TOPICS[term.topic]
    return {
        "id": term.id,
        "topic": topic.id,
        "title": topic.title,
        "what": topic.body[0],
        "why": _sentence(topic.id, "Why"),
        "how": _sentence(topic.id, "How to", "Fish them", "When"),
        "names": {lang: list(names) for lang, names in term.names.items()},
        "skip_on": list(SKIP_ON.get(term.id, ())),
        "fish": [{"slug": f.slug, "name": f.name, "why": f.why} for f in fish_for(term)],
        "source_ids": list(topic.source_ids),
    }


def all_cards() -> list[dict]:
    return [card(t) for t in TERMS]
