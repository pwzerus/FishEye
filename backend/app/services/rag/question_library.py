"""The question library as Ask's second tier (docs/adr/0051).

The library is not added to the guides' index. Its 494 question-shaped
passages would shift every BM25 average and crowd the reviewed cards out of
the top results, so it has an index of its own, and the guides' retrieval and
eval numbers stay exactly as they were.

What it adds to an answer:
- nothing, when the best match is a state's rule, or when nothing in the
  library clearly matches what was asked;
- the closest question, when the guides found nothing (a fish with no guide,
  a reel problem, a buying question);
- the closest question beside the guides' cards, when it asks nearly the
  same thing as the user did: first if the guides' best card doesn't plainly
  answer, second if it does.

"Clearly matches" is measured on the question itself. A share of the asker's
words, weighted by how rare they are, must appear in it, so a word the
library has never seen ("guitar") counts against a match, and to be shown
beside the guides it must also be mostly about those words. A Chinese question
is also compared with the library's Chinese wording, character pair by pair.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.angling_qa import CATEGORIES, ITEMS, QaItem
from app.services.rag import zh
from app.services.rag.chunking import SHARED_SLUG, Passage
from app.services.rag.embeddings import Embedder, passage_vectors
from app.services.rag.retriever import (
    BM25Retriever,
    ScoredPassage,
    expand_query,
    is_on_topic,
    names_unguided_fish,
    tokenize,
    tokenize_query,
)

RRF_K = 60
DENSE_TOP = 8
DENSE_W = 0.5
CANDIDATES = 12  # fused results looked at for a clear match
# Shares of the asker's (rarity-weighted) words.
STRONG_SHARE = 0.68  # in the question: shown beside the guides' cards
# And the library's question must be mostly about those words too. "Why does
# braid of the same pound test have a much thinner diameter" holds every word
# of "what pound test", but it asks something else.
BOTH_WAYS = 0.33
GUIDE_ANSWERS = 0.5  # in the title of the guides' best card: it stays first
USABLE_SHARE = 0.65  # in the question or short answer: only when the guides have nothing
STRONG_ZH = 0.62  # character-pair overlap with the Chinese question
USABLE_ZH = 0.45
RARE_IDF = 3.5  # a word in about 3% of the library's answers or fewer
MAX_WHEN_ALONE = 2


def qa_passage(item: QaItem) -> Passage:
    return Passage(
        id=f"{SHARED_SLUG}#{item.id}",
        species_slug=SHARED_SLUG,
        species_name="",
        section=item.id,
        title=item.question,
        text=f"{item.question} ({CATEGORIES[item.category]['en']}): {item.short} {item.body}",
        source_ids=item.source_ids,
        title_zh=item.question_zh,
        text_zh=f"{item.short_zh}{item.body_zh}",
        basis=item.basis,
    )


def _pairs(text: str) -> set[str]:
    chars = [c for c in text if "一" <= c <= "鿿"]
    return {a + b for a, b in zip(chars, chars[1:])}


def _dice(a: set[str], b: set[str]) -> float:
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


@dataclass(frozen=True)
class Found:
    passage: Passage
    score: float
    strong: bool


class QuestionLibrary:
    def __init__(self, embedder: Embedder | None = None) -> None:
        self.passages = [qa_passage(i) for i in ITEMS]
        self.bm25 = BM25Retriever(self.passages)
        self._index = {p.id: n for n, p in enumerate(self.passages)}
        self._question = [set(tokenize(i.question)) for i in ITEMS]
        self._short = [set(tokenize(i.short)) for i in ITEMS]
        self._zh_pairs = [_pairs(i.question_zh) for i in ITEMS]
        self._max_idf = max(self.bm25._idf.values())
        self.embedder = embedder
        # The question and its short answer: what a query should be close to.
        self._vecs = (
            passage_vectors(embedder, [f"{i.question} {i.short}" for i in ITEMS]) if embedder is not None else None
        )

    def _share(self, asked: set[str], have: set[str]) -> float:
        weight = lambda t: self.bm25._idf.get(t, self._max_idf)  # noqa: E731
        total = sum(weight(t) for t in asked)
        return sum(weight(t) for t in asked & have) / total if total else 0.0

    def _rare(self, token: str) -> bool:
        return self.bm25._idf.get(token, 0.0) >= RARE_IDF

    def _ranked(self, query: str) -> list[tuple[int, float]]:
        tokens = tokenize_query(zh.with_english(query))
        lexical = self.bm25._rank(expand_query(tokens), None) if tokens else []
        fused: dict[int, float] = {}
        for rank, h in enumerate(lexical):
            n = self._index[h.passage.id]
            fused[n] = fused.get(n, 0.0) + 1 / (RRF_K + rank + 1)
        if self._vecs is not None:
            qvec = self.embedder.encode([zh.with_english(query)], kind="query")[0]
            sims = qvec @ self._vecs.T
            for rank, n in enumerate(sims.argsort()[::-1][:DENSE_TOP]):
                fused[int(n)] = fused.get(int(n), 0.0) + DENSE_W / (RRF_K + rank + 1)
        if zh.has_chinese(query):
            # The glossary reaches only part of a Chinese question; its
            # character pairs reach the library's Chinese wording directly.
            pairs = _pairs(query)
            close = sorted(range(len(ITEMS)), key=lambda n: -_dice(pairs, self._zh_pairs[n]))[:DENSE_TOP]
            for rank, n in enumerate(close):
                fused[n] = fused.get(n, 0.0) + 1 / (RRF_K + rank + 1)
        return sorted(fused.items(), key=lambda kv: (-kv[1], self.passages[kv[0]].id))

    def guides_answer(self, hit: ScoredPassage, query: str) -> bool:
        """Does the guides' best card plainly answer? Its fish and title say
        what it is about; a card that shares one word with the question doesn't."""
        asked = set(tokenize_query(zh.with_english(query)))
        title = set(tokenize(f"{hit.passage.species_name} {hit.passage.title}"))
        return self._share(asked, title) >= GUIDE_ANSWERS

    def search(self, query: str) -> list[Found]:
        """Clear matches, best first; empty when nothing clearly matches."""
        asked = set(tokenize_query(zh.with_english(query)))
        chinese = zh.has_chinese(query)
        if not asked and not chinese:
            return []
        pairs = _pairs(query) if chinese else set()
        # One word is a match only if the question is about fishing and the
        # word is a rare one ("backlash", not "bait"). A fish with no guide,
        # named in Chinese, isn't in the glossary, so only the wording can match.
        one_word = len(asked) == 1 and is_on_topic(query) and self._rare(next(iter(asked)))
        words_count = not (chinese and names_unguided_fish(query))
        out: list[Found] = []
        for n, score in self._ranked(query)[:CANDIDATES]:
            words = self._question[n]
            matched = asked & words
            in_question = self._share(asked, words)
            anywhere = self._share(asked, words | self._short[n])
            several = words_count and len(matched) >= 2
            similar = _dice(pairs, self._zh_pairs[n])
            both = self._share(asked | words, asked & words)
            strong = (several and in_question >= STRONG_SHARE and both >= BOTH_WAYS) or similar >= STRONG_ZH
            usable = strong or (several and anywhere >= USABLE_SHARE) or (one_word and bool(matched)) or similar >= USABLE_ZH
            if usable:
                out.append(Found(self.passages[n], score, strong))
        return sorted(out, key=lambda f: (not f.strong, -f.score))


_libraries: dict[int, QuestionLibrary] = {}


def library(embedder: Embedder | None = None) -> QuestionLibrary:
    """Built once per process and embedder; the library changes only with a deploy."""
    key = id(embedder)
    if key not in _libraries:
        _libraries[key] = QuestionLibrary(embedder)
    return _libraries[key]


def merge(hits: list[ScoredPassage], query: str, k: int, retriever: object) -> list[ScoredPassage]:
    """The guides' hits with the library's added, as the module docstring says."""
    if hits and hits[0].passage.section.startswith(("rule-", "bait_rules")):
        return hits
    lib = library(getattr(retriever, "embedder", None))
    found = lib.search(query)
    if not found:
        return hits
    if not hits:
        return [ScoredPassage(f.passage, f.score) for f in found[:MAX_WHEN_ALONE]]
    if not found[0].strong:
        return hits
    # One card more than usual, so no guide card is pushed out by it.
    card = ScoredPassage(found[0].passage, hits[0].score)
    return [hits[0], card, *hits[1:]] if lib.guides_answer(hits[0], query) else [card, *hits]
