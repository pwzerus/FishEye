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
# A rule FishEye has written for Minnesota but not for Texas (2026-11-06:
# every state has its licence rule now, so that no longer serves).
UNWRITTEN = ("is there a free fishing day", "TX")


def _ids(result):
    return [p.id for p in result.citations]


# ---------------------------------------------------------------- registry


def test_every_state_is_listed_and_most_have_their_bait_rules():
    assert len(j.JURISDICTIONS) == 51  # 50 states and DC
    # Not found in a page that could be read and checked (2026-11-01).
    assert {c for c, v in j.JURISDICTIONS.items() if not v.covered} == {"AK", "DE", "HI", "MT", "SD"}
    assert j.covered_names() == "45 states and Washington, D.C."


def test_every_written_state_cites_its_own_agency_page():
    from app.knowledge.species_guides import SOURCES

    for code in j.STATE_BAIT_RULES:
        state = j.JURISDICTIONS[code]
        assert state.bait_rules and state.bait_rules_source_ids[0] == f"bait-{code.lower()}", code
        source = SOURCES[state.bait_rules_source_ids[0]]
        assert source.url.startswith("https://") and source.label.startswith(state.agency_short), code
        assert all(rule.endswith((".", ")")) for rule in state.bait_rules), code
    # Where live fish are mostly banned as bait, every bait question shows the rules.
    assert j.get("NV").bait_rules_on_every_bait_question and not j.get("MO").bait_rules_on_every_bait_question


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


def test_a_state_without_written_rules_still_names_its_agency_and_pages():
    """Every state's agency and its regulations and licence pages are on
    file (opened and checked 2026-10-29); "covered" still means FishEye has
    written that state's rules."""
    mt = j.get("MT")
    assert not mt.covered
    assert (mt.agency, mt.agency_short) == ("Montana Fish, Wildlife & Parks", "Montana FWP")
    assert mt.limits_url.startswith("https://fwp.mt.gov/")
    assert mt.agency_label == "Montana FWP"
    for code, state in j.JURISDICTIONS.items():
        assert state.agency and state.agency_short, code
        assert state.limits_url.startswith("https://") and state.license_url.startswith("https://"), code


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
    question, state = UNWRITTEN
    result = rag_ask.search_guides(question, state=state)
    assert result.citations == []
    assert result.trace.outcome == rag_ask.OUTCOME_OTHER_STATE
    assert "Texas" in result.answer


def test_a_state_with_a_license_topic_answers_with_it():
    result = rag_ask.search_guides(RULE_QUESTION, state="AL")
    assert result.citations[0].id == "all-fish#rule-license-al" and "Alabama" in result.citations[0].text
    assert j.get("AK").license_from_age is None  # residents and visitors differ
    assert j.get("AL").license_from_age == 16 and j.get("AL").license_topic == "rule-license-al"


def test_the_rule_for_every_state_answers_in_a_state_without_its_own():
    result = rag_ask.search_guides("how do I stop spreading zebra mussels", state="AL")
    assert result.citations[0].id == "all-fish#rule-clean-drain-dry-us"


@pytest.mark.parametrize(
    ("question", "want"),
    [
        ("do I need a fishing license in Minnesota?", "MN"),
        ("License rules in Texas.", "TX"),
        ("west virginia trout stamp", "WV"),  # not Virginia
        ("Virginia trout stamp", "VA"),
        ("Arkansas crappie limit", "AR"),  # not Kansas
        ("fishing in Washington, D.C.", "DC"),
        ("Lake Washington perch", "WA"),
        ("明尼苏达钓鱼需要执照吗", "MN"),
        ("西弗吉尼亚鳟鱼", "WV"),
        ("加州能用活饵吗", "CA"),
        ("得州钓鱼证多少钱", "TX"),
        # Not a place: rigs and fish named after a state, Kansas City.
        ("how do I tie a Texas rig", None),
        ("what do Kentucky bass eat", None),
        ("Kansas City catfish", None),
        ("肯塔基鲈用什么饵", None),
        # Two states: no one state to answer for.
        ("Texas or Oklahoma license on Texoma", None),
        ("what bait for crappie", None),
    ],
)
def test_a_state_named_in_a_question_is_recognised(question, want):
    assert j.state_in_question(question) == want


def test_a_state_named_in_the_question_wins_over_the_one_picked():
    """The 2026-10-28 review: a Minnesota licence question was answered with
    Texas's, Georgia's and California's rules. Since 2026-11-06 Minnesota's
    own licence rule is written, and it answers wherever the reader is."""
    for picked in (None, "TX"):
        result = rag_ask.search_guides("do I need a fishing license in Minnesota", state=picked)
        assert result.citations[0].id == "all-fish#rule-license-mn", picked
        assert {c.region for c in result.citations} <= {"MN", "all"}
    # Named in Chinese, answered from the same passage.
    result = rag_ask.search_guides("明尼苏达钓鱼需要执照吗")
    assert result.citations[0].id == "all-fish#rule-license-mn"
    # A rule that isn't written for the state picked says so.
    result = rag_ask.search_guides(*UNWRITTEN[:1], state=UNWRITTEN[1])
    assert result.citations == [] and "some of Texas's fishing rules" in result.answer
    # A covered state named in the question gets its own rules, whatever was picked.
    ids = _ids(rag_ask.search_guides("do I need a fishing license in Georgia", state="TX"))
    assert ids and ids[0] == "all-fish#rule-license-ga", ids


def test_a_question_in_chinese_is_introduced_in_chinese():
    result = rag_ask.search_guides("钓鲶鱼用什么饵")
    assert result.citations and result.answer == rag_ask.PASSAGES_INTRO_ZH


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
    ga, co, mt, ak = (regional.for_state(full, s) for s in ("GA", "CO", "MT", "AK"))
    assert {p.region for p in ga.passages} == {"all", "GA"}
    assert {p.region for p in co.passages} == {"all", "CO"}
    assert {p.region for p in mt.passages} == {"all", "MT"}  # a license topic and nothing else
    assert {p.region for p in ak.passages} == {"all", "AK"}
    # No state picked: the three states written up first, none of the
    # bait-rules-only ones (they'd answer every bait question).
    assert {p.region for p in regional.for_state(full, None).passages} == {"all", "CA", "GA", "TX"}
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
    answers = {s: _ids(rag_ask.search_guides(q, state=s)) for s in ("TX", "MT", "GA")}
    assert len({tuple(a[:2]) for a in answers.values()}) == 1
    for a in answers.values():
        assert all(i.split("#")[0] in ("white-crappie", "black-crappie") for i in a), a


def test_what_ranks_below_another_states_rule_is_not_shown_as_an_answer():
    # The licence passage is the best match; the rest are filler. Showing
    # the filler would read as an answer to "do I need a licence".
    assert rag_ask.search_guides(UNWRITTEN[0], state=UNWRITTEN[1]).citations == []


def test_a_state_never_sees_passages_of_another_state():
    for q in ("can I use live bait or a cast net", "what should I put in my tackle box", "kids life jacket"):
        for p in rag_ask.search_guides(q, state="MT").citations:
            assert p.region in (j.REGION_ALL, "MT"), (q, p.id)
        for p in rag_ask.search_guides(q, state="CO").citations:
            assert p.region in (j.REGION_ALL, "CO"), (q, p.id)


def test_a_state_with_bait_rules_gets_them_for_a_bait_question():
    # Colorado bans live fish as bait in much of the state, against the
    # guides' live-minnow advice: the rules come with any bait question.
    ids = _ids(rag_ask.search_guides("what bait for trout", state="CO"))
    assert "all-fish#bait_rules-co" in ids, ids
    ids = _ids(rag_ask.search_guides("can I use goldfish as bait", state="MI"))
    assert "all-fish#bait_rules-mi" in ids, ids


def test_the_other_state_answer_names_who_to_ask_and_what_is_covered():
    text = j.other_state_answer("SD")
    # South Dakota's own agency, by name, spelled out once.
    assert "check SD GFP (South Dakota Game, Fish and Parks) for the current ones" in text
    assert "45 states and Washington, D.C." in text


# ------------------------------------------------------------------- API


def test_jurisdictions_endpoint_lists_covered_states_first(client):
    body = client.get("/api/jurisdictions").json()
    assert len(body) == 51
    covered = [s for s in body if s["covered"]]
    assert body[: len(covered)] == covered and len(covered) == 46
    assert all(s["bait_rules"] and s["bait_rules_sources"] for s in covered)
    montana = next(s for s in body if s["code"] == "MT")
    # No bait rules written, but its license topic is, and its agency's pages are linked.
    assert montana["covered"] is False and montana["limits_url"].startswith("https://fwp.mt.gov/")
    assert montana["bait_rules"] == []
    assert montana["license_from_age"] == 12 and montana["license_topic"] == "rule-license-mt"
    ages = {s["code"]: s["license_from_age"] for s in body}
    assert ages["CA"] == 16 and ages["TX"] == 17 and ages["MN"] == 16 and ages["HI"] is None
    topics = {s["license_topic"] for s in body if s["license_topic"]}
    assert len(topics) == 51


@pytest.mark.parametrize("code", ["CA", "GA", "TX"])
def test_a_states_licence_age_is_the_one_its_handbook_topic_states(code):
    """The start page and a lake's rules row say "a licence from 16" in a
    line; the topic they link to must say the same thing, with the detail."""
    state = j.JURISDICTIONS[code]
    topics = {t.id: t for t in TOPICS}
    licence, first_trip = topics[state.license_topic], topics[state.first_trip_topic]
    assert licence.region == code and first_trip.region == code
    text = " ".join(licence.body)
    age = state.license_from_age
    assert f"{age} and older" in text or f"{age} or older" in text or f"under {age}" in text


def test_ask_endpoint_takes_a_state(client):
    other = client.post("/api/ask", json={"question": UNWRITTEN[0], "state": UNWRITTEN[1]}).json()
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


@pytest.mark.parametrize("state", ["MN", "TX", "GA"])
def test_summary_is_refused_only_when_the_search_finds_nothing(client, state):
    # An AI summary can't be spent on a rules question another state's
    # reader would only get "not written yet" for. (Needs sign-in first, so
    # the contract tested here is the search half they share.)
    result = rag_ask.search_guides(RULE_QUESTION, state=state)
    assert result.citations
    assert not rag_ask.search_guides(UNWRITTEN[0], state=UNWRITTEN[1]).citations
