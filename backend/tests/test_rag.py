"""Guide Q&A (services/rag/): chunking, retrieval, grounding, fallback, API.

Runs against the real guide content and the mock provider — no network.
Retrieval *quality* across many questions is measured by the eval
(app/eval/rag_cases.py, tests/test_rag_eval.py); these are the mechanics.
"""
from __future__ import annotations

import json

import pytest

from app.knowledge.species_guides import GUIDES, get_guide
from app.services.llm import LLMProvider, LLMResponse, LLMUnavailable
from app.services.llm.mock import (
    FAILURE_HALLUCINATED_SOURCE,
    FAILURE_HALLUCINATED_SPECIES,
    FAILURE_INVALID_JSON,
    FAILURE_INVENTED_NUMBER,
    FAILURE_UNAVAILABLE,
    MockProvider,
)
from app.services.rag import ask as rag
from app.services.rag.chunking import SHARED_SLUG, build_passages
from app.services.rag.retriever import (
    BM25Retriever,
    default_retriever,
    detect_species,
    split_species,
    stem,
)


@pytest.fixture(autouse=True)
def _fresh_cache():
    rag.reset_cache()
    yield
    rag.reset_cache()


def _ids(hits):
    return [h.passage.id for h in hits]


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------


def test_every_guide_is_indexed_with_an_overview_and_diet():
    ids = {p.id for p in build_passages()}
    for g in GUIDES:
        assert f"{g.slug}#overview" in ids
        assert f"{g.slug}#diet" in ids


def test_passage_ids_are_unique_and_every_setup_is_its_own_passage():
    passages = build_passages()
    assert len({p.id for p in passages}) == len(passages)
    for g in GUIDES:
        setups = [p for p in passages if p.species_slug == g.slug and p.section.startswith("setup-")]
        assert len(setups) == len(g.setups)


def test_setup_passages_cite_that_setups_own_sources_not_the_whole_guide():
    guide = get_guide("white-crappie")
    assert guide is not None
    passage = next(p for p in build_passages() if p.id == "white-crappie#setup-1")
    assert passage.source_ids == guide.setups[0].source_ids
    assert passage.source_ids != guide.source_ids


def test_passages_carry_a_header_naming_the_fish_and_section():
    passage = next(p for p in build_passages() if p.id == "bluegill#diet")
    assert passage.text.startswith("Bluegill — What it eats: ")


def test_the_repeated_bait_rules_are_indexed_once():
    rules = [p for p in build_passages() if "unlawful to use any game fish" in p.text]
    assert [p.id for p in rules] == [f"{SHARED_SLUG}#bait_rules"]


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word, expected",
    [("crappies", "crappie"), ("jigging", "jig"), ("inches", "inch"), ("bass", "bass"), ("lures", "lure")],
)
def test_the_stemmer_handles_plurals_and_ing_without_mangling_bass(word, expected):
    assert stem(word) == expected


def test_texas_nicknames_route_to_the_right_fish():
    assert detect_species("when do sand bass run") == ("white-bass",)
    assert detect_species("bream on a cane pole") == ("bluegill",)
    assert detect_species("striper rod") == ("striped-bass",)


def test_a_specific_name_is_consumed_so_it_does_not_also_count_as_the_family():
    named, residual = split_species("white crappie bait")
    assert named == ("white-crappie",)
    assert "crappie" not in residual


def test_routing_keeps_other_species_out_of_the_answer():
    hits = default_retriever().search("what bait for crappie")
    assert hits
    assert {h.passage.species_slug for h in hits} <= {"white-crappie", "black-crappie", SHARED_SLUG}


def test_a_question_about_two_fish_gets_passages_for_both():
    hits = default_retriever().search("what gear do I need for catfish", k=4)
    assert {h.passage.species_slug for h in hits} == {"channel-catfish", "blue-catfish"}


def test_shared_passages_only_fill_slots_the_fish_left_empty():
    hits = default_retriever().search("where do bluegill hang out in summer", k=4)
    slugs = [h.passage.species_slug for h in hits]
    if SHARED_SLUG in slugs:
        first_shared = slugs.index(SHARED_SLUG)
        assert all(s == SHARED_SLUG for s in slugs[first_shared:])


def test_a_question_that_only_names_a_fish_starts_with_its_overview():
    hits = default_retriever().search("tell me about bluegill")
    assert _ids(hits)[0] == "bluegill#overview"
    assert all(h.score == 0.0 for h in hits)  # section order, not a text match


def test_page_context_is_a_hard_filter():
    hits = default_retriever().search("what do they eat", species=("blue-catfish",))
    assert _ids(hits)[0] == "blue-catfish#diet"
    assert all(h.passage.species_slug in {"blue-catfish", SHARED_SLUG} for h in hits)


def test_a_fish_named_in_the_question_beats_the_page_it_was_asked_on():
    hits = default_retriever().search("what bait for bluegill", species=("blue-catfish",))
    assert hits and all(h.passage.species_slug in {"bluegill", SHARED_SLUG} for h in hits)


def test_off_topic_questions_retrieve_nothing():
    assert default_retriever().search("what is the capital of france") == []


def test_results_are_deterministic():
    r = BM25Retriever(build_passages())
    assert _ids(r.search("slip bobber minnow")) == _ids(r.search("slip bobber minnow"))


# --------------------------------------------------------------------------
# Validation (parse_and_validate)
# --------------------------------------------------------------------------


def _passages(*ids):
    by_id = {p.id: p for p in build_passages()}
    return [by_id[i] for i in ids]


def _reply(answer, citations):
    return json.dumps({"answer": answer, "citations": citations})


def test_a_grounded_answer_passes_and_citations_are_deduplicated():
    ps = _passages("white-crappie#live_baits")
    answer, cited = rag.parse_and_validate(
        _reply("Use small live minnows.", ["white-crappie#live_baits", "white-crappie#live_baits"]),
        "crappie bait?",
        ps,
    )
    assert answer == "Use small live minnows."
    assert [p.id for p in cited] == ["white-crappie#live_baits"]


@pytest.mark.parametrize(
    "raw, outcome",
    [
        ("not json at all", rag.OUTCOME_INVALID_JSON),
        (json.dumps({"answer": "", "citations": ["x"]}), rag.OUTCOME_INVALID_JSON),
        (json.dumps({"answer": "Minnows.", "citations": []}), rag.OUTCOME_INVALID_JSON),
        (_reply("Minnows.", ["bluegill#diet"]), rag.OUTCOME_UNGROUNDED_CITATION),
        (_reply("See https://example.com", ["white-crappie#live_baits"]), rag.OUTCOME_URL_IN_ANSWER),
        (_reply("Blue Catfish like minnows too.", ["white-crappie#live_baits"]), rag.OUTCOME_UNGROUNDED_SPECIES),
        (_reply("Use a size 37 hook.", ["white-crappie#live_baits"]), rag.OUTCOME_UNGROUNDED_NUMBER),
    ],
)
def test_ungrounded_or_malformed_replies_are_rejected(raw, outcome):
    with pytest.raises(rag.GroundingError) as exc:
        rag.parse_and_validate(raw, "crappie bait?", _passages("white-crappie#live_baits"))
    assert exc.value.outcome == outcome


def test_unicode_fractions_in_the_guides_match_ascii_in_the_answer():
    ps = _passages("white-crappie#live_baits")  # "1½–2½ in minnows"
    answer, _ = rag.parse_and_validate(
        _reply("Minnows 1 1/2 to 2 1/2 inches long.", ["white-crappie#live_baits"]), "q", ps
    )
    assert "1 1/2" in answer


def test_numbers_the_user_wrote_are_allowed_back_in_the_answer():
    ps = _passages("white-crappie#live_baits")
    rag.parse_and_validate(_reply("At 15 ft, use minnows.", ["white-crappie#live_baits"]), "fishing at 15 ft?", ps)


def test_a_fish_named_in_an_uncited_but_given_passage_is_not_a_fabrication():
    ps = _passages("white-crappie#live_baits", "black-crappie#live_baits")
    rag.parse_and_validate(
        _reply("Black Crappie take the same minnows.", ["white-crappie#live_baits"]), "q", ps
    )


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


class _NeverCalled(LLMProvider):
    name = "never"

    def complete(self, system_prompt, user_prompt):  # pragma: no cover - must not run
        raise AssertionError("the model must not be called without passages")


class _Scripted(LLMProvider):
    """Returns the given replies in order."""

    name = "scripted"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def complete(self, system_prompt, user_prompt):
        self.calls += 1
        return LLMResponse(self.replies.pop(0), "scripted", "s-1", 10, 5, 0.0, 1.0)


def test_happy_path_answers_from_the_model_with_validated_citations():
    result = rag.ask("what bait for crappie", provider=MockProvider())
    assert result.answer_source == rag.ANSWER_LLM
    assert result.trace.outcome == rag.OUTCOME_OK
    retrieved = {r["id"] for r in result.trace.retrieved}
    assert result.citations and {p.id for p in result.citations} <= retrieved


def test_nothing_retrieved_short_circuits_without_calling_the_model():
    result = rag.ask("what is the capital of france", provider=_NeverCalled())
    assert result.answer_source == rag.ANSWER_NO_MATCH
    assert result.trace.outcome == rag.OUTCOME_NO_MATCH
    assert result.citations == []


def test_a_named_fish_question_its_guide_cannot_answer_is_not_covered():
    # Regression: this used to widen to every guide and come back with the
    # threadfin shad bait list ("Striped bass and hybrid striped bass, live").
    result = rag.ask("how do I tell white bass from hybrid striped bass", provider=_NeverCalled())
    assert result.answer_source == rag.ANSWER_NO_MATCH
    assert result.trace.routed_species == ["hybrid-striped-bass", "white-bass"]
    assert result.citations == []


def test_routing_never_widens_to_other_fish():
    for q in ("how do I tell white bass from hybrid striped bass", "how do I tell a striper from a hybrid"):
        hits = default_retriever().search(q)
        assert all("shad" not in h.passage.species_slug for h in hits), q


@pytest.mark.parametrize(
    "mode, outcome, attempts",
    [
        (FAILURE_HALLUCINATED_SOURCE, rag.OUTCOME_UNGROUNDED_CITATION, 2),
        (FAILURE_HALLUCINATED_SPECIES, rag.OUTCOME_UNGROUNDED_SPECIES, 2),
        (FAILURE_INVENTED_NUMBER, rag.OUTCOME_UNGROUNDED_NUMBER, 2),
        (FAILURE_INVALID_JSON, rag.OUTCOME_INVALID_JSON, 2),
        (FAILURE_UNAVAILABLE, rag.OUTCOME_PROVIDER_UNAVAILABLE, 0),
    ],
)
def test_every_failure_mode_falls_back_to_quoting_the_guides(mode, outcome, attempts):
    result = rag.ask("what bait for crappie", provider=MockProvider(failure_mode=mode))
    assert result.answer_source == rag.ANSWER_FALLBACK
    assert result.trace.outcome == outcome
    assert result.trace.validation_attempts == attempts
    assert result.answer.startswith("Here's what the FishEye guides say:")
    # The fallback quotes passages verbatim, so it cites exactly what it quotes.
    for p in result.citations:
        assert rag.body_of(p) in result.answer


def test_a_bad_first_reply_is_retried_once():
    good = _reply("Use live minnows.", ["white-crappie#live_baits"])
    provider = _Scripted(["{broken", good])
    result = rag.ask("what bait for white crappie", provider=provider)
    assert result.answer_source == rag.ANSWER_LLM
    assert result.trace.validation_attempts == 2
    assert provider.calls == 2


def test_accepted_answers_are_cached_and_fallbacks_are_not():
    first = rag.ask("what bait for crappie", provider=MockProvider())
    second = rag.ask("what bait for crappie", provider=_NeverCalled())
    assert second.trace.cache_hit and second.answer == first.answer
    assert second.trace.trace_id != first.trace.trace_id

    rag.reset_cache()
    rag.ask("what bait for bluegill", provider=MockProvider(failure_mode=FAILURE_UNAVAILABLE))
    retry = rag.ask("what bait for bluegill", provider=MockProvider())
    assert not retry.trace.cache_hit and retry.answer_source == rag.ANSWER_LLM


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------


def test_ask_endpoint_returns_answer_citations_and_trace(client):
    resp = client.post("/api/ask", json={"question": "what bait for crappie"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer_source"] == "llm"
    assert body["trace"]["retriever"] == "bm25"
    assert body["trace"]["routed_species"] == ["white-crappie", "black-crappie"]
    first = body["citations"][0]
    assert first["species_name"] in {"White Crappie", "Black Crappie"}
    assert not first["excerpt"].startswith(first["species_name"])  # header stripped
    assert first["sources"] and first["sources"][0]["url"].startswith("https://")


def test_ask_endpoint_uses_the_page_species_as_context(client):
    body = client.post(
        "/api/ask", json={"question": "what do they eat", "species_slug": "blue-catfish"}
    ).json()
    assert body["citations"][0]["id"] == "blue-catfish#diet"


def test_ask_endpoint_rejects_unknown_species_and_bad_questions(client):
    assert client.post("/api/ask", json={"question": "bait?", "species_slug": "nessie"}).status_code == 404
    assert client.post("/api/ask", json={"question": "hi"}).status_code == 422
    assert client.post("/api/ask", json={"question": "x" * 301}).status_code == 422


def test_ask_endpoint_reports_not_covered_honestly(client):
    body = client.post("/api/ask", json={"question": "what is the capital of france"}).json()
    assert body["answer_source"] == "no_match"
    assert body["citations"] == []
    assert body["trace"]["provider"] == "none"


def test_provider_outage_still_returns_200(client, monkeypatch):
    from app.services import llm

    monkeypatch.setenv("LLM_MOCK_FAILURE_MODE", "unavailable")
    llm.reset_provider_cache()
    try:
        body = client.post("/api/ask", json={"question": "what bait for bluegill"}).json()
    finally:
        monkeypatch.delenv("LLM_MOCK_FAILURE_MODE")
        llm.reset_provider_cache()
    assert body["answer_source"] == "fallback"
    assert body["trace"]["outcome"] == "provider_unavailable"


def test_llm_unavailable_is_importable_for_provider_authors():
    # Guards the public surface ask.py relies on.
    assert issubclass(LLMUnavailable, Exception)
