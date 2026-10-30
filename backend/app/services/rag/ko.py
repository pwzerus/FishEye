"""Korean questions.

Like a Spanish question (es.py), a Korean one is put into the English words
Ask's search is decided by before it is searched: "블루길 바늘 크기는요?" is
searched as "bluegill hook size". The answer quotes the guides, with
FishEye's own sentences in Korean (replies.py).

Korean writes its particles onto the word (블루길은, 미끼를), so the glossary
matches substrings, longest first, and what it doesn't know is dropped. A
few entries are there to be dropped: 찌개 (a stew) isn't a 찌 (a bobber),
방법 (a way) isn't a 법 (a law). The glossary is the words Korean anglers
use (찌, 좁쌀봉돌, 떡밥, 조과, 포 뜨기), written by hand.
"""
from __future__ import annotations

import re
import unicodedata

from app.knowledge import jurisdictions

HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")

# US states as Korean writes them (the National Institute of Korean
# Language's spellings), by postal code (frontend i18n/names.ts).
STATE_NAMES: dict[str, str] = {
    "AL": "앨라배마주", "AK": "알래스카주", "AZ": "애리조나주", "AR": "아칸소주", "CA": "캘리포니아주",
    "CO": "콜로라도주", "CT": "코네티컷주", "DE": "델라웨어주", "DC": "워싱턴 D.C.", "FL": "플로리다주",
    "GA": "조지아주", "HI": "하와이주", "ID": "아이다호주", "IL": "일리노이주", "IN": "인디애나주",
    "IA": "아이오와주", "KS": "캔자스주", "KY": "켄터키주", "LA": "루이지애나주", "ME": "메인주",
    "MD": "메릴랜드주", "MA": "매사추세츠주", "MI": "미시간주", "MN": "미네소타주", "MS": "미시시피주",
    "MO": "미주리주", "MT": "몬태나주", "NE": "네브래스카주", "NV": "네바다주", "NH": "뉴햄프셔주",
    "NJ": "뉴저지주", "NM": "뉴멕시코주", "NY": "뉴욕주", "NC": "노스캐롤라이나주", "ND": "노스다코타주",
    "OH": "오하이오주", "OK": "오클라호마주", "OR": "오리건주", "PA": "펜실베이니아주", "RI": "로드아일랜드주",
    "SC": "사우스캐롤라이나주", "SD": "사우스다코타주", "TN": "테네시주", "TX": "텍사스주", "UT": "유타주",
    "VT": "버몬트주", "VA": "버지니아주", "WA": "워싱턴주", "WV": "웨스트버지니아주", "WI": "위스콘신주",
    "WY": "와이오밍주",
}

# Korean phrase -> the English words the guides use for it ("" drops it).
GLOSSARY: dict[str, str] = {
    # not fishing, though they contain a fishing word
    "찌개": "", "방법": "", "시간": "time", "추천": "best",
    # fish
    "큰입배스": "largemouth bass", "큰입우럭": "largemouth bass", "라지마우스": "largemouth bass",
    "작은입배스": "smallmouth bass", "작은입우럭": "smallmouth bass", "스몰마우스": "smallmouth bass",
    "스포티드배스": "spotted bass", "스포티드 배스": "spotted bass", "과달루페배스": "guadalupe bass",
    "과달루페 배스": "guadalupe bass", "화이트배스": "white bass", "화이트 배스": "white bass",
    "스트라이프드배스": "striped bass", "스트라이프드 배스": "striped bass", "줄무늬농어": "striped bass",
    "스트라이퍼": "striped bass", "하이브리드": "hybrid striped bass", "블랙배스": "bass", "배스": "bass",
    "채널메기": "channel catfish", "채널 메기": "channel catfish", "찬넬동자개": "channel catfish",
    "블루메기": "blue catfish", "블루 메기": "blue catfish", "플랫헤드메기": "flathead catfish",
    "플랫헤드": "flathead catfish", "메기": "catfish",
    "화이트크래피": "white crappie", "화이트 크래피": "white crappie", "블랙크래피": "black crappie",
    "블랙 크래피": "black crappie", "크래피": "crappie", "크라피": "crappie",
    "블루길": "bluegill", "파랑볼우럭": "bluegill", "레드이어선피시": "redear sunfish", "레드이어": "redear sunfish",
    "선피시": "sunfish",
    "무지개송어": "rainbow trout", "브라운송어": "brown trout", "브라운 송어": "brown trout", "송어": "trout",
    "트라우트": "trout", "민물드럼": "freshwater drum", "드럼": "freshwater drum", "잉어": "carp",
    "기자드섀드": "gizzard shad", "기자드 섀드": "gizzard shad", "스레드핀섀드": "threadfin shad",
    "스레드핀 섀드": "threadfin shad", "섀드": "shad",
    "월아이": "walleye", "강꼬치고기": "northern pike", "노던파이크": "northern pike", "파이크": "northern pike",
    "옐로퍼치": "yellow perch", "틸라피아": "tilapia",
    # bait
    "생미끼": "live bait", "미끼": "bait", "떡밥": "dough bait", "밑밥": "chum", "집어제": "chum",
    "냄새 미끼": "stink bait", "줄지렁이": "worm", "지렁이": "worm worms nightcrawler", "나이트크롤러": "nightcrawler",
    "밀웜": "mealworm", "왁스웜": "wax worm", "귀뚜라미": "cricket", "메뚜기": "grasshopper", "가재": "crayfish",
    "새우": "shrimp", "닭 간": "chicken liver", "닭간": "chicken liver", "치즈": "cheese", "옥수수": "corn",
    "소시지": "hot dog", "핫도그": "hot dog", "토막": "cut bait", "미노우": "minnow minnows",
    "작은 물고기": "minnow minnows", "피라미": "minnow",
    # lures and tackle
    "루어": "lure lures", "스피너베이트": "spinnerbait", "스피너": "spinner", "스푼": "spoon",
    "크랭크베이트": "crankbait", "크랭크": "crankbait", "바이브레이션": "lipless crankbait",
    "탑워터": "topwater", "톱워터": "topwater", "포퍼": "popper", "지그헤드": "jighead",
    "메탈지그": "slab spoon", "메탈 지그": "slab spoon", "지그": "jig", "저크베이트": "jerkbait",
    "스윔베이트": "swimbait", "네드리그": "ned rig", "네드 리그": "ned rig", "다운샷": "drop shot",
    "웜": "soft plastic worm",
    "서클훅": "circle hook", "서클 훅": "circle hook", "바늘 크기": "hook size", "바늘 사이즈": "hook size",
    "바늘 호수": "hook size", "낚싯바늘": "hook", "바늘": "hook", "훅": "hook",
    "낚싯대": "rod", "낚시대": "rod", "로드": "rod",
    "스피닝 릴": "spinning reel", "스피닝릴": "spinning reel", "베이트 릴": "baitcasting reel",
    "베이트릴": "baitcasting reel", "베이트캐스팅": "baitcasting reel", "스핀캐스트": "spincast",
    "캐치 앤 릴리스": "catch and release", "릴리스": "release", "릴": "reel",
    "낚싯줄": "line", "낚시줄": "line", "원줄": "line", "라인": "line", "합사": "braid line",
    "플로로카본": "fluorocarbon", "카본": "fluorocarbon", "나일론": "monofilament",
    "좁쌀봉돌": "split shot", "봉돌": "sinker", "찌": "bobber", "도래": "swivel", "스위벨": "swivel",
    "쇼크리더": "leader", "목줄": "leader", "리더": "leader",
    "클린치": "clinch knot", "팔로마": "palomar knot", "매듭": "knot", "노트": "knot",
    "묶는": "tie", "묶어": "tie", "묶나": "tie", "드랙": "drag", "뜰채": "net",
    # doing it
    "낚는 법": "how catch", "낚는법": "how catch", "잡는 법": "how catch", "잡는법": "how catch",
    "잡으려면": "how catch", "낚으려면": "how catch",
    "낚시 면허": "fishing license", "낚시": "fishing",
    "낚는": "catch", "낚아": "catch", "낚으": "catch", "낚을": "catch",
    "잡는": "catch", "잡아": "catch", "잡히": "catch", "잡으": "catch", "잡을": "catch", "잡았": "catch",
    "캐스팅": "cast", "던지": "cast", "던져": "cast",
    "포 뜨기": "fillet", "포뜨기": "fillet", "포를 뜨": "fillet", "손질": "clean", "껍질": "skin", "비늘": "scale",
    "요리": "cook", "조리": "cook", "튀기": "fry", "튀김": "fry", "냉동": "freeze", "얼리": "freeze",
    "방생": "release", "놓아주": "release", "가져가": "keep", "가져갈": "keep", "보관": "keep",
    "피 빼기": "bleed", "피빼기": "bleed", "피를 빼": "bleed", "길이": "measure", "재는": "measure",
    # rules and safety
    "면허": "license", "라이선스": "license", "라이센스": "license", "허가증": "permit",
    "하루 한도": "daily limit", "일일 한도": "daily limit", "체장": "size limit", "크기 제한": "size limit",
    "한도": "limit", "마릿수": "limit", "규정": "rules regulations", "규칙": "rules", "법규": "law rules",
    "구명조끼": "life jacket", "몇 살": "age", "나이": "age",
    # where and when
    "물가": "bank shore", "연안": "bank shore", "선착장": "dock pier", "잔교": "dock pier",
    "저수지": "reservoir", "호수": "lake", "강가": "river bank", "강에서": "in river", "강에": "river",
    "하천": "river", "개울": "creek", "계곡": "creek", "연못": "pond",
    "밤낚시": "night", "야간": "night", "밤": "night", "새벽": "dawn morning", "아침": "morning",
    "해 질 녘": "dusk evening", "해질녘": "dusk evening", "저녁": "evening",
    "겨울": "winter", "여름": "summer", "가을": "fall", "봄": "spring", "바람": "wind",
    "비 오는": "rain", "비가": "rain", "전선": "front", "흙탕물": "muddy water", "탁한": "muddy water",
    "맑은 물": "clear water", "수심": "depth deep", "깊이": "depth", "깊은": "deep", "시즌": "season",
    "시기": "season", "산란": "spawn",
    # asking
    "왜": "why", "어떻게": "how", "몇 마리": "how many", "얼마나": "how many", "무엇": "what", "무슨": "what",
    "어떤": "what", "뭐": "what", "어디": "where", "언제": "when", "어느": "which",
    "가장": "best", "제일": "best", "최고": "best", "좋아": "good", "좋은": "good",
    "쉬운": "easy", "쉽게": "easy", "초보": "beginner", "처음": "beginner", "어린이": "kid", "아이": "kid",
    "먹": "eat", "써야": "use", "쓰는": "use", "사용": "use", "필요": "need",
}
# A state by its Korean name, with or without 주, is the state's English
# name: what Ask's state rules read (jurisdictions.state_in_question).
for _code, _name in STATE_NAMES.items():
    _english = jurisdictions.JURISDICTIONS[_code].name.lower()
    GLOSSARY[_name.lower()] = _english
    if _name.endswith("주"):
        GLOSSARY.setdefault(_name[:-1], _english)

_PHRASES = sorted(GLOSSARY.items(), key=lambda kv: -len(kv[0]))
_NOT_ENGLISH = re.compile(r"[^a-z0-9 ]+")


def is_korean(text: str) -> bool:
    return bool(text) and bool(HANGUL_RE.search(text))


def to_english(text: str) -> str:
    """The question in the words the guides use, and nothing else: ASCII it
    already had stays, Korean the glossary doesn't know is dropped."""
    out = unicodedata.normalize("NFKC", text).lower()
    for ko, english in _PHRASES:
        if ko in out:
            out = out.replace(ko, f" {english} ")
    return " ".join(_NOT_ENGLISH.sub(" ", out).split())
