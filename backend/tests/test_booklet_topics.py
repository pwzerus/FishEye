"""What the state fishing-education booklets taught (2026-11-08, docs/adr/0050).

Booklets from Texas, New York, Minnesota and Oklahoma were read for facts and
written up in our own words: caring for gear, new line, a push-button reel
that won't cast, a hook in your skin, black spots in a fillet, lead, trimming
a fillet, stocked trout. These tests pin the cards, the words that let their
questions through, and the passage vectors that no longer depend on their
neighbours. The questions are scored as an eval set
(eval/rag_cases.BOOKLET_CASES)."""
import numpy as np
import pytest

from app.knowledge.angling_handbook import CATEGORIES, get_topic
from app.knowledge.species_guides import SOURCES
from app.services.rag import embeddings, es, zh
from app.services.rag import ask as rag_ask
from app.services.rag.retriever import is_on_topic, resolve_species

BOOKLET_TOPICS = (
    "tackle-care", "tackle-new-line", "trouble-spincast", "safe-hook-injury", "care-black-spots", "tackle-lead",
    "clean-trim-fillet", "method-stocked-trout",
)


def _ids(result):
    return [p.id for p in result.citations]


def test_the_booklet_topics_exist_and_cite_the_booklets():
    for tid in BOOKLET_TOPICS:
        t = get_topic(tid)
        assert t is not None, tid
        assert t.region == "all" and t.category in CATEGORIES, tid
        assert t.source_ids and all(SOURCES[s].url.startswith("https://") for s in t.source_ids), tid


def test_no_card_copies_a_number_the_booklets_do_not_give():
    # The lead card names no weight: the New York guide's figure didn't
    # survive text extraction, so the card says "small lead sinkers".
    lead = " ".join(get_topic("tackle-lead").body)
    assert "oz" not in lead


@pytest.mark.parametrize(
    ("question", "want"),
    [
        ("how often should I change my fishing line", "all-fish#tackle-new-line"),
        ("I got a fishing hook stuck in my finger, what do I do", "all-fish#safe-hook-injury"),
        ("there are black spots in my bluegill fillet, is it safe to eat?", "all-fish#care-black-spots"),
        ("are lead sinkers bad?", "all-fish#tackle-lead"),
        ("鱼线多久换一次", "all-fish#tackle-new-line"),
        ("铅坠对鸟有害吗", "all-fish#tackle-lead"),
    ],
)
def test_booklet_questions_find_their_card(question, want):
    assert want in _ids(rag_ask.search_guides(question))[:4]


@pytest.mark.parametrize(
    "question",
    ["the button on my zebco doesn't work and no line comes out", "what is the dark strip on a fillet, should I cut it off"],
)
def test_booklet_questions_the_gate_used_to_turn_away(question):
    assert is_on_topic(question)


def test_black_spots_in_a_fillet_are_not_spotted_bass():
    assert resolve_species("there are black spots in my fillet")[0] == ()
    assert resolve_species("what bait do spots bite in winter")[0] == ("spotted-bass",)


def test_chinese_release_and_stocked_trout_are_told_apart():
    assert "stocked" in zh.with_english("放流的虹鳟怎么钓")
    # Letting a fish go is still "release", not stocking.
    letting_go = zh.with_english("放流的时候怎么做才不会伤到鱼")
    assert "release" in letting_go and "stocked" not in letting_go
    assert "care" in zh.with_english("渔轮怎么保养")


def test_spanish_words_the_glossary_lacked():
    assert "fishing line" in es.to_english("¿Cada cuánto cambio el sedal?")
    assert "reel" in es.to_english("¿Cómo limpio mi carrete de pesca?")
    spots = es.to_english("¿Es seguro comer pescado con puntos negros?")
    # "spots" alone reads as spotted bass.
    assert "black spot" in spots and "spots" not in spots


class _Fake:
    name = "fake"

    def __init__(self):
        self.calls = 0

    def encode(self, texts, kind):
        self.calls += 1
        return np.ones((len(texts), 2), dtype=np.float32)


def test_vectors_made_in_batches_are_not_reused(tmp_path, monkeypatch):
    fake = _Fake()
    embeddings.passage_vectors(fake, ["a", "b"], cache_dir=tmp_path)
    embeddings.passage_vectors(fake, ["a", "b"], cache_dir=tmp_path)
    assert fake.calls == 1  # the second call reads the cache
    monkeypatch.setattr(embeddings, "ENCODING", "batches-of-16")
    embeddings.passage_vectors(fake, ["a", "b"], cache_dir=tmp_path)
    assert fake.calls == 2  # another encoding is another key


def test_passages_are_encoded_one_at_a_time():
    # In a batch, the int8 model's on-the-fly quantization made a passage's
    # vector depend on the passages beside it (docs/adr/0050).
    assert embeddings.BATCH == 1
