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


def test_every_state_is_listed_and_three_are_covered():
    assert len(j.JURISDICTIONS) == 51  # 50 states and DC
    assert {c for c, v in j.JURISDICTIONS.items() if v.covered} == {"CA", "GA", "TX"}
    assert j.covered_names() == "California, Georgia and Texas"


def test_a_covered_state_names_its_agency_and_pages():
    tx = j.get("tx")
    assert (tx.name, tx.agency_short) == ("Texas", "TPWD")
    assert tx.limits_url.startswith("https://tpwd.texas.gov/")
    assert tx.license_url.startswith("https://tpwd.texas.gov/")
    ga = j.get("GA")
    assert ga.agency_short == "Georgia WRD"
    assert ga.license_url.startswith("https://georgiawildlife.com/")
    for state in (tx, ga):
        assert state.bait_rules and state.bait_rules_source_ids


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
        "all-fish#safe-lifejacket-tx",
        "all-fish#rule-clean-drain-dry",
        "all-fish#care-filleting-rule",
        "all-fish#start-first-trip",
    ):
        assert by_id[pid].region == "TX", pid


def test_the_georgia_rule_passages_are_all_tagged_and_cite_georgia():
    by_id = {p.id: p for p in build_passages()}
    for pid in (
        "all-fish#bait_rules-ga",
        "all-fish#rule-license-ga",
        "all-fish#safe-lifejacket-ga",
        "all-fish#rule-clean-drain-dry-ga",
        "all-fish#start-first-trip-ga",
        "all-fish#care-possession-ga",
    ):
        p = by_id[pid]
        assert p.region == "GA", pid
        assert "Georgia" in p.text, pid
        assert all(s.startswith(("gawrd-", "garegs-")) for s in p.source_ids), pid


def test_a_states_passages_cite_only_that_states_agency():
    prefixes = {"TX": ("tpwd-",), "GA": ("gawrd-", "garegs-"), "CA": ("cdfw-", "cadbw-")}
    for p in build_passages():
        if p.region in prefixes:
            assert all(s.startswith(prefixes[p.region]) for s in p.source_ids), p.id


def test_the_general_life_jacket_card_states_no_states_law():
    p = {p.id: p for p in build_passages()}["all-fish#safe-lifejacket"]
    assert p.region == j.REGION_ALL
    assert "under 13" not in p.text


def test_an_untagged_passage_never_states_a_texas_rule():
    """The other half: what is shown everywhere may mention Texas as an
    example ("in Texas, the Department of State Health Services"), but a
    rule stated as Texas's belongs in a tagged passage."""
    rule = re.compile(
        r"\b(texas law|texas rules?|tpwd (allows|requires|says)|in (texas|georgia),? (every|you|residents|anglers)"
        r"|georgia (law|wrd requires))\b",
        re.I,
    )
    for p in build_passages():
        if p.region == j.REGION_ALL and p.species_slug == "all-fish":
            assert not rule.search(p.text), p.id


# ------------------------------------------------------------------- Ask


def test_a_rules_question_from_another_state_is_not_answered_with_texas_rules():
    result = rag_ask.search_guides(RULE_QUESTION, state="CO")
    assert result.citations == []
    assert result.trace.outcome == rag_ask.OUTCOME_OTHER_STATE
    assert "Colorado" in result.answer and "California, Georgia and Texas" in result.answer


def test_the_same_question_in_texas_or_without_a_state_gets_the_texas_rules():
    for state in ("TX", "tx", None):
        assert "all-fish#rule-license" in _ids(rag_ask.search_guides(RULE_QUESTION, state=state)), state


def test_each_covered_state_gets_its_own_rules_first():
    for state, want, other in (("GA", "rule-license-ga", "rule-license"), ("TX", "rule-license", "rule-license-ga")):
        ids = _ids(rag_ask.search_guides(RULE_QUESTION, state=state))
        assert ids and ids[0] == f"all-fish#{want}", (state, ids)
        assert f"all-fish#{other}" not in ids, state


@pytest.mark.parametrize(
    ("question", "want"),
    [
        ("does my 12 year old need a fishing license", "rule-license-ga"),
        ("do kids have to wear a life jacket in a boat", "safe-lifejacket-ga"),
        ("is it legal to use a small bass as live bait", "bait_rules-ga"),
        ("can I throw a cast net for shad", "bait_rules-ga"),
        ("how do I stop spreading zebra mussels", "rule-clean-drain-dry-ga"),
        ("can I borrow fishing tackle at a state park", "start-first-trip-ga"),
        ("佐治亚钓鱼需要钓鱼证吗", "rule-license-ga"),
    ],
)
def test_georgia_questions_find_georgias_rules(question, want):
    ids = _ids(rag_ask.search_guides(question, state="GA"))
    assert f"all-fish#{want}" in ids, (question, ids)
    assert not any(i.endswith(("-tx", "#rule-license", "#bait_rules", "#rule-clean-drain-dry")) for i in ids), ids


def test_a_covered_state_without_that_rule_says_so_instead_of_borrowing_texas():
    # FishEye has Texas's filleting rule but no Georgia equivalent.
    result = rag_ask.search_guides("when am I allowed to fillet a fish I keep", state="GA")
    assert all(p.region != "TX" for p in result.citations)
    if not result.citations:
        assert result.trace.outcome == rag_ask.OUTCOME_OTHER_STATE
        assert "some of Georgia's fishing rules" in result.answer


def test_each_state_searches_its_own_index():
    from app.services.rag import regional
    from app.services.rag.retriever import bm25_retriever

    full = bm25_retriever()
    ga, co, ak = (regional.for_state(full, s) for s in ("GA", "CO", "AK"))
    assert {p.region for p in ga.passages} == {"all", "GA"}
    assert {p.region for p in co.passages} == {"all"}
    assert co is ak  # every state without rules shares one view
    assert regional.for_state(full, "GA") is ga  # built once


def test_the_california_rule_passages_are_tagged_and_cite_california():
    by_id = {p.id: p for p in build_passages()}
    for pid in (
        "all-fish#bait_rules-ca",
        "all-fish#rule-license-ca",
        "all-fish#safe-lifejacket-ca",
        "all-fish#rule-clean-drain-dry-ca",
        "all-fish#start-first-trip-ca",
        "all-fish#care-keeping-ca",
    ):
        p = by_id[pid]
        assert p.region == "CA" and "California" in p.text, pid


@pytest.mark.parametrize(
    ("question", "want"),
    [
        ("do I need a fishing license", "rule-license-ca"),
        ("does my 14 year old need a license", "rule-license-ca"),
        ("can I fish with two rods", "rule-license-ca"),
        ("do I need a report card for sturgeon", "rule-license-ca"),
        ("do kids have to wear a life jacket in a kayak", "safe-lifejacket-ca"),
        ("can I use live minnows as bait", "bait_rules-ca"),
        ("can I use dead sardines as bait", "bait_rules-ca"),
        ("what is a mussel fee sticker", "rule-clean-drain-dry-ca"),
        ("how long do I dry my boat for quagga mussels", "rule-clean-drain-dry-ca"),
        ("how is a fish measured for the length limit", "care-keeping-ca"),
        ("加州钓鱼要钓鱼证吗", "rule-license-ca"),
    ],
)
def test_california_questions_find_californias_rules(question, want):
    ids = _ids(rag_ask.search_guides(question, state="CA"))
    assert f"all-fish#{want}" in ids, (question, ids)
    assert all(not i.endswith(("-tx", "-ga")) for i in ids), ids


def test_every_bait_question_in_california_shows_its_bait_rules():
    # The guides recommend live minnows; California forbids fish as bait in
    # most inland waters. Whatever ranks first, the rule is right under it.
    for q in ("what bait for crappie", "best live bait for bass", "鲈鱼用什么饵"):
        ids = _ids(rag_ask.search_guides(q, state="CA"))
        assert ids[1] == "all-fish#bait_rules-ca", (q, ids)
    # Not in states whose rules don't contradict the guides, and not for
    # questions that aren't about bait.
    assert "all-fish#bait_rules" not in _ids(rag_ask.search_guides("what bait for crappie", state="TX"))[:1]
    assert "all-fish#bait_rules-ca" not in _ids(rag_ask.search_guides("how do I tie a palomar knot", state="CA"))


def test_texas_never_sees_georgias_rules():
    for q in (RULE_QUESTION, "kids life jacket", "can I use live bait or a cast net", "zebra mussels boat"):
        for p in rag_ask.search_guides(q, state="TX").citations:
            assert p.region in (j.REGION_ALL, "TX"), (q, p.id)


def test_how_to_questions_get_the_same_answer_in_every_state():
    # Each state searches its own index (ADR 0028), whose word statistics
    # differ a little, so the order below the top can shift; what is shown
    # is the same guidance. California adds its bait rules (ADR 0030).
    q = "what bait works for crappie"
    answers = {s: _ids(rag_ask.search_guides(q, state=s)) for s in ("TX", "CO", "GA")}
    assert len({tuple(a[:2]) for a in answers.values()}) == 1
    for a in answers.values():
        assert all(i.split("#")[0] in ("white-crappie", "black-crappie") for i in a), a


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
    assert "California, Georgia and Texas" in text


# ------------------------------------------------------------------- API


def test_jurisdictions_endpoint_lists_covered_states_first(client):
    body = client.get("/api/jurisdictions").json()
    assert len(body) == 51
    assert [s["code"] for s in body[:3]] == ["CA", "GA", "TX"]
    assert all(s["covered"] and s["bait_rules"] and s["bait_rules_sources"] for s in body[:3])
    assert body[2]["agency_short"] == "TPWD"
    colorado = next(s for s in body if s["code"] == "CO")
    assert colorado["covered"] is False and colorado["limits_url"] is None
    assert colorado["bait_rules"] == []


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
    assert topics["rule-license-ga"] == "GA" and topics["safe-lifejacket"] == "all"
    guides = client.get("/api/species/guides").json()
    assert {g["legal_notes_region"] for g in guides} == {"TX"}


@pytest.mark.parametrize("state", ["CO", "TX", "GA"])
def test_summary_is_refused_only_when_the_search_finds_nothing(client, state):
    # An AI summary can't be spent on a rules question another state's
    # reader would only get "not written yet" for. (Needs sign-in first, so
    # the contract tested here is the search half they share.)
    result = rag_ask.search_guides(RULE_QUESTION, state=state)
    assert bool(result.citations) == (state != "CO")
