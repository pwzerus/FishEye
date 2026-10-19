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

import numpy as np

from app.services.rag import zh
from app.services.rag.chunking import SHARED_SLUG
from app.services.rag.embeddings import Embedder, passage_vectors
from app.services.rag.retriever import (
    AMBIGUOUS_ALIASES,
    AmbiguousName,
    BM25Retriever,
    ScoredPassage,
    arrange_routed,
    explain_empty,
    is_howto,
    is_on_topic,
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


class HybridRetriever:
    name = "hybrid"

    def __init__(self, bm25: BM25Retriever, embedder: Embedder, vectors: np.ndarray | None = None) -> None:
        self.bm25 = bm25
        self.passages = bm25.passages
        self.embedder = embedder
        self._vecs = vectors if vectors is not None else passage_vectors(embedder, [p.text for p in self.passages])
        self._slugs = np.array([p.species_slug for p in self.passages])
        self._index = {p.id: i for i, p in enumerate(self.passages)}
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
        return explain_empty(question, self.resolve(question)[0], species)

    def _qvec(self, question: str) -> np.ndarray:
        return self.embedder.encode([question], kind="query")[0]

    def search(self, question: str, k: int = 4, species: tuple[str, ...] | None = None) -> list[ScoredPassage]:
        qvec = self._qvec(question)
        sims = qvec @ self._vecs.T
        named, residual = self._resolve(question, qvec)
        routed = named or species or ()
        if routed:
            if is_howto(residual if named else question):
                return self.bm25.howto(routed[0], k)
        elif names_unguided_fish(question) or not is_on_topic(question):
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
            return self.bm25.howto(routed[0], k)
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
        hits = [ScoredPassage(self.passages[i], s) for i, s in fused.items()]
        hits.sort(key=lambda h: (-h.score, h.passage.id))
        if routed:
            return arrange_routed(hits, query, k)
        return hits[:k]
