"""Hybrid (keyword + semantic) retrieval, docs/adr/0025.

The fusion and routing rules are tested with a fake embedder whose vectors
are chosen by hand, so these run without the 470 MB model. The last test
uses the real model and is skipped when it isn't installed."""
import pytest

# The semantic extras (requirements-semantic.txt) are optional; CI without
# them skips this file rather than failing it.
np = pytest.importorskip("numpy")

from app.services.rag.embeddings import MODEL_DIR, load_embedder  # noqa: E402
from app.services.rag.hybrid import HybridRetriever  # noqa: E402
from app.services.rag.retriever import bm25_retriever, split_species  # noqa: E402


class FakeEmbedder:
    """Every passage gets a unit vector of its own; a query is pointed at
    whichever passage ids `targets` maps it to (cosine 1.0), or at nothing
    (cosine 0)."""

    name = "fake"

    def __init__(self, passage_ids: list[str], targets: dict[str, str]):
        self.index = {pid: i for i, pid in enumerate(passage_ids)}
        self.n = len(passage_ids)
        self.targets = targets

    def encode(self, texts, kind):
        out = np.zeros((len(texts), self.n), dtype=np.float32)
        for row, text in enumerate(texts):
            if kind == "passage":
                out[row, row] = 1.0
            elif text in self.targets:
                out[row, self.index[self.targets[text]]] = 1.0
        return out


def _hybrid(targets: dict[str, str]) -> HybridRetriever:
    bm25 = bm25_retriever()
    ids = [p.id for p in bm25.passages]
    fake = FakeEmbedder(ids, targets)
    return HybridRetriever(bm25, fake, vectors=fake.encode(ids, "passage"))


def _ids(hits):
    return [h.passage.id for h in hits]


def test_a_chinese_question_with_no_english_word_is_found_by_meaning():
    r = _hybrid({"怎么杀鱼最人道": "all-fish#care-dispatch-bleed"})
    assert _ids(r.search("怎么杀鱼最人道"))[0] == "all-fish#care-dispatch-bleed"


def test_chinese_fish_names_route_like_english_ones():
    assert split_species("鲈鱼用什么饵")[0] == ("largemouth-bass", "spotted-bass", "guadalupe-bass")
    assert split_species("淡水鼓鱼好吃吗")[0] == ("freshwater-drum",)
    # The longer unguided name is blanked first: red drum is not freshwater drum.
    assert split_species("红鼓鱼用什么饵")[0] == ()
    assert split_species("黄金鲈怎么钓")[0] == ()
    assert split_species("小口黑鲈怎么钓")[0] == ("smallmouth-bass",)


def test_routing_still_keeps_other_fish_out_even_if_their_passage_is_closest():
    # The embedder says a shad passage is the best match; the question is
    # about bass, so the shad passage may not appear.
    r = _hybrid({"鲈鱼用什么饵": "gizzard-shad#bait_for"})
    slugs = {h.passage.species_slug for h in r.search("鲈鱼用什么饵")}
    assert "gizzard-shad" not in slugs
    assert slugs <= {"largemouth-bass", "spotted-bass", "guadalupe-bass", "all-fish"}


def test_an_unguided_fish_is_not_covered_whatever_the_embedder_says():
    r = _hybrid({"红鼓鱼用什么饵": "freshwater-drum#live_baits"})
    assert r.search("红鼓鱼用什么饵") == []


def test_off_topic_questions_the_embedder_finds_nothing_for_stay_rejected():
    r = _hybrid({})
    assert r.search("红烧肉怎么做") == []
    assert r.search("what is the capital of france") == []


def test_a_fish_name_alone_still_gets_the_beginner_sections():
    r = _hybrid({})
    assert _ids(r.search("tell me about bluegill")) == _ids(bm25_retriever().search("tell me about bluegill"))
    assert _ids(r.search("蓝鳃太阳鱼"))[0].startswith("bluegill#")


def test_a_passage_both_rankers_agree_on_wins():
    q = "how do I tie a palomar knot"
    r = _hybrid({q: "all-fish#knot-palomar"})
    assert _ids(r.search(q))[0] == "all-fish#knot-palomar"


def test_the_model_never_decides_a_question_is_about_fishing():
    # Even with the embedder pointing an off-topic question straight at a
    # passage, the rule-based gate turns it away (ADR 0025: cosines can't
    # separate fishing from off-topic questions for this model).
    r = _hybrid({"how long to cook chicken": "all-fish#care-eating-safely", "金鱼怎么养": "bluegill#overview"})
    assert r.search("how long to cook chicken") == []
    assert r.search("金鱼怎么养") == []


def test_an_english_question_keyword_search_finds_nothing_for_stays_not_covered():
    r = _hybrid({"what is the lifespan of a white crappie in an aquarium": "white-crappie#habits"})
    assert r.search("what is the lifespan of a white crappie in an aquarium") == []


def test_a_broad_how_to_question_gets_bait_lures_a_rig_and_when():
    want = ["largemouth-bass#live_baits", "largemouth-bass#lures", "largemouth-bass#setup-1",
            "largemouth-bass#where_and_when"]
    for retriever in (bm25_retriever(), _hybrid({})):
        for q in ("how can i fish a bass", "teach me to catch a bass", "鲈鱼怎么钓"):
            assert _ids(retriever.search(q)) == want, q


@pytest.mark.skipif(not (MODEL_DIR / "tokenizer.json").exists(), reason="embedding model not installed")
def test_the_real_model_answers_a_chinese_question():
    embedder = load_embedder()
    assert embedder is not None
    r = HybridRetriever(bm25_retriever(), embedder)
    assert "all-fish#care-dispatch-bleed" in _ids(r.search("怎么杀鱼最人道"))
    assert r.search("红烧肉怎么做") == []


def test_a_states_view_of_the_hybrid_index_reuses_the_vectors():
    from app.services.rag import regional

    r = _hybrid({"is it legal to use a small bass as live bait": "all-fish#bait_rules-ga"})
    view = regional.for_state(r, "GA")
    assert isinstance(view, HybridRetriever)
    assert len(view.passages) == len(view._vecs) < len(r.passages)
    assert {p.region for p in view.passages} == {"all", "GA"}
    ids = _ids(view.search("is it legal to use a small bass as live bait"))
    assert "all-fish#bait_rules-ga" in ids and "all-fish#bait_rules" not in ids


def test_semantic_search_is_the_default_and_missing_model_stops_startup(monkeypatch):
    """ADR 0029: no quiet fallback to keyword-only in a deployment."""
    from app.core.config import Settings
    from app.services.rag import embeddings, retriever

    monkeypatch.delenv("RAG_SEMANTIC", raising=False)
    assert Settings().rag_semantic == "on"

    monkeypatch.setattr(embeddings, "load_embedder", lambda *a, **k: None)
    monkeypatch.setattr(retriever, "_default", None)
    monkeypatch.setattr(
        "app.core.config.get_settings", lambda: Settings(rag_semantic="on")
    )
    with pytest.raises(RuntimeError, match="fetch_embedding_model"):
        retriever.default_retriever()
    monkeypatch.setattr(retriever, "_default", None)
