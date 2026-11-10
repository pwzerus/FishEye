"""Matching a Chinese question to the handbook's Chinese topics (docs/adr/0052).

A Chinese question otherwise reaches the English passages only through the
glossary and the embedding model, so a word nobody put in the glossary (中暑,
旧鱼线, 浑水) found nothing or the wrong thing. The handbook has a Chinese title
and text for every topic (knowledge/translations/), and a topic's title is
close to how people ask: "中暑" against "中暑：痉挛、热衰竭和热射病".

BM25 over overlapping pairs of characters (Chinese has no spaces, and a pair
is the usual stand-in for a word without a dictionary), with a title's pairs
counted several times. The guides stay out: every fish's section repeats the
same few words ("竿", "轮", "磅"), and ranked here they crowded out the topic
that answers. Measured on Chinese questions the tuning never saw (the ADR).
"""
from __future__ import annotations

import math
import re
from collections import Counter

from app.knowledge.translations import table
from app.services.rag.chunking import SHARED_SLUG, Passage

_RUNS = re.compile(r"[㐀-鿿]+|[a-z0-9]+")
K1 = 1.2
B = 0.75
TITLE_TIMES = 4
TOP = 6
# Question words: in almost every question, and in many a topic ("怎么组").
_WEAK = frozenset(
    {"怎么", "么办", "什么", "么时", "时候", "为什", "如何", "怎样", "可以", "能不", "不能", "需要", "应该", "一下", "钓鱼", "了怎", "的时"}
)


def tokens(text: str) -> list[str]:
    out: list[str] = []
    for run in _RUNS.findall(text.lower()):
        if run.isascii():
            out.append(run)
        elif len(run) > 1:
            out.extend(run[i : i + 2] for i in range(len(run) - 1))
    return out


class ZhTopics:
    def __init__(self, passages: list[Passage]) -> None:
        titles = table("topic_titles", "zh")
        self._docs: dict[int, Counter[str]] = {}
        for i, p in enumerate(passages):
            if p.species_slug != SHARED_SLUG or not p.text_zh or p.region != "all":
                continue
            doc = Counter(tokens(p.text_zh))
            for t in tokens(titles.get(p.section, "")):
                doc[t] += TITLE_TIMES
            self._docs[i] = doc
        self._avg = sum(sum(d.values()) for d in self._docs.values()) / max(1, len(self._docs))
        df: Counter[str] = Counter()
        for d in self._docs.values():
            df.update(d.keys())
        n = len(self._docs)
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def _scored(self, question: str) -> list[tuple[float, int]]:
        terms = [t for t in dict.fromkeys(tokens(question)) if t in self._idf and t not in _WEAK]
        if not terms:
            return []
        out: list[tuple[float, int]] = []
        for i, doc in self._docs.items():
            norm = K1 * (1 - B + B * sum(doc.values()) / self._avg)
            score = sum(self._idf[t] * doc[t] * (K1 + 1) / (doc[t] + norm) for t in terms if t in doc)
            if score > 0:
                out.append((score, i))
        out.sort(key=lambda s: (-s[0], s[1]))
        return out[:TOP]

    def rank(self, question: str) -> list[int]:
        """Indexes of the passages of the topics closest to the question, best first."""
        return [i for _, i in self._scored(question)]
