"""Japanese questions.

The guides are English, and Ask's search is decided by English words
(retriever.py). Like a Spanish question (es.py), a Japanese one is put into
those words first: "ブルーギルの針のサイズは？" is searched as "bluegill hook
size". The answer quotes the guides, with FishEye's own sentences in
Japanese (replies.py).

Japanese has no spaces, so the glossary matches substrings, longest first,
as Chinese does (zh.py), and what it doesn't know is dropped: leftover kana
or kanji never reach the Chinese rules (a kanji such as 湖 is both). A
question with any kana is Japanese; Chinese has none. The glossary is the
words Japanese anglers use (エサ, ウキ, ガン玉, おかっぱり, 持ち帰り),
written by hand.
"""
from __future__ import annotations

import re
import unicodedata

from app.knowledge import jurisdictions

KANA_RE = re.compile(r"[぀-ヿㇰ-ㇿ]")

# US states as Japanese writes them, by postal code (frontend i18n/names.ts).
STATE_NAMES: dict[str, str] = {
    "AL": "アラバマ州", "AK": "アラスカ州", "AZ": "アリゾナ州", "AR": "アーカンソー州", "CA": "カリフォルニア州",
    "CO": "コロラド州", "CT": "コネチカット州", "DE": "デラウェア州", "DC": "ワシントンD.C.", "FL": "フロリダ州",
    "GA": "ジョージア州", "HI": "ハワイ州", "ID": "アイダホ州", "IL": "イリノイ州", "IN": "インディアナ州",
    "IA": "アイオワ州", "KS": "カンザス州", "KY": "ケンタッキー州", "LA": "ルイジアナ州", "ME": "メイン州",
    "MD": "メリーランド州", "MA": "マサチューセッツ州", "MI": "ミシガン州", "MN": "ミネソタ州", "MS": "ミシシッピ州",
    "MO": "ミズーリ州", "MT": "モンタナ州", "NE": "ネブラスカ州", "NV": "ネバダ州", "NH": "ニューハンプシャー州",
    "NJ": "ニュージャージー州", "NM": "ニューメキシコ州", "NY": "ニューヨーク州", "NC": "ノースカロライナ州",
    "ND": "ノースダコタ州", "OH": "オハイオ州", "OK": "オクラホマ州", "OR": "オレゴン州", "PA": "ペンシルベニア州",
    "RI": "ロードアイランド州", "SC": "サウスカロライナ州", "SD": "サウスダコタ州", "TN": "テネシー州",
    "TX": "テキサス州", "UT": "ユタ州", "VT": "バーモント州", "VA": "バージニア州", "WA": "ワシントン州",
    "WV": "ウェストバージニア州", "WI": "ウィスコンシン州", "WY": "ワイオミング州",
}

# Japanese phrase -> the English words the guides use for it.
GLOSSARY: dict[str, str] = {
    # fish
    "ラージマウスバス": "largemouth bass", "ラージマウス": "largemouth bass", "オオクチバス": "largemouth bass",
    "スモールマウスバス": "smallmouth bass", "スモールマウス": "smallmouth bass", "コクチバス": "smallmouth bass",
    "スポッテッドバス": "spotted bass", "グアダルーペバス": "guadalupe bass", "ホワイトバス": "white bass",
    "ストライプドバス": "striped bass", "ストライパー": "striped bass", "シマスズキ": "striped bass",
    "ハイブリッドストライプドバス": "hybrid striped bass", "ハイブリッド": "hybrid striped bass",
    "ブラックバス": "bass", "バス": "bass",
    "チャネルキャットフィッシュ": "channel catfish", "チャネルキャット": "channel catfish", "アメリカナマズ": "channel catfish",
    "ブルーキャットフィッシュ": "blue catfish", "ブルーキャット": "blue catfish",
    "フラットヘッドキャットフィッシュ": "flathead catfish", "フラットヘッド": "flathead catfish",
    "キャットフィッシュ": "catfish", "ナマズ": "catfish", "なまず": "catfish", "鯰": "catfish",
    "ホワイトクラッピー": "white crappie", "ブラッククラッピー": "black crappie", "クラッピー": "crappie",
    "ブルーギル": "bluegill", "レッドイヤーサンフィッシュ": "redear sunfish", "レッドイヤー": "redear sunfish",
    "サンフィッシュ": "sunfish",
    "ニジマス": "rainbow trout", "虹鱒": "rainbow trout", "レインボートラウト": "rainbow trout",
    "ブラウントラウト": "brown trout", "トラウト": "trout", "マス": "trout", "鱒": "trout",
    "フレッシュウォータードラム": "freshwater drum", "ドラム": "freshwater drum",
    "コイ": "carp", "鯉": "carp",
    "ギザードシャッド": "gizzard shad", "スレッドフィンシャッド": "threadfin shad", "シャッド": "shad",
    "ウォールアイ": "walleye", "ノーザンパイク": "northern pike", "パイク": "northern pike",
    "イエローパーチ": "yellow perch", "アリゲーターガー": "gar", "ガーパイク": "gar", "ティラピア": "tilapia",
    # bait
    "生きエサ": "live bait", "生き餌": "live bait", "活きエサ": "live bait", "活き餌": "live bait",
    "練りエサ": "dough bait", "練り餌": "dough bait", "においエサ": "stink bait", "臭いエサ": "stink bait",
    "寄せエサ": "chum", "撒きエサ": "chum",
    "エサ": "bait", "えさ": "bait", "餌": "bait",
    "ドバミミズ": "nightcrawler", "ミミズ": "worm nightcrawler", "みみず": "worm nightcrawler",
    "ミールワーム": "mealworm", "ブドウムシ": "wax worm", "コオロギ": "cricket", "バッタ": "grasshopper",
    "ザリガニ": "crayfish", "エビ": "shrimp", "えび": "shrimp", "海老": "shrimp",
    "鶏レバー": "chicken liver", "レバー": "liver", "チーズ": "cheese", "ソーセージ": "hot dog",
    "コーン": "corn", "トウモロコシ": "corn", "とうもろこし": "corn", "切り身": "cut bait",
    "小魚": "minnow minnows", "ミノー": "minnow",
    # lures and tackle
    "ルアー": "lure lures", "スピナーベイト": "spinnerbait", "スピナー": "spinner", "スプーン": "spoon",
    "クランクベイト": "crankbait", "バイブレーション": "lipless crankbait", "トップウォーター": "topwater",
    "ポッパー": "popper", "ジグヘッド": "jighead", "メタルジグ": "slab spoon", "ジグ": "jig",
    "ジャークベイト": "jerkbait", "スイムベイト": "swimbait", "ワーム": "soft plastic worm",
    "ネドリグ": "ned rig", "ダウンショット": "drop shot",
    "サークルフック": "circle hook", "針のサイズ": "hook size", "針の大きさ": "hook size", "針の号数": "hook size",
    "釣り針": "hook", "フック": "hook", "針": "hook",
    "釣り竿": "rod", "ロッド": "rod", "竿": "rod",
    "スピニングリール": "spinning reel", "ベイトリール": "baitcasting reel", "スピンキャスト": "spincast", "リール": "reel",
    "peライン": "braid line", "フロロカーボン": "fluorocarbon", "フロロ": "fluorocarbon", "ナイロン": "monofilament",
    "釣り糸": "line", "道糸": "line", "ライン": "line", "糸": "line",
    "ウキ": "bobber", "浮き": "bobber", "ガン玉": "split shot", "オモリ": "sinker", "おもり": "sinker", "錘": "sinker",
    "サルカン": "swivel", "スイベル": "swivel", "リーダー": "leader", "ハリス": "leader",
    "クリンチノット": "clinch knot", "パロマーノット": "palomar knot",
    "結び方": "how tie knot", "結ぶ": "tie", "結び": "knot", "ノット": "knot",
    "ドラグ": "drag", "タモ網": "net", "たも網": "net", "タモ": "net", "網": "net",
    # doing it
    "釣り方": "how catch", "釣るには": "how catch", "釣る方法": "how catch",
    "釣れる": "catch", "釣れ": "catch", "釣る": "catch", "釣った": "catch", "釣り": "fishing", "釣": "catch",
    "投げ方": "how cast", "キャスト": "cast", "投げる": "cast",
    "さばき方": "clean fillet", "さばく": "clean", "捌く": "clean", "三枚におろす": "fillet", "おろし方": "fillet",
    "下処理": "clean", "皮をはぐ": "skin", "皮を剥ぐ": "skin", "ウロコ": "scale", "鱗": "scale",
    "料理": "cook", "調理": "cook", "焼く": "cook", "揚げる": "fry", "冷凍": "freeze",
    "リリース": "release", "逃がす": "release", "持ち帰り制限": "daily limit", "持ち帰り尾数": "daily limit",
    "持ち帰": "keep", "キープ": "keep", "血抜き": "bleed", "締め方": "kill", "締める": "kill",
    "測り方": "measure", "測る": "measure", "計る": "measure",
    # rules and safety
    "釣りライセンス": "fishing license", "ライセンス": "license", "遊漁券": "fishing license", "釣り免許": "fishing license",
    "免許": "license", "許可": "permit", "サイズ制限": "size limit", "制限": "limit", "リミット": "limit",
    "規則": "rules regulations", "ルール": "rules", "規制": "regulations", "法律": "law rules",
    "ライフジャケット": "life jacket", "救命胴衣": "life jacket", "何歳": "age", "年齢": "age",
    # where and when
    "おかっぱり": "bank shore", "オカッパリ": "bank shore", "岸釣り": "bank shore", "岸": "bank shore",
    "桟橋": "dock pier", "ダム湖": "reservoir", "貯水池": "reservoir", "湖": "lake",
    "小川": "creek", "河川": "river", "川": "river", "池": "pond",
    "夜釣り": "night", "夜": "night", "朝マズメ": "dawn morning", "朝まずめ": "dawn morning", "早朝": "dawn morning",
    "朝": "morning", "夕マズメ": "dusk evening", "夕まずめ": "dusk evening", "夕方": "evening",
    "冬": "winter", "夏": "summer", "春": "spring", "秋": "fall", "風": "wind", "雨": "rain", "前線": "front",
    "濁り": "muddy water", "水深": "depth deep", "深場": "deep", "深さ": "depth", "季節": "season", "時期": "season",
    "時間帯": "time", "産卵": "spawn",
    # asking
    "どうして": "why", "なぜ": "why", "どうやって": "how", "どうすれば": "how", "どう": "how",
    "何匹": "how many", "何尾": "how many", "何": "what", "なに": "what", "どんな": "what",
    "どこ": "where", "いつ": "when", "どれ": "which", "どの": "which",
    "いちばん": "best", "一番": "best", "おすすめ": "best", "ベスト": "best", "がいい": "good", "良い": "good",
    "簡単": "easy", "かんたん": "easy", "初心者": "beginner", "はじめて": "beginner", "初めて": "beginner",
    "子ども": "kid", "子供": "kid", "食べる": "eat", "食う": "eat", "使えば": "use", "使う": "use", "必要": "need",
}
# A state by its Japanese name, with or without 州, is the state's English
# name: what Ask's state rules read (jurisdictions.state_in_question).
for _code, _name in STATE_NAMES.items():
    _english = jurisdictions.JURISDICTIONS[_code].name.lower()
    GLOSSARY[_name.lower()] = _english
    if _name.endswith("州"):
        GLOSSARY.setdefault(_name[:-1], _english)

_PHRASES = sorted(GLOSSARY.items(), key=lambda kv: -len(kv[0]))
_NOT_ENGLISH = re.compile(r"[^a-z0-9 ]+")


def is_japanese(text: str) -> bool:
    return bool(text) and bool(KANA_RE.search(text))


def to_english(text: str) -> str:
    """The question in the words the guides use, and nothing else: ASCII it
    already had (a lake's name, "PE") stays, Japanese the glossary doesn't
    know is dropped."""
    out = unicodedata.normalize("NFKC", text).lower()
    for ja, english in _PHRASES:
        if ja in out:
            out = out.replace(ja, f" {english.lower()} ")
    return " ".join(_NOT_ENGLISH.sub(" ", out).split())
