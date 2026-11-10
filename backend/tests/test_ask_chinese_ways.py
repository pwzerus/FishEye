"""How people really ask, in Chinese: matched to the handbook's topics (zh_search.ZhAsks)."""
from __future__ import annotations

import pytest

from app.knowledge.angling_handbook import TOPICS
from app.knowledge.translations import table
from app.services.rag import site_help, zh, zh_search


def test_every_way_of_asking_is_about_a_real_topic():
    ids = {t.id for t in TOPICS}
    for topic in table("topic_asks", "zh"):
        assert topic in ids or any(i.startswith(f"{topic}-") for i in ids), topic


def test_the_lists_are_not_empty_and_have_no_repeats():
    ways = table("topic_asks", "zh")
    for topic, phrases in ways.items():
        assert phrases and len(phrases) == len(set(phrases)), topic
    others = table("not_fishing", "zh")
    assert len(others) > 100 and len(others) == len(set(others))


@pytest.mark.parametrize(
    "question,topic",
    [
        ("一直没口怎么办", "trouble-no-bites"),
        ("线用几号的", "tackle-line"),
        ("两根线怎么接", "knot-joining"),
        ("气压低鱼还吃口吗", "cond-fronts"),
        ("大嘴鲈和小嘴鲈怎么分", "id-black-bass"),
        ("鱼钩吞进肚子了怎么取", "care-deep-hook"),
    ],
)
def test_a_way_of_asking_finds_its_topic(question, topic):
    assert zh_search.asks().best(question)[0].topic == topic


@pytest.mark.parametrize("question", ["一直没口怎么办", "线用几号的", "气压低鱼还吃口吗", "需要穿救生衣吗", "软虫怎么绑"])
def test_how_people_ask_counts_as_a_fishing_question(question):
    assert zh_search.is_asked_about(question)


@pytest.mark.parametrize(
    "question",
    ["夏天穿什么衣服", "孕妇能吃什么", "两根电线怎么接", "数据线断了怎么办", "水果能放多久", "虾怎么做好吃", "线上课程怎么报名"],
)
def test_being_shaped_like_one_isnt_enough(question):
    assert not zh_search.is_asked_about(question)


def test_rod_is_spelled_both_ways():
    assert zh.normalized("鱼杆多长合适") == "鱼竿多长合适"
    assert zh.normalized("抛杆怎么抛") == "抛竿怎么抛"
    assert zh.normalized("杠杆原理") == "杠杆原理"


@pytest.mark.parametrize(
    "question,expected",
    [
        ("这个网站怎么分享渔获", site_help.SHARE),
        ("为什么我的分享按钮是灰的", site_help.SHARE),
        ("怎么上传钓到的鱼", site_help.SHARE),
        ("how do I share a catch", site_help.SHARE),
        ("拍照识别准吗", site_help.PHOTO),
        ("相机拍了说没有鱼是怎么回事", site_help.PHOTO),
        ("怎么看附近的湖", site_help.FIND),
        ("你是谁", site_help.ABOUT),
        ("FishEye 怎么用", site_help.ABOUT),
        ("忘记密码怎么办", site_help.ACCOUNT),
        ("这个网站要收费吗", site_help.PRICE),
        ("找不到我常去的湖怎么办", site_help.MISSING_WATER),
        ("别人能看到我的钓点吗", site_help.PRIVACY),
        ("怎么删除我发的渔获", site_help.EDIT_CATCH),
        ("为什么照片传不上去", site_help.UPLOAD),
        ("怎么换语言", site_help.LANGUAGE),
        ("地图打不开怎么办", site_help.MAP_TROUBLE),
        ("怎么订阅提醒", site_help.ALERTS),
    ],
)
def test_questions_about_the_site(question, expected):
    assert site_help.topic(question) == expected


@pytest.mark.parametrize(
    "question",
    ["鱼钩怎么绑", "怎么看湖里有没有鱼", "what bait do I use", "how do I find fish in a lake", "catch and release tips", "一直没口怎么办", "订阅式渔具盒适合当礼物吗",
     "how do I add weight to catch more fish", "这个湖收费吗", "怎么找钓点", "怎么晒鱼干", "remove the hook after a catch"],
)
def test_fishing_questions_are_left_for_the_guides(question):
    assert site_help.topic(question) is None


def test_every_site_answer_exists_in_english_and_chinese():
    from app.services.rag import replies

    names = [v for k, v in vars(site_help).items() if k.isupper() and isinstance(v, str)]
    for name in names:
        assert replies.site_help(name, "en")
        assert replies.site_help(name, "zh")
        assert replies.site_help(name, "ko")  # falls back to English where there's no translation
