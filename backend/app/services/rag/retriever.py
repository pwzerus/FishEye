"""Rank guide passages for a question.

Why BM25 and not embeddings (the long version is ADR 0014)
-----------------------------------------------------------
The corpus is ~110 short passages of reviewed text with a small, very
specific vocabulary — species names, "jig", "slip bobber", "cast net". That
is the case lexical ranking is good at, and the retrieval eval
(app/eval/rag_cases.py) measures it rather than assuming it. Embeddings
would need either a model download or a vendor key and network access on
every machine the demo runs on, which buys a dependency before there's a
measured miss to justify it. The `Retriever` protocol is the seam an
embedding or hybrid retriever plugs into once the eval shows lexical
matching falling short.

Two things are added on top of plain BM25, both small and both visible:

1. **Species routing.** A question that names a fish ("crappie", or the
   Texas nickname "sand bass") only searches that fish's passages plus the
   shared ones. Without this, "what bait for crappie" ranks the *catfish*
   bait list well too — both are bait lists — and the answer would quote
   the wrong fish. Nicknames are listed explicitly in SPECIES_ALIASES.
2. **A short synonym list** for the words beginners use that the guides
   don't ("gear" for rod/reel, "feed on" for eats). It's a list, not a
   model, so it can be read in full and tested.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from app.services.rag.chunking import SHARED_SLUG, Passage, build_passages

# BM25 defaults from the literature; the eval did not show a reason to tune them.
K1 = 1.2
B = 0.75

STOPWORDS = frozenset(
    """a an and are as at be but by can do does for from go good how i if in
    into is it its me my of on or should so some that the their them then there
    these they this to use using up was we what which who why will with you
    your best catch fish fishing texas about me know info information more
    anything""".split()
)
# "tell me about X" asks for an overview; a bare "tell" ("tell them apart")
# asks how to recognise a fish. The phrase is removed before tokenising so
# the two don't collide.
_QUERY_NOISE_RE = re.compile(r"\btell me\b")
# "fish", "catch", "fishing", "texas", "best" appear in nearly every question
# and carry no signal about which passage answers it. They are still matched
# inside passages through species names like "catfish" and "bait fish".

# Words beginners use -> words the guides use. Applied to the query only.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "feed": ("eat",),
    "food": ("eat",),
    "diet": ("eat",),
    "gear": ("rod", "reel", "setup"),
    "tackle": ("rod", "reel", "setup"),
    "equipment": ("rod", "reel", "setup"),
    "pole": ("rod",),
    "rig": ("hook", "rig"),
    "tie": ("hook", "rig"),
    "artificial": ("lure",),
    "lure": ("lure", "jig"),
    "where": ("where", "find"),
    "spot": ("where", "find"),
    "locate": ("where", "find"),
    "season": ("when", "spring", "summer", "fall", "winter"),
    "time": ("when",),
    "month": ("when",),
    "legal": ("legal", "unlawful", "rule"),
    "law": ("legal", "unlawful", "rule"),
    "allowed": ("legal", "unlawful", "rule"),
    "illegal": ("legal", "unlawful", "rule"),
    "regulation": ("legal", "unlawful", "rule"),
    "identify": ("recognise",),
    "recognize": ("recognise",),
    "apart": ("recognise",),
    "difference": ("recognise",),
    "easy": ("beginner",),
    "easiest": ("beginner",),
    "easier": ("beginner",),
    "kid": ("beginner",),
    "net": ("net", "cast"),
    "tell": ("recognise",),
    "deep": ("deep", "ft"),  # depths in the guides are written "5 ft", "10 ft deep"
    "depth": ("deep", "ft"),
    "shallow": ("deep", "ft"),
}

# A question that names no fish must use at least one fishing word to be
# searched at all. Without this gate, "recommend a good pizza place" matches
# "the easiest place to start" and gets a confident answer about catfish.
DOMAIN_TERMS = frozenset(
    """bait lure hook rod reel line setup bobber float slip jig rig sinker weight
    leader swivel net cast worm minnow shad cricket nightcrawler liver shrimp
    lake pond river reservoir creek dock brush cover deep ft depth shallow spawn
    spawning school legal rule unlawful regulation eat recognise beginner where
    when spring summer fall winter topwater crankbait spinner spinnerbait grub
    slab troll drift boat bank shore panfish gamefish game""".split()
)

# Phrase -> species slugs. Longest phrases are matched first and consumed,
# so "white crappie" never also counts as a bare "crappie".
SPECIES_ALIASES: dict[str, tuple[str, ...]] = {
    "largemouth bass": ("largemouth-bass",),
    "largemouth": ("largemouth-bass",),
    "bigmouth": ("largemouth-bass",),
    "spotted bass": ("spotted-bass",),
    "kentucky bass": ("spotted-bass",),
    "white bass": ("white-bass",),
    "sand bass": ("white-bass",),
    "sandbass": ("white-bass",),
    "sandies": ("white-bass",),
    "hybrid striped bass": ("hybrid-striped-bass",),
    "hybrid striper": ("hybrid-striped-bass",),
    "hybrids": ("hybrid-striped-bass",),
    "hybrid": ("hybrid-striped-bass",),
    "wipers": ("hybrid-striped-bass",),
    "wiper": ("hybrid-striped-bass",),
    "striped bass": ("striped-bass",),
    "stripers": ("striped-bass",),
    "striper": ("striped-bass",),
    "channel catfish": ("channel-catfish",),
    "channel cats": ("channel-catfish",),
    "channel cat": ("channel-catfish",),
    "blue catfish": ("blue-catfish",),
    "blue cats": ("blue-catfish",),
    "blue cat": ("blue-catfish",),
    "catfish": ("channel-catfish", "blue-catfish"),
    "white crappie": ("white-crappie",),
    "black crappie": ("black-crappie",),
    "crappies": ("white-crappie", "black-crappie"),
    "crappie": ("white-crappie", "black-crappie"),
    "sac-a-lait": ("white-crappie", "black-crappie"),
    "papermouth": ("white-crappie", "black-crappie"),
    "bluegills": ("bluegill",),
    "bluegill": ("bluegill",),
    "bream": ("bluegill",),
    "brim": ("bluegill",),
    "sunfish": ("bluegill",),
    "perch": ("bluegill",),
    "gizzard shad": ("gizzard-shad",),
    "threadfin shad": ("threadfin-shad",),
    "threadfin": ("threadfin-shad",),
    "yellowtails": ("threadfin-shad",),
    "shad": ("gizzard-shad", "threadfin-shad"),
}
_ALIAS_PATTERNS = [
    (re.compile(rf"\b{re.escape(alias)}\b"), slugs)
    for alias, slugs in sorted(SPECIES_ALIASES.items(), key=lambda kv: -len(kv[0]))
]

_TOKEN_RE = re.compile(r"[a-z]+|\d+(?:/\d+)?")


def stem(word: str) -> str:
    """A deliberately light stemmer: plurals and -ing. The corpus is small
    and hand-written, so a full Porter stemmer's over-merging ("bass" ->
    "bas", "lure" -> "lur") costs more than it finds."""
    if len(word) <= 3 or word.endswith(("ss", "us")):
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-1]  # crappies -> crappie, fries -> frie (harmless)
    if word.endswith(("shes", "ches", "xes")):
        return word[:-2]  # inches -> inch
    if word.endswith("ing") and len(word) > 5:
        root = word[:-3]
        if len(root) > 2 and root[-1] == root[-2] and root[-1] not in "ls":
            root = root[:-1]  # jigging -> jig
        return root
    if word.endswith("s"):
        return word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def tokenize_query(text: str) -> list[str]:
    return tokenize(_QUERY_NOISE_RE.sub(" ", text.lower()))


def is_on_topic(tokens: list[str]) -> bool:
    return any(t in DOMAIN_TERMS or t in SYNONYMS for t in tokens)


def expand_query(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        out.append(t)
        out.extend(SYNONYMS.get(t, ()))
    return out


def split_species(question: str) -> tuple[tuple[str, ...], str]:
    """(species slugs named in the question, the question with those names
    removed). Slugs are ordered longest-alias-first, which puts a specific
    name ("white crappie") ahead of a family one ("crappie")."""
    text = question.lower()
    found: list[str] = []
    for pattern, slugs in _ALIAS_PATTERNS:
        if pattern.search(text):
            for slug in slugs:
                if slug not in found:
                    found.append(slug)
            text = pattern.sub(" ", text)
    return tuple(found), text


def detect_species(question: str) -> tuple[str, ...]:
    return split_species(question)[0]


# Order used when a question names a fish and nothing else ("tell me about
# bluegill"): there are no words left to rank on, so show the passages a
# beginner needs first.
SECTION_ORDER = (
    "overview",
    "diet",
    "where_and_when",
    "live_baits",
    "lures",
    "setup",
    "identification",
    "how_to_get",
    "bait_for",
    "tips",
    "bait_rules",
)


def _section_rank(p: Passage) -> int:
    base = p.section.split("-")[0]
    return SECTION_ORDER.index(base) if base in SECTION_ORDER else len(SECTION_ORDER)


def _interleave(hits: list[ScoredPassage], k: int) -> list[ScoredPassage]:
    """Round-robin across species, strongest species first.

    "What gear for catfish" is about two fish; plain top-k hands all four
    slots to whichever one's passages happen to score a little higher, and
    the answer silently covers only blue catfish. Hits must already be
    sorted best-first."""
    groups: dict[str, list[ScoredPassage]] = {}
    for h in hits:
        groups.setdefault(h.passage.species_slug, []).append(h)
    # dict order = order of each group's best hit. The shared bait rules
    # only fill slots the fish themselves left empty, so they never displace
    # the fish the question was about.
    shared = groups.pop(SHARED_SLUG, [])
    queues = list(groups.values())
    out: list[ScoredPassage] = []
    while len(out) < k and any(queues):
        for q in queues:
            if q and len(out) < k:
                out.append(q.pop(0))
    return out + shared[: k - len(out)]


@dataclass(frozen=True)
class ScoredPassage:
    passage: Passage
    score: float


class Retriever(Protocol):
    def search(
        self, question: str, k: int = 4, species: tuple[str, ...] | None = None
    ) -> list[ScoredPassage]: ...


class BM25Retriever:
    def __init__(self, passages: list[Passage]) -> None:
        self.passages = passages
        self._docs = [Counter(tokenize(p.text)) for p in passages]
        self._lengths = [sum(d.values()) for d in self._docs]
        self._avg_len = sum(self._lengths) / len(self._lengths)
        df: Counter[str] = Counter()
        for d in self._docs:
            df.update(d.keys())
        n = len(passages)
        # BM25+ style idf floor at 0: a term in most passages adds nothing,
        # rather than a negative amount.
        self._idf = {t: max(0.0, math.log((n - f + 0.5) / (f + 0.5) + 1)) for t, f in df.items()}

    def _score(self, i: int, query: list[str]) -> float:
        doc, length = self._docs[i], self._lengths[i]
        score = 0.0
        for term in query:
            tf = doc.get(term, 0)
            if tf == 0:
                continue
            denom = tf + K1 * (1 - B + B * length / self._avg_len)
            score += self._idf.get(term, 0.0) * tf * (K1 + 1) / denom
        return score

    def search(
        self, question: str, k: int = 4, species: tuple[str, ...] | None = None
    ) -> list[ScoredPassage]:
        """Top-k passages, best first; empty means "the guides don't cover this".

        Routing: fish named in the question win; otherwise `species` (the
        page the question was asked from) is used. Once the search is
        limited to those fish, their names are dropped from the query —
        every routed passage is about that fish already, so the name only
        rewards passages that happen to repeat it.

        Once routed, the search never widens. A question that names a fish
        but matches none of that fish's passages gets an empty result (the
        "not covered" answer), not the best matches from other fish.
        Widening used to be the fallback, and it answered "how do I tell
        white bass from hybrid striped bass" — which no guide covers — with
        the threadfin shad bait list, because that passage happens to say
        "striped bass and hybrid striped bass". Retrieval only reaches this
        point when a name *was* recognised, so there is no misread nickname
        to recover from; an unrecognised name never routes and is searched
        across the whole index below.
        """
        named, residual = split_species(question)
        routed = named or species or ()

        if routed:
            allowed = set(routed) | {SHARED_SLUG}
            query = expand_query(tokenize_query(residual if named else question))
            if not query:
                return self._by_section(routed, k)
            hits = self._rank(query, allowed)
            return _interleave(hits, k) if hits else []

        tokens = tokenize_query(question)
        if not is_on_topic(tokens):
            return []
        query = expand_query(tokens)
        return self._rank(query, None)[:k] if query else []

    def _rank(self, query: list[str], allow: set[str] | None) -> list[ScoredPassage]:
        hits = [
            ScoredPassage(p, self._score(i, query))
            for i, p in enumerate(self.passages)
            if allow is None or p.species_slug in allow
        ]
        hits = [h for h in hits if h.score > 0]
        # Stable tiebreak on id keeps results (and the eval) deterministic.
        hits.sort(key=lambda h: (-h.score, h.passage.id))
        return hits

    def _by_section(self, species: tuple[str, ...], k: int) -> list[ScoredPassage]:
        """Score 0.0 on purpose: these are ordered by SECTION_ORDER, not by
        any text match, and a trace reader should be able to tell."""
        chosen = [p for p in self.passages if p.species_slug in species]
        chosen.sort(key=lambda p: (_section_rank(p), species.index(p.species_slug), p.id))
        return _interleave([ScoredPassage(p, 0.0) for p in chosen], k)


_default: BM25Retriever | None = None


def default_retriever() -> BM25Retriever:
    """The guide index, built once per process — the guides only change
    with a deploy, so there is nothing to invalidate."""
    global _default
    if _default is None:
        _default = BM25Retriever(build_passages())
    return _default
