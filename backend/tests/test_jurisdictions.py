"""Whose rules apply (knowledge/jurisdictions.py, docs/adr/0027).

How to catch a fish is for everyone; a rule belongs to a state. These tests
pin the part that matters most: a person in another state must never be
given Texas's rules as if they were theirs."""
import re

import pytest

from app.knowledge import jurisdictions as j
from app.knowledge.angling_handbook import TOPICS
from app.services.rag import ask as rag_ask
from app.services.rag.chunking import build_passages

RULE_QUESTION = "do I need a fishing licence"


def _ids(result):
    return [p.id for p in result.citations]


# ---------------------------------------------------------------- registry


def test_every_state_is_listed_and_texas_is_the_only_covered_one():
    assert len(j.JURISDICTIONS) == 51  # 50 states and DC
    assert {c for c, v in j.JURISDICTIONS.items() if v.covered} == {"TX"}


def test_a_covered_state_names_its_agency_and_pages():
    tx = j.get("tx")
    assert (tx.name, tx.agency_short) == ("Texas", "TPWD")
    assert tx.limits_url.startswith("https://tpwd.texas.gov/")
    assert tx.license_url.startswith("https://tpwd.texas.gov/")


def test_an_uncovered_state_has_no_invented_links():
    co = j.get("CO")
    assert not co.covered
    assert co.agency is None and co.limits_url is None and co.license_url is None
    assert co.agency_label == "Colorado's fish and wildlife agency"


def test_normalize_accepts_codes_and_nothing_else():
    assert j.normalize(" tx ") == "TX"
    assert j.normalize("ZZ") is None
    assert j.normalize("Texas") is None
    assert j.normalize(None) is None


def test_applies():
    assert j.applies("all", "CO")
    assert j.applies("TX", "TX")
    assert not j.applies("TX", "CO")
    assert j.applies("TX", None)  # no state given: nothing is hidden


# ------------------------------------------------------------ the content


def test_every_region_in_the_content_is_a_real_state():
    regions = {p.region for p in build_passages()} | {t.region for t in TOPICS}
    assert regions <= {j.REGION_ALL} | set(j.JURISDICTIONS)
    assert "TX" in regions


def test_the_texas_rule_passages_are_all_tagged():
    by_id = {p.id: p for p in build_passages()}
    for pid in (
        "all-fish#bait_rules",
        "all-fish#rule-license",
        "all-fish#safe-lifejacket",
        "all-fish#rule-clean-drain-dry",
        "all-fish#care-filleting-rule",
        "all-fish#start-first-trip",
    ):
        assert by_id[pid].region == "TX", pid


def test_an_untagged_passage_never_states_a_texas_rule():
    """The other half: what is shown everywhere may mention Texas as an
    example ("in Texas, the Department of State Health Services"), but a
    rule stated as Texas's belongs in a tagged passage."""
    rule = re.compile(r"\b(texas law|texas rules?|tpwd (allows|requires|says)|in texas,? (every|you|residents))\b", re.I)
    for p in build_passages():
        if p.region == j.REGION_ALL and p.species_slug == "all-fish":
            assert not rule.search(p.text), p.id


# ------------------------------------------------------------------- Ask


def test_a_rules_question_from_another_state_is_not_answered_with_texas_rules():
    result = rag_ask.search_guides(RULE_QUESTION, state="CO")
    assert result.citations == []
    assert result.trace.outcome == rag_ask.OUTCOME_OTHER_STATE
    assert "Colorado" in result.answer and "Texas" in result.answer


def test_the_same_question_in_texas_or_without_a_state_gets_the_texas_rules():
    for state in ("TX", "tx", None):
        assert "all-fish#rule-license" in _ids(rag_ask.search_guides(RULE_QUESTION, state=state)), state


def test_how_to_questions_are_the_same_in_every_state():
    q = "what bait works for crappie"
    texas = _ids(rag_ask.search_guides(q, state="TX"))
    colorado = _ids(rag_ask.search_guides(q, state="CO"))
    assert colorado and colorado == texas


def test_what_ranks_below_another_states_rule_is_not_shown_as_an_answer():
    # The licence passage is the best match; the rest are filler. Showing
    # the filler would read as an answer to "do I need a licence".
    assert rag_ask.search_guides(RULE_QUESTION, state="CO").citations == []


def test_a_state_never_sees_passages_of_another_state():
    for q in ("can I use live bait or a cast net", "what should I put in my tackle box", "kids life jacket"):
        for p in rag_ask.search_guides(q, state="CO").citations:
            assert p.region == j.REGION_ALL, (q, p.id)


def test_the_other_state_answer_names_who_to_ask_and_what_is_covered():
    text = j.other_state_answer("OK")
    assert "Oklahoma's fish and wildlife agency" in text
    assert "Texas" in text


# ------------------------------------------------------------------- API


def test_jurisdictions_endpoint_lists_covered_states_first(client):
    body = client.get("/api/jurisdictions").json()
    assert len(body) == 51
    assert body[0]["code"] == "TX" and body[0]["covered"] is True
    assert body[0]["agency_short"] == "TPWD"
    colorado = next(s for s in body if s["code"] == "CO")
    assert colorado["covered"] is False and colorado["limits_url"] is None


def test_ask_endpoint_takes_a_state(client):
    other = client.post("/api/ask", json={"question": RULE_QUESTION, "state": "CO"}).json()
    assert other["citations"] == [] and other["trace"]["outcome"] == "other_state"
    texas = client.post("/api/ask", json={"question": RULE_QUESTION, "state": "TX"}).json()
    assert "TX" in {c["region"] for c in texas["citations"]}


def test_ask_endpoint_rejects_an_unknown_state(client):
    assert client.post("/api/ask", json={"question": RULE_QUESTION, "state": "ZZ"}).status_code == 422
    assert client.post("/api/ask", json={"question": RULE_QUESTION, "state": "Texas"}).status_code == 422


def test_citations_say_which_are_regional(client):
    body = client.post("/api/ask", json={"question": "what bait for crappie"}).json()
    assert {c["region"] for c in body["citations"]} == {"all"}


def test_handbook_and_guides_say_which_parts_are_one_states_rules(client):
    topics = {t["id"]: t["region"] for t in client.get("/api/species/handbook").json()}
    assert topics["rule-license"] == "TX" and topics["bait-worms"] == "all"
    guides = client.get("/api/species/guides").json()
    assert {g["legal_notes_region"] for g in guides} == {"TX"}


@pytest.mark.parametrize("state", ["CO", "TX"])
def test_summary_is_refused_only_when_the_search_finds_nothing(client, state):
    # An AI summary can't be spent on a rules question another state's
    # reader would only get "not written yet" for. (Needs sign-in first, so
    # the contract tested here is the search half they share.)
    result = rag_ask.search_guides(RULE_QUESTION, state=state)
    assert bool(result.citations) == (state == "TX")
