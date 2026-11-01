"""The guides say what to do, and /sources says who said it (docs/adr/0043);
a rule question gets the rule; Ask's own sentences count what is there."""
from __future__ import annotations

import re

from app.knowledge import jurisdictions as j
from app.knowledge.angling_handbook import TOPICS
from app.knowledge.species_guides import GUIDES, BAIT_RULES
from app.services.rag import ask as rag_ask
from app.services.rag import replies

_CREDIT = re.compile(
    r"\((?:TPWD|CDFW|MDC|Missouri Dept[^)]*|Oklahoma Dept[^)]*|Take Me Fishing|Texas A&M[^)]*|NY DEC|New York DEC)\)"
    r"|\b(?:TPWD|CDFW|MDC) suggests\b|\bper TPWD\b|\bPennsylvania's (?:trout )?advice\b|\bCalifornia reports\b"
)


def _guide_sentences(guide) -> list[str]:
    sentences: list[str] = [guide.summary]
    for value in vars(guide).values():
        if isinstance(value, tuple):
            sentences += [v for v in value if isinstance(v, str)]
    return sentences


def test_no_credit_in_the_running_text():
    found = [s for g in GUIDES for s in _guide_sentences(g) if _CREDIT.search(s)]
    found += [s for t in TOPICS for s in t.body if _CREDIT.search(s)]
    found += [s for s in BAIT_RULES if _CREDIT.search(s)]
    assert found == []


def test_every_guide_and_topic_still_has_a_source_for_the_sources_page():
    assert all(g.source_ids for g in GUIDES)
    assert all(t.source_ids for t in TOPICS)


def test_a_license_question_gets_the_license_rule_and_nothing_else():
    for question, state, want in (
        ("do I need a fishing license", "AL", "all-fish#rule-license-al"),
        ("do I need a fishing license", "TX", "all-fish#rule-license"),
        ("钓鱼需要执照吗", "AL", "all-fish#rule-license-al"),
    ):
        result = rag_ask.search_guides(question, state=state)
        assert [c.id for c in result.citations] == [want], question


def test_with_no_state_every_states_license_rule_stays():
    ids = [c.id for c in rag_ask.search_guides("do I need a fishing license").citations]
    assert len(ids) > 1 and all("rule-license" in i for i in ids)


def test_a_bait_question_keeps_the_guides_under_its_rule():
    ids = [c.id for c in rag_ask.search_guides("what bait for trout", state="CO").citations]
    assert "all-fish#bait_rules-co" in ids and len(ids) > 1


def test_the_reply_counts_the_guides_and_says_what_rules_there_are():
    fish = str(len(GUIDES))
    for lang in replies.LANGS:
        assert fish in replies.coverage(lang), lang
    assert "nineteen" not in replies.coverage("en")
    assert "license rules" in replies.coverage("en") and "执照" in replies.coverage("zh")
    n, dc = j.license_count()
    assert n == 45 and dc
