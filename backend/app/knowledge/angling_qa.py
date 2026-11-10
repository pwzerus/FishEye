"""The question library: short answers to what anglers actually ask.

494 questions, each with an English and a Chinese answer, in qa_library.json
and qa_sources.json (generated; docs/adr/0051). The guides and the handbook
remain the reviewed reference. This library covers what they leave out, mostly
gear choice, reel trouble and first-trip questions, and Ask reaches it second
(services/rag/question_library.py).

`basis` says what an answer rests on, and the page shows it:
- "guide": FishEye's own guides and handbook;
- "official": a state or federal agency, or a fisheries education booklet;
- "maker": a tackle maker's own page;
- "general": general fishing knowledge, not checked against a published source.

Facts and methods only, in our own words. A forum answer is never a source.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.knowledge.species_guides import SOURCES, Source

_HERE = Path(__file__).resolve().parent
BASES = ("guide", "official", "maker", "general")


@dataclass(frozen=True)
class QaItem:
    id: str  # "qa-...": anchor on /questions and passage section
    category: str
    question: str
    question_zh: str
    short: str  # the answer in a sentence or two
    body: str  # the rest of it
    short_zh: str
    body_zh: str
    basis: str  # one of BASES
    source_ids: tuple[str, ...]


def _load() -> tuple[dict[str, dict[str, str]], tuple[QaItem, ...]]:
    data = json.loads((_HERE / "qa_library.json").read_text(encoding="utf-8"))
    items = tuple(QaItem(**{**row, "source_ids": tuple(row["source_ids"])}) for row in data["items"])
    return data["categories"], items


SOURCES.update(
    {row["id"]: Source(**row) for row in json.loads((_HERE / "qa_sources.json").read_text(encoding="utf-8"))}
)
CATEGORIES, ITEMS = _load()
_BY_ID = {i.id: i for i in ITEMS}


def get_item(item_id: str) -> QaItem | None:
    return _BY_ID.get(item_id)


def _check() -> None:
    if len(_BY_ID) != len(ITEMS):
        raise ValueError("duplicate question ids")
    for i in ITEMS:
        if i.category not in CATEGORIES:
            raise ValueError(f"{i.id}: unknown category {i.category!r}")
        if i.basis not in BASES:
            raise ValueError(f"{i.id}: unknown basis {i.basis!r}")
        missing = [s for s in i.source_ids if s not in SOURCES]
        if missing:
            raise ValueError(f"{i.id}: unknown sources {missing}")


_check()
