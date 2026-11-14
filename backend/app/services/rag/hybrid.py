"""Keyword + semantic retrieval, fused (docs/adr/0025).

BM25 (retriever.py) is precise on the guides' own vocabulary — "slip
bobber", "palomar", a fish's name — and blind to everything else: a
paraphrase that shares no word with the passage, or a question in Chinese.
The embedding model (embeddings.py) covers exactly that gap and is weaker
at what BM25 does well, so neither replaces the other. Each ranks the
passages separately and the two rankings are merged by reciprocal rank
fusion: a passage's score is the sum of 1 / (RRF_K + rank) over the lists it
appears in. Rank-based, so BM25 scores and cosines never have to be put on
one scale.

What stays rule-based, because a rule is checkable and a similarity is not:
- species routing, now with Chinese names too (retriever.split_species);
- fish with no guide get "not covered" (retriever.names_unguided_fish);
- the shared-passage ordering (retriever.arrange_routed).

The on-topic gate gains one way in: a question the keyword gate turns away
is still searched when its best cosine to any passage clears GATE_COSINE.
That is what lets "怎么杀鱼" through, which has no English word to match.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

import numpy as np

from app.knowledge.translations import table
from app.services.rag import zh
from app.services.rag.chunking import SHARED_SLUG
from app.services.rag.embeddings import MODEL_DIR, Embedder, passage_vectors
from app.services.rag.zh_search import ZhTopics, asks
from app.services.rag.retriever import (
    AMBIGUOUS_ALIASES,
    EMPTY_OFF_TOPIC,
    AmbiguousName,
    BM25Retriever,
    ScoredPassage,
    arrange_routed,
    explain_empty,
    is_howto,
    is_on_topic,
    topic_fish_passages,
    names_unguided_fish,
    query_terms,
    resolve_species,
    wants_howto,
)

RRF_K = 60
# How many of the closest passages (by cosine, within the fish the question
# routed to) the semantic side contributes. Ranks only: the model's
# cosines are compressed (0.73 between a bass question and a bread recipe)
# and can't separate fishing from off-topic questions, so no decision here
# rests on a cosine threshold (ADR 0025 has the measurements).
DENSE_TOP = 5
DENSE_W = 0.5
# A Chinese question's closest handbook topics (zh_search.py), per place in that list.
ZH_TOPIC_W = 0.5
# A topic whose ways of asking the question is close to (zh_search.ZhAsks), times
# how close. Above the three lists together, because a question that is how
# people ask about a topic is about that topic.
ZH_ASK_W = 4.0
# The closest way of asking by meaning (WaysOfAsking), for a question put in
# other words than any of them. Its weight rises from nothing at NEAR_FLOOR to
# all of it at NEAR_FLOOR + NEAR_SPAN: a nearest way that is only as close as
# unrelated questions get says nothing.
ZH_NEAR_W = 2.5
NEAR_FLOOR = 0.90
NEAR_SPAN = 0.06
# Only the topics about as close as the closest: the third nearest is usually
# just the next most similar sentence shape.
NEAR_TIE = 0.012
# A fish named and nothing else the keyword side can read ("钓鳟鱼用什么线"): the
# how-to for that fish, under the topic the question is about, if one is this close.
ROUTED_NEAR_FIRST = 0.94
# With a fish named, a topic goes first only when the question is nearly how
# people ask about it: "大嘴鲈和小嘴鲈怎么分" is the look-alike card, but "白鲈什么
# 季节最好钓" is that fish's own section, not the card about seasons.
ROUTED_ASK_FIRST = 0.75


# Words that can be about fishing. A question with none of them isn't let in by
# being close to a way of asking: "下雨天开车要注意什么" is near "下雨天能钓鱼吗".
_CAN_BE_FISHING = (
    *"鱼线竿钩饵漂铅轮抛口鲈鲶鳟鲤救虫绑证湖河船晒",
    "水里", "水草", "水位", "水库", "水温", "水面", "水色", "水深", "落水", "掉水", "浑水", "清水",
)


class WaysOfAsking:
    """Chinese questions compared by meaning with how people ask about each topic.

    The same list as zh_search.ZhAsks, which only sees shared characters.
    Here "鱼太大拉不动怎么办" is near "怎么把鱼拉上来", and "钩子怎么从鱼嘴里拿出来"
    near "鱼吞钩了怎么取". This model's cosines can't say by themselves whether a
    question is about fishing (ADR 0025), but which of two lists a question is
    closer to they can: the ways of asking, or questions about anything else
    (translations/zh_not_fishing.json). The same comparison as the "bass" decoys.
    """

    def __init__(self, embedder: Embedder, cache: bool = True) -> None:
        ways = cast("dict[str, list[str]]", table("topic_asks", "zh"))
        others = cast("list[str]", table("not_fishing", "zh"))
        library = json.loads((KNOWLEDGE / "qa_library.json").read_text(encoding="utf-8"))
        self._topics = [topic for topic, phrases in ways.items() for _ in phrases]
        cache_dir = MODEL_DIR if cache else None
        self._ways = passage_vectors(embedder, [p for phrases in ways.values() for p in phrases], cache_dir, "query")
        self._others = passage_vectors(embedder, others, cache_dir, "query")
        asked = [item["question_zh"] for item in library["items"] if item.get("question_zh")]
        self._library = passage_vectors(embedder, asked, cache_dir, "query")

    def nearest(self, qvec: np.ndarray, top: int = 3) -> list[tuple[str, float]]:
        sims = self._ways @ qvec
        found: dict[str, float] = {}
        for i in np.argsort(-sims):
            found.setdefault(self._topics[int(i)], float(sims[i]))
            if len(found) == top:
                break
        return list(found.items())

    def is_fishing(self, question: str, qvec: np.ndarray) -> bool:
        text = zh.without_other_meanings(question)
        if not any(c in text for c in _CAN_BE_FISHING):
            return False
        return float((self._ways @ qvec).max()) > float((self._others @ qvec).max())

    def means_fishing(self, qvec: np.ndarray) -> bool:
        """A question that has 钓鱼 in it: about fishing, or about dating, a
        dream, a game or baiting someone? The fishing side is the ways of
        asking and the question library's Chinese questions; the closer
        side wins, and a tie counts as fishing."""
        fishing = max(float((self._ways @ qvec).max()), float((self._library @ qvec).max()))
        return fishing >= float((self._others @ qvec).max())


KNOWLEDGE = Path(__file__).resolve().parents[2] / "knowledge"
# Tackle and bait that only anglers talk about: a question naming one is about
# fishing whatever else it says (HybridRetriever._not_about_fishing).
_GEAR_WORD = re.compile(
    r"\b(rods?|reels?|lures?|baits?|tackle|gear|equipment|bobbers?|hooks?|jigs?|sinkers?|swivels?|"
    r"leaders?|braid|fluoro(carbon)?|mono(filament)?|spinnerbaits?|crankbaits?|jerkbaits?|soft ?plastics?|"
    r"rigs?|fish ?finders?|fishing line|nightcrawlers?|minnows?|waders?|spools?|drag|licen[cs]e)\b",
    re.I,
)
# The same in Chinese: every fishing word the keyword gate knows except 钓
# itself, which 钓鱼执法, 钓凯子 and a date who loves fishing share.
_ZH_TACKLE = tuple(term for term in zh.FISHING_TERMS if term != "钓")


class EnglishGate:
    """Is an English question that uses a fishing word about fishing?

    The keyword gate (retriever.is_on_topic) lets in any question with
    "fish" or "fishing" in it, so "how to find a girl who loves fishing"
    brought back the trolling guide (the product owner, 2026-11-13). Here
    the question is compared by meaning with what FishEye covers (every
    guide passage, and the question library's questions) and with
    questions about something else that use the same words: dating, scams
    ("phishing"), video games, aquariums, idioms
    (knowledge/not_fishing_en.json). The closer side wins, as with the
    "bass" decoys: this model's cosines can't say by themselves whether a
    question is about fishing (ADR 0025), but which of two things it is
    closer to they can. Everything is encoded as a passage, so both sides
    are measured the same way. A tie counts as fishing."""

    def __init__(self, embedder: Embedder, passages: np.ndarray, cache: bool = True) -> None:
        library = json.loads((KNOWLEDGE / "qa_library.json").read_text(encoding="utf-8"))
        others = json.loads((KNOWLEDGE / "not_fishing_en.json").read_text(encoding="utf-8"))
        cache_dir = MODEL_DIR if cache else None
        questions = passage_vectors(embedder, [item["question"] for item in library["items"]], cache_dir, "passage")
        self._ways = np.vstack([passages, questions])
        self._others = passage_vectors(embedder, others, cache_dir, "passage")

    def is_fishing(self, qvec: np.ndarray) -> bool:
        return float((self._ways @ qvec).max()) >= float((self._others @ qvec).max())


class HybridRetriever:
    name = "hybrid"

    def __init__(
        self,
        bm25: BM25Retriever,
        embedder: Embedder,
        vectors: np.ndarray | None = None,
        ways: WaysOfAsking | None = None,
        en_gate: EnglishGate | None = None,
    ) -> None:
        self.bm25 = bm25
        self.passages = bm25.passages
        self.embedder = embedder
        self._vecs = vectors if vectors is not None else passage_vectors(embedder, [p.text for p in self.passages])
        self._slugs = np.array([p.species_slug for p in self.passages])
        self._index = {p.id: i for i, p in enumerate(self.passages)}
        self._zh = ZhTopics(self.passages)
        self._topic = {p.section: i for i, p in enumerate(self.passages) if p.species_slug == SHARED_SLUG and p.region == "all"}
        # A licence card is per state; this index holds the asker's, or all of them.
        for i, p in enumerate(self.passages):
            if p.section.startswith("rule-license"):
                self._topic.setdefault("rule-license", i)
        self.ways = ways if ways is not None else WaysOfAsking(embedder, cache=vectors is None)
        self.en_gate = en_gate if en_gate is not None else EnglishGate(embedder, self._vecs, cache=vectors is None)
        # One vector per decoy sentence, for the ambiguous names
        # (retriever.AmbiguousName). About 30 short sentences, encoded once.
        decoys = [(alias, d) for alias, n in AMBIGUOUS_ALIASES.items() for d in n.decoys]
        self._decoy_of = [alias for alias, _ in decoys]
        self._decoy_vecs = embedder.encode([d for _, d in decoys], kind="passage")

    def _about_the_fish_sims(self, sims: np.ndarray, qvec: np.ndarray, alias: str, name: AmbiguousName) -> bool:
        """Is "bass" here a fish or a guitar? The question is compared with
        the fish's own passages and with that name's decoy sentences, and
        the closer side wins.

        A comparison, not a threshold: this model's cosines sit in a narrow
        band and no cut-off separates fishing from everything else (ADR
        0025), but which of two things a question is closer to is exactly
        what an embedding can answer."""
        fish = float(sims[np.isin(self._slugs, list(name.slugs))].max())
        mine = [i for i, a in enumerate(self._decoy_of) if a == alias]
        decoy = float((self._decoy_vecs[mine] @ qvec).max()) if mine else 0.0
        return fish >= decoy

    def resolve(self, question: str) -> tuple[tuple[str, ...], str]:
        return self._resolve(question, self._qvec(question))

    def _resolve(self, question: str, qvec: np.ndarray) -> tuple[tuple[str, ...], str]:
        sims = qvec @ self._vecs.T
        return resolve_species(question, lambda q, alias, name: self._about_the_fish_sims(sims, qvec, alias, name))

    def why_empty(self, question: str, species: tuple[str, ...] | None = None) -> str:
        qvec = self._qvec(question)
        named = self._resolve(question, qvec)[0]
        if self._not_about_fishing(question, qvec, named or species):
            return EMPTY_OFF_TOPIC
        return explain_empty(question, named, species)

    def _not_about_fishing(
        self, question: str, qvec: np.ndarray, routed: tuple[str, ...] | None, zh_vec: np.ndarray | None = None
    ) -> bool:
        """A question that names no fish and passed the keyword gate on a
        fishing word, but means something else: EnglishGate in English, and
        in Chinese the ways of asking against questions about other things
        (WaysOfAsking.means_fishing). One that names a piece of tackle is
        taken as fishing: "Best Fish Finder" and "Rocket Fishing rod?" were
        turned away on 2026-11-13's check against real beginners' questions,
        while "fish" and "fishing" (钓鱼) alone are the words dating,
        aquarium and video game questions share."""
        if routed:
            return False
        if zh.has_chinese(question):
            text = zh.without_other_meanings(question)
            if any(term in text for term in _ZH_TACKLE):
                return False
            if zh_vec is None:
                zh_vec = self.embedder.encode([question.lower()], kind="query")[0]
            return not self.ways.means_fishing(zh_vec)
        if _GEAR_WORD.search(question):
            return False
        return not self.en_gate.is_fishing(qvec)

    def _qvec(self, question: str) -> np.ndarray:
        # A Chinese question with the glossary's English added, as the
        # keyword side reads it: "鱼线怎么绑到渔轮上" alone is closest to the
        # reel passages, not the arbor knot. On the eval (2026-10-30) this
        # took Chinese hit@4 from 96% to 100% and moved nothing else.
        return self.embedder.encode([zh.with_english(question)], kind="query")[0]

    def _under_nearest_topic(self, hits: list[ScoredPassage], zh_vec: np.ndarray | None, k: int) -> list[ScoredPassage]:
        if zh_vec is None:
            return hits
        topic, sim = self.ways.nearest(zh_vec, top=1)[0]
        i = self._topic.get(topic)
        if i is None or sim < ROUTED_NEAR_FIRST:
            return hits
        first = ScoredPassage(self.passages[i], sim)
        return [first, *(h for h in hits if h.passage is not first.passage)][:k]

    def search(self, question: str, k: int = 4, species: tuple[str, ...] | None = None) -> list[ScoredPassage]:
        qvec = self._qvec(question)
        sims = qvec @ self._vecs.T
        named, residual = self._resolve(question, qvec)
        routed = named or species or ()
        # The question as asked, for comparing Chinese with Chinese.
        zh_vec = self.embedder.encode([question.lower()], kind="query")[0] if zh.has_chinese(question) else None
        topics = topic_fish_passages(question)
        if topics:
            # Fish the handbook covers but no guide does (salmon, steelhead,
            # lake trout…): the keyword side's routing to their topics.
            return self.bm25.search(question, k, species)
        if routed:
            if is_howto(residual if named else question):
                return self.bm25.howto(routed[0], k)
        elif names_unguided_fish(question):
            return []
        elif not is_on_topic(question) and not (zh_vec is not None and self.ways.is_fishing(question.lower(), zh_vec)):
            return []
        elif self._not_about_fishing(question, qvec, routed, zh_vec):
            return []

        query = query_terms(question, residual, named)
        chinese = zh.has_chinese(residual if named else question)
        if named and not query and not chinese:
            # Only a fish's name ("tell me about bluegill"): nothing to rank
            # on, so the beginner's sections in order.
            return self.bm25._by_section(routed, k)

        allowed = set(routed) | {SHARED_SLUG} if routed else None
        lexical = self.bm25._rank(query, allowed) if query else []
        if not lexical and routed and wants_howto(residual if named else question):
            return self._under_nearest_topic(self.bm25.howto(routed[0], k), zh_vec, k)
        if not lexical and not chinese:
            # An English question keyword search finds nothing for is "not
            # covered", as before: the model would always find *something*.
            return []

        mask = np.isin(self._slugs, list(allowed)) if allowed else np.ones(len(self.passages), dtype=bool)
        dense = [int(i) for i in np.argsort(-sims) if mask[i]][:DENSE_TOP]

        fused: dict[int, float] = {}
        for rank, h in enumerate(lexical):
            i = self._index[h.passage.id]
            fused[i] = fused.get(i, 0.0) + 1 / (RRF_K + rank + 1)
        for rank, i in enumerate(dense):
            fused[i] = fused.get(i, 0.0) + DENSE_W / (RRF_K + rank + 1)
        asked = asks().best(question) if chinese else []
        if chinese:
            for rank, i in enumerate(self._zh.rank(residual if named else question)):
                fused[i] = fused.get(i, 0.0) + ZH_TOPIC_W / (RRF_K + rank + 1)
            for rank, match in enumerate(asked):
                if (i := self._topic.get(match.topic)) is not None:
                    fused[i] = fused.get(i, 0.0) + ZH_ASK_W * match.closeness / (RRF_K + rank + 1)
            if zh_vec is not None and not routed:
                near = self.ways.nearest(zh_vec)
                for rank, (topic, sim) in enumerate(near):
                    if sim >= near[0][1] - NEAR_TIE and (i := self._topic.get(topic)) is not None:
                        weight = ZH_NEAR_W * min(1.0, max(0.0, (sim - NEAR_FLOOR) / NEAR_SPAN))
                        fused[i] = fused.get(i, 0.0) + weight / (RRF_K + rank + 1)
        hits = [ScoredPassage(self.passages[i], s) for i, s in fused.items()]
        hits.sort(key=lambda h: (-h.score, h.passage.id))
        if not routed:
            return hits[:k]
        arranged = arrange_routed(hits, query, k)
        if asked and asked[0].closeness >= ROUTED_ASK_FIRST and (i := self._topic.get(asked[0].topic)) is not None:
            first = next(h for h in hits if h.passage is self.passages[i])
            return [first, *(h for h in arranged if h is not first)][:k]
        return arranged
