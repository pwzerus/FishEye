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
from dataclasses import dataclass
from functools import lru_cache
from typing import cast

from app.knowledge.translations import table
from app.services.rag import zh
from app.services.rag.chunking import SHARED_SLUG, Passage

_RUNS = re.compile(r"[㐀-鿿]+|[a-z0-9]+")
K1 = 1.2
B = 0.75
TITLE_TIMES = 4
TOP = 6
# How close a question has to be to one way of asking (ZhAsks) to count.
ASK_MIN = 0.45
ASK_ON_TOPIC = 0.6
ASK_TOP = 3
# Words that say nothing about what is asked; left out before comparing.
_FILLER = re.compile("请问|一下|的|了|吗|呢|啊|呀|吧|哦|嘛")
_FISHING_THINGS = "鱼线竿钩饵漂铅轮抛口鲈鲶鳟鲤救虫绑证"
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


@dataclass(frozen=True)
class AskMatch:
    topic: str
    closeness: float  # 0 to 1; 1: the question is one of the topic's ways of asking


class ZhAsks:
    """Which handbook topic a Chinese question is, by how people ask about each.

    A topic's title and text are written Chinese. People ask "一直没口怎么办" and
    "线用几号的", which share nothing with "一直没口？该改什么" but a pair or two,
    and nothing at all with the glossary. So each topic has the ways people ask
    about it, written by hand from the topic (translations/zh_topic_asks.json).
    A question is compared with every one of them, as the cosine of their pairs
    of characters weighted by how rare each pair is among all the ways of asking.
    """

    def __init__(self, asks: dict[str, list[str]]) -> None:
        phrases = [(topic, self._terms(p)) for topic, ways in asks.items() for p in ways]
        df = Counter(t for _, terms in phrases for t in terms)
        self._idf = {t: math.log(1 + len(phrases) / c) for t, c in df.items()}
        self._rarest = math.log(1 + len(phrases))
        self._phrases = [(topic, terms, self._norm(terms)) for topic, terms in phrases if terms]

    @staticmethod
    def _terms(text: str) -> list[str]:
        return [t for t in dict.fromkeys(tokens(_FILLER.sub("", text))) if t not in _WEAK]

    def _weight(self, term: str) -> float:
        return self._idf.get(term, self._rarest)

    def _norm(self, terms: list[str]) -> float:
        return math.sqrt(sum(self._weight(t) ** 2 for t in terms))

    def best(self, question: str) -> list[AskMatch]:
        """The topics this question is closest to, closest first, up to ASK_TOP."""
        terms = self._terms(question)
        if not terms:
            return []
        norm = self._norm(terms)
        wanted = set(terms)
        closest: dict[str, float] = {}
        for topic, way, way_norm in self._phrases:
            shared = sum(self._weight(t) ** 2 for t in way if t in wanted)
            if shared:
                closest[topic] = max(closest.get(topic, 0.0), shared / (norm * way_norm))
        found = sorted(closest.items(), key=lambda kv: (-kv[1], kv[0]))
        return [AskMatch(topic, c) for topic, c in found[:ASK_TOP] if c >= ASK_MIN]


@lru_cache(maxsize=1)
def asks() -> ZhAsks:
    return ZhAsks(cast("dict[str, list[str]]", table("topic_asks", "zh")))


def is_asked_about(question: str) -> bool:
    """Close enough to how people ask about a topic to be a fishing question.
    Closeness alone isn't enough: "夏天穿什么衣服" is as close to "钓鱼穿什么" as
    many real questions are to theirs. It has to name something a question
    about fishing names as well, once words like 电线 are out of the way."""
    text = zh.without_other_meanings(question)
    if not any(c in text for c in _FISHING_THINGS):
        return False
    found = asks().best(text)
    return bool(found) and found[0].closeness >= ASK_ON_TOPIC
