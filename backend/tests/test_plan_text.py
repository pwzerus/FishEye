"""Today's plan in Chinese, Spanish, Korean and Japanese (knowledge/plan_text.py)."""
from __future__ import annotations

import pytest

from app.knowledge import plan_text
from app.knowledge.species_guides import get_guide
from app.services import fishing_plan as fp


def cond(**over) -> fp.Conditions:
    base = dict(wind_mph=12.0, wind_from="SE", wind_text="10 to 15 mph", sky="cloudy", forecast_text="Mostly Cloudy",
                rain_chance=None, temperature=68.0, low_light=True, light_word="dawn", front_drop_f=None)
    return fp.Conditions(**{**base, **over})


def every_plan_sentence() -> set[str]:
    """Each lure, bait and reason the plan can say, with the light word as a
    placeholder where it changes."""
    out: set[str] = {"A standard choice for this fish.", "A standard bait for this fish."}
    for tackle in fp.TACKLE.values():
        for rule in (*tackle.lures, *tackle.baits):
            out.add(fp._display(rule.pick))
            out.add(rule.why(cond(light_word="{light}")) if callable(rule.why) else rule.why)
        for name, why in (*tackle.lure_fallback, *tackle.bait_fallback):
            out.update((fp._display(name), why))
        if tackle.lure_note:
            out.add(tackle.lure_note)
    return out


@pytest.mark.parametrize("lang", plan_text.LANGS)
def test_every_plan_sentence_is_translated(lang):
    missing = sorted(s for s in every_plan_sentence() if s not in plan_text.TEXT[lang])
    assert missing == [], f"untranslated in {lang}: {missing[:5]}"
    unused = sorted(set(plan_text.TEXT[lang]) - every_plan_sentence())
    assert unused == [], f"translations for sentences the plan no longer says: {unused[:5]}"


def test_the_light_word_is_translated_inside_a_sentence():
    english = "Low light at dusk: bass come up and hit surface lures."
    assert plan_text.tr(english, "zh") == "黄昏光线暗：黑鲈会上浮攻击水面拟饵。"
    assert plan_text.tr(english, "es").startswith("Poca luz al atardecer")
    assert plan_text.tr(english, "en") == english
    assert plan_text.tr("Something new.", "zh") == "Something new."
    assert plan_text.tr(english, "ja") == "夕暮れは光が弱く、バスが浮いてきてトップウォーターに出ます。"
    assert plan_text.tr(english, "ko") == "해 질 녘에는 빛이 약해서 배스가 떠올라 탑워터 루어를 공격해요."


def test_a_plan_in_chinese_and_spanish():
    bass = get_guide("Largemouth Bass")
    zh = fp.tackle_for(bass, cond(), "zh")
    assert all(p["name"] in plan_text.TEXT["zh"].values() for p in zh["lures"])
    where = fp.where_to_fish(cond(), "zh")
    assert where["shore"] == "NW" and where["text"].startswith("试试西北岸")
    assert fp.where_to_fish(cond(), "es")["text"].startswith("Prueba la orilla noroeste")
    assert fp._conditions_line(cond(), "zh") == "68°F，大部多云，东南风 10–15 英里/小时"
    assert fp._conditions_line(cond(), "es") == "68°F, mayormente nublado, viento del sureste 10 a 15 mph"
    notes = fp.heads_up(cond(wind_mph=28, front_drop_f=14.0, rain_chance=70, sky="rain"), "es")
    assert notes[0].startswith("Viento de hasta 28 mph") and "14°F" in notes[1]
    # Korean and Japanese put the speed after 시속 / 時速, as they write it,
    # and name the bank with a compass word (no particle that changes with it).
    assert fp._conditions_line(cond(), "ko") == "68°F, 구름많음, 남동풍 시속 10~15마일"
    assert fp._conditions_line(cond(), "ja") == "68°F、曇りがち、南東の風 時速10〜15マイル"
    assert fp.where_to_fish(cond(), "ko")["text"].startswith("북서쪽 물가를 노려 보세요. 그 시간에는 남동쪽에서")
    assert fp.where_to_fish(cond(), "ja")["text"].startswith("北西岸を試してみましょう。その時間は南東から")
    assert plan_text.wind_speed("10 mph", "ja") == "時速10マイル"
    assert plan_text.wind_speed("Calm", "ko") == "Calm"
    # English is unchanged.
    assert fp.where_to_fish(cond())["text"].startswith("Try the NW bank")
