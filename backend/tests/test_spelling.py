"""Misspelled fishing words on Ask (app/services/rag/spelling.py)."""
import pytest

from app.services.rag import spelling


@pytest.mark.parametrize(
    ("typed", "fixed"),
    [
        ("waht bate for catfsh", "waht bait for catfish"),
        ("how to catch crapie", "how to catch crappie"),
        ("bluegil hook size", "bluegill hook size"),
        ("largmouth lures", "largemouth lures"),
        ("do I need a lisense", "do I need a license"),
    ],
)
def test_a_misspelled_fishing_word_is_put_right(typed, fixed):
    assert spelling.fix(typed) == fixed


@pytest.mark.parametrize(
    "question",
    ["how do I cook pasta", "recommend a cartoon", "best basketball shoes", "what's the weather tomorrow", "钓鱼用什么饵", "12345"],
)
def test_other_words_are_left_alone(question):
    assert spelling.fix(question) == question


@pytest.mark.parametrize(
    "question",
    [
        "how is a fish measured for the length limit",  # "measure" used to replace it, and changed the results
        "tell me a story",
        "how to write a letter",
        "my father is proud of the truth",
        "best lunch near me",
        "hair salon prices",
        "finishing my homework",
        "a stranger at the door",
        "the capital of Spain",
        "a wire stripper",
    ],
)
def test_a_real_word_is_not_a_typo(question):
    assert spelling.fix(question) == question


@pytest.mark.parametrize(
    ("typed", "fixed"),
    [("wallye jigs", "walleye jigs"), ("best flourocarbon line", "best fluorocarbon line"), ("sturgen season", "sturgeon season")],
)
def test_swapped_and_dropped_letters_are_one_slip(typed, fixed):
    assert spelling.fix(typed) == fixed


def test_ask_answers_through_a_misspelling(client):
    body = client.post("/api/ask", json={"question": "waht bate for catfsh"}).json()
    assert body["answer_source"] == "passages"
    assert body["question"] == "waht bate for catfsh"  # shown as typed
