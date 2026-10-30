"""What Ask says in its own words, in the asker's language (en, zh, es, ko, ja).

The guides it quotes are English. Its own sentences (the line before the
passages, and the three kinds of "not covered", docs/adr/0026) are in the
language of the question: Chinese for a Chinese question, Spanish, Korean
or Japanese for one in those; for an English question, the site's language
(someone reading the site in Spanish can still type "crappie bait").
Japanese is told apart from Chinese by its kana, so it is asked first.
"""
from __future__ import annotations

from app.knowledge import jurisdictions
from app.services.rag import es, ja, ko
from app.services.rag.zh import has_chinese

LANGS = ("en", "zh", "es", "ko", "ja")

# "No guide for that fish" when the fish's name can't be read back.
THAT_FISH = {"en": "that fish", "zh": "这种鱼", "es": "ese pez", "ko": "그 물고기", "ja": "その魚"}

# Spanish names of the states whose name differs from the English one.
ES_STATE_NAMES = {
    "DC": "Distrito de Columbia", "HI": "Hawái", "LA": "Luisiana", "MI": "Míchigan", "MS": "Misisipi",
    "MO": "Misuri", "NH": "Nuevo Hampshire", "NJ": "Nueva Jersey", "NM": "Nuevo México", "NY": "Nueva York",
    "NC": "Carolina del Norte", "ND": "Dakota del Norte", "OR": "Oregón", "PA": "Pensilvania",
    "SC": "Carolina del Sur", "SD": "Dakota del Sur", "WV": "Virginia Occidental",
}


def reply_lang(question: str, site_lang: str | None) -> str:
    if ja.is_japanese(question):
        return "ja"
    if ko.is_korean(question):
        return "ko"
    if has_chinese(question):
        return "zh"
    if es.is_spanish(question):
        return "es"
    return site_lang if site_lang in LANGS else "en"


def _state_name(code: str, lang: str) -> str:
    j = jurisdictions.JURISDICTIONS[code]
    if lang == "zh":
        return jurisdictions.ZH_STATE_NAMES.get(code, j.name)
    if lang == "es":
        return ES_STATE_NAMES.get(code, j.name)
    if lang == "ko":
        return ko.STATE_NAMES.get(code, j.name)
    if lang == "ja":
        return ja.STATE_NAMES.get(code, j.name)
    return j.name


def _covered(lang: str) -> str:
    names = [_state_name(c.code, lang) for c in jurisdictions.covered()]
    if lang in ("zh", "ja"):
        return "、".join(names)
    if lang == "ko":
        return ", ".join(names)
    if lang == "es":
        return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"
    return jurisdictions.covered_names()


def coverage(lang: str) -> str:
    if lang == "ko":
        return (
            "FishEye에는 민물고기 19종의 가이드(대부분 미국 전역에 사는 어종으로, 먹이, 사는 곳, 잘 먹히는 미끼와 "
            "그 이유, 낚싯대와 릴 구성, 손질과 요리법)와, 미끼, 루어, 장비, 매듭, 캐스팅, 날씨와 물, 안전, 잡은 "
            f"물고기 다루기에 대한 핸드북이 있어요. 낚시 규정은 지금까지 {_covered(lang)}의 규정을 정리했고, 물고기가 "
            "사는 곳의 예시는 텍사스주 것이 많아요. 둘 다 주마다 달라요."
        )
    if lang == "ja":
        return (
            "FishEyeには、淡水魚19種のガイド（多くは全米にいる魚で、何を食べ、どこにいるか、効くエサとその理由、"
            "竿とリールの組み合わせ、さばき方と料理）と、エサ、ルアー、道具、結び方、投げ方、天気と水、安全、"
            f"釣った魚の扱いについてのハンドブックがあります。釣りの規則は今のところ{_covered(lang)}の分を掲載していて、"
            "魚の生息場所の例にはテキサス州のものが多くあります。どちらも州によって違います。"
        )
    if lang == "zh":
        return (
            "FishEye 现有十九种淡水鱼的指南（大多在全美都有：吃什么、住在哪、什么饵管用和为什么、竿轮搭配、"
            "怎么处理和烹饪），以及一本关于饵料、拟饵、装备、绳结、抛投、天气水情、安全和处理渔获的手册。"
            f"钓鱼规定目前整理了{_covered(lang)}，很多栖息地的例子来自得克萨斯州；这两样都因州而异。"
        )
    if lang == "es":
        return (
            "FishEye tiene guías de diecinueve peces de agua dulce, casi todos presentes en todo EE. UU. (qué "
            "comen, dónde viven, qué carnadas funcionan y por qué, equipos de caña y carrete, y cómo limpiarlos "
            "y cocinarlos), y un manual sobre carnadas, señuelos, equipo, nudos, lances, clima y agua, seguridad "
            f"y cuidado de tu captura. Por ahora las reglas de pesca están escritas para {_covered(lang)}, y "
            "muchos ejemplos de dónde viven los peces son de Texas; ambas cosas cambian según el estado."
        )
    return (
        "FishEye covers nineteen freshwater fish, most of them found across the U.S. (what each one "
        "eats, where it lives, which baits work and why, rod-and-reel setups, and how to clean and "
        "cook it) plus a handbook on baits, lures, tackle, knots, casting, weather and water, safety "
        f"and caring for your catch. Fishing rules are written for {jurisdictions.covered_names()} so "
        "far, and many examples of where fish live are Texas's; both differ by state."
    )


def passages_intro(lang: str) -> str:
    if lang == "zh":
        return "以下是 FishEye 指南里的相关内容（原文为英文）："
    if lang == "es":
        return "Esto es lo que dicen las guías de FishEye (en inglés):"
    if lang == "ko":
        return "FishEye 가이드에는 이렇게 나와 있어요(원문은 영어예요):"
    if lang == "ja":
        return "FishEyeのガイドには、こう書かれています（原文は英語）："
    return "Here's what the FishEye guides say:"


def no_match(lang: str) -> str:
    if lang == "zh":
        return f"FishEye 的指南还没有覆盖这个问题。{coverage(lang)}可以问问这些方面。"
    if lang == "es":
        return f"Las guías de FishEye todavía no cubren eso. {coverage(lang)} Prueba preguntar sobre algo de eso."
    if lang == "ko":
        return f"FishEye 가이드에는 아직 그 내용이 없어요. {coverage(lang)} 이 중에서 물어봐 주세요."
    if lang == "ja":
        return f"FishEyeのガイドには、まだその内容がありません。{coverage(lang)}このどれかについて聞いてみてください。"
    return f"The FishEye guides don't cover that yet. {coverage(lang)} Try asking about one of those."


def off_topic(lang: str) -> str:
    if lang == "zh":
        return f"这看起来不像钓鱼问题，或者我没看懂。{coverage(lang)}试着说出一种鱼、一种饵或一件装备，用中文、英文、西班牙语、韩语或日语都行。"
    if lang == "es":
        return (
            f"Eso no parece una pregunta de pesca, o no la entendí. {coverage(lang)} Prueba nombrar un pez, "
            "una carnada o un equipo, en español, inglés, chino, coreano o japonés."
        )
    if lang == "ko":
        return (
            f"낚시 질문이 아닌 것 같아요. 아니면 제가 잘 이해하지 못했어요. {coverage(lang)} 어종, 미끼, 장비 이름을 "
            "넣어서 한국어, 영어, 중국어, 스페인어, 일본어로 물어보세요."
        )
    if lang == "ja":
        return (
            f"釣りの質問ではないようです。あるいは、うまく理解できませんでした。{coverage(lang)}魚、エサ、道具の名前を"
            "入れて、日本語、英語、中国語、スペイン語、韓国語で質問してください。"
        )
    return (
        "That doesn't look like a fishing question to me — or I didn't understand it. "
        f"{coverage(lang)} Try naming a fish, a bait or a piece of tackle, in English, Chinese, Spanish, Korean or Japanese."
    )


def unguided_fish(name: str, lang: str) -> str:
    if lang == "zh":
        return f"FishEye 还没有{name}的指南，所以关于这种鱼说什么都只是猜测。{coverage(lang)}"
    if lang == "es":
        return f"FishEye todavía no tiene guía para {name}, así que cualquier cosa sobre ese pez sería adivinar. {coverage(lang)}"
    if lang == "ko":
        return f"FishEye에는 아직 {name} 가이드가 없어서, 그 물고기에 대해 답하면 짐작일 뿐이에요. {coverage(lang)}"
    if lang == "ja":
        return f"FishEyeにはまだ{name}のガイドがないので、その魚について答えても推測になってしまいます。{coverage(lang)}"
    return f"FishEye has no guide for {name} yet, so anything it told you about that fish would be guesswork. {coverage(lang)}"


def other_state(state: str, lang: str) -> str:
    if lang == "zh":
        return jurisdictions.other_state_answer_zh(state)
    if lang == "ko":
        return _other_state_ko(state)
    if lang == "ja":
        return _other_state_ja(state)
    if lang != "es":
        return jurisdictions.other_state_answer(state)
    j = jurisdictions.JURISDICTIONS[state]
    name = _state_name(state, lang)
    agency = j.agency_short or f"la agencia de pesca y vida silvestre de {name}"
    if j.covered:
        return (
            f"FishEye ya escribió algunas reglas de pesca de {name}, pero no la de esta pregunta. Revisa las "
            f"reglas vigentes con {agency} antes de pescar. Todo lo de cómo pescar, manejar y cocinar un pez "
            "funciona igual en cualquier lugar."
        )
    return (
        f"Esa es una pregunta sobre las reglas de pesca de {name}, y FishEye todavía no las ha escrito (por ahora "
        f"revisó las reglas de {_covered(lang)}). Las reglas de licencias, límites, carnada y lanchas cambian de un "
        f"estado a otro, así que revisa las vigentes con {agency}. Todo lo de cómo pescar, manejar y cocinar un pez "
        "funciona igual en cualquier lugar."
    )


def _other_state_ko(state: str) -> str:
    j = jurisdictions.JURISDICTIONS[state]
    name = _state_name(state, "ko")
    agency = j.agency_short or f"{name} 어류·야생동물 기관"
    same = "물고기를 잡고 다루고 요리하는 방법은 어디서나 똑같아요."
    if j.covered:
        return (
            f"FishEye에 {name}의 낚시 규정이 일부 정리되어 있지만, 이 질문에 해당하는 규정은 아직 없어요. "
            f"낚시하기 전에 {agency}에서 최신 규정을 확인하세요. {same}"
        )
    return (
        f"{name}의 낚시 규정에 대한 질문인데, FishEye는 아직 그 규정을 정리하지 않았어요(지금까지 "
        f"{_covered('ko')}의 규정을 확인했어요). 면허, 한도, 미끼, 보트 규정은 주마다 다르니 {agency}에서 "
        f"최신 규정을 확인하세요. {same}"
    )


def _other_state_ja(state: str) -> str:
    j = jurisdictions.JURISDICTIONS[state]
    name = _state_name(state, "ja")
    agency = j.agency_short or f"{name}の魚類野生生物局"
    same = "魚の釣り方、扱い方、料理の仕方は、どこでも同じです。"
    if j.covered:
        return (
            f"FishEyeは{name}の釣りの規則をいくつか掲載していますが、この質問の規則はまだありません。"
            f"釣りをする前に、{agency}で最新の規則を確認してください。{same}"
        )
    return (
        f"これは{name}の釣りの規則についての質問ですが、FishEyeはまだ掲載していません（今のところ"
        f"{_covered('ja')}の規則を確認済みです）。ライセンス、制限、エサ、ボートの規則は州ごとに違うので、"
        f"{agency}で最新の規則を確認してください。{same}"
    )
