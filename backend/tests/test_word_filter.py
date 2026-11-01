"""Slurs stay out of what other people read (services/word_filter.py)."""
from __future__ import annotations

import pytest

from app.knowledge import error_text
from app.services.word_filter import blocked_word
from tests.conftest import signup
from tests.test_pins_api import create


@pytest.mark.parametrize(
    "text",
    [
        "nigger", "NIGGERS", "you nigga", "n1gg3r", "n!gger", "n*gger", "niiiigger", "n i g g e r", "n.i.g.g.e.r",
        "n-i-g-g-e-r", "ｎｉｇｇｅｒ", "nіgger",  # fullwidth; a Cyrillic і
        "nig\u200bger",  # an invisible space
        "sandnigger", "fag", "f a g", "f@g", "fags", "faggot", "f4gg0t", "spic", "sp1c", "chinks", "kikes",
        "maricón", "MARICON", "retarded", "tranny", "cunt", "c*nt", "KKK", "Sieg Heil!", "porch monkey",
        "a squaw", "squaw trash",  # not a place's name
        "黑鬼", "黑 鬼", "你个黑鬼", "支那人", "ﾆｶﾞｰ", "ニガー", "깜둥이", "깜 둥 이", "병신같네", "ガイジ",
    ],
)
def test_slurs_are_found_through_the_usual_disguises(text):
    assert blocked_word(text)


@pytest.mark.parametrize(
    "text",
    [
        # words that hold one, or look like one
        "Niger River", "sniggering at my cast", "a niggardly limit", "niggling doubt", "spicy cajun catfish",
        "Scunthorpe", "Japan", "Japanese knotweed", "raccoon tracks", "Coon Lake", "Caught on white Power Bait",
        "pollack", "woop woop", "Kike Hernández", "pez negro", "black crappie", "draghead",
        "4lb bass on a 5in worm", "Van Dyke Lake", "Dykes Pond",
        # old place names, near misses from the 250,000 names on file (2026-10-31)
        "Squaw Creek", "Old Squaw Lake", "Squaw Town Creek", "Big Injun Lake", "Chinaman Lake", "Darky Branch",
        "Darkies Creek", "Knigga Run", "Polack Lake", "Dago Creek", "Beaner Lake", "Fag Lake", "Redskin Creek",
        "Gook Creek",
        # pieces of common words in Chinese, Japanese and Korean
        "玉米棒子做饵", "ガイジンの釣り人", "シナモン", "おかまでご飯", "물병 신발", "새끼 물고기 방류", "니 거야", "튀기면 맛있다",
        "", None,
    ],
)
def test_names_and_words_people_really_write_pass(text):
    assert blocked_word(text) is None


def test_a_display_name_with_a_slur_is_refused(make_client):
    c = make_client()
    resp = c.post("/api/auth/register", json={"email": "a@example.com", "password": "tight-lines-42", "display_name": "n1gger joe"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "That name includes a word FishEye doesn't allow."
    signup(c, email="b@example.com", name="Joe")
    assert c.patch("/api/auth/me", json={"display_name": "Joe the f.a.g"}).status_code == 422
    assert c.patch("/api/auth/me", json={"display_name": "Joe at Squaw Creek"}).status_code == 200


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"title": "Caught by a k i k e s"}, "The title includes a word FishEye doesn't allow."),
        ({"note": "Some 黑鬼 was fishing here"}, "The notes include a word FishEye doesn't allow."),
        ({"species_other": "spic fish"}, "The fish's name includes a word FishEye doesn't allow."),
    ],
)
def test_a_catch_with_a_slur_is_refused_in_the_readers_language(make_client, fields, message):
    c = make_client()
    signup(c)
    resp = create(c, **fields)
    assert resp.status_code == 422 and resp.json()["detail"] == message
    c.cookies.set(error_text.LANG_COOKIE, "zh")
    assert create(c, **fields).json()["detail"] == error_text.TEXT[message]["zh"]


def test_invisible_characters_are_taken_out_of_a_catch(make_client):
    c = make_client()
    signup(c)
    # A right-to-left override would show this backwards, as the slur.
    pin = create(c, title="Big \u202ereggin\u202c bass", note="Line one\nline\u200b two").json()
    assert pin["title"] == "Big reggin bass" and pin["note"] == "Line one\nline two"
    # Zero-width spaces would make a title that looks empty.
    assert create(c, title="\u200b\u200b\u200b\u200b").status_code == 422
    # Emoji keep their joiners.
    assert create(c, title="Family day \U0001F468\u200d\U0001F466").json()["title"].endswith("\u200d\U0001F466")


def test_an_edit_cant_add_one_either(make_client):
    c = make_client()
    signup(c)
    pin = create(c, title="Squaw Creek crappie").json()
    assert c.patch(f"/api/pins/{pin['id']}", json={"title": "retards everywhere"}).status_code == 422
    assert c.get(f"/api/pins/{pin['id']}").json()["title"] == "Squaw Creek crappie"
