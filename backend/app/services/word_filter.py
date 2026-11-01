"""Words FishEye doesn't publish: slurs and hate slogans (community safety).

Checked wherever someone writes what other people will see: display names
(services/auth.clean_display_name) and a catch's title, notes and the fish
named under "Other" (services/pins.validate). Not what a report tells the
moderators, which may have to quote what it reports, nor a question to Ask,
which nobody else reads.

The lists are slurs against people for their race, ethnicity, nationality,
religion, sexual orientation, gender identity or disability, in the site's
five languages, and a few hate slogans. This is not a swear filter ("damn,
what a bass" is fine); reports and the moderators handle the rest.

Matching sees through the usual disguises: capitals, accents, fullwidth and
look-alike letters (a Cyrillic а for a), invisible characters, l33t
(n1gg3r), letters spaced or dotted out (n.i.g.g.e.r, 黑 鬼), stretched
(niiigger) or starred (n*gger). And it leaves alone the names people really
write: Latin-script words are matched whole, so "Niger", "snigger",
"spicy", "Scunthorpe", "Japan" and "raccoon" pass, and no lake, river,
access point, county or shop name in the database is refused (checked
against all 250,000 of them on 2026-10-31; tests/test_word_filter.py keeps
the ones that came close).
"""
from __future__ import annotations

import itertools
import re
import unicodedata

# Latin-script slurs refused wherever they appear in a word: long and
# distinctive enough that only the words in LATIN_ALLOWED hold them by chance.
LATIN_ANYWHERE = {
    # anti-Black
    "nigger", "nigga", "niggur", "nigguh", "niglet", "nigglet", "jigaboo", "jiggaboo", "pickaninny",
    "porchmonkey", "junglebunny",
    # anti-Latino, anti-Asian, anti-Arab and anti-Muslim
    "wetback", "zipperhead", "towelhead", "raghead", "cameljockey",
    # anti-gay, anti-trans
    "faggot", "faggit", "shemale",
}
LATIN_ALLOWED = {
    "nigger": ("snigger",),
    "nigga": ("niggard", "knigga"),  # Knigga Run, a creek
    "raghead": ("draghead",),  # a dredge's suction head
}

# Refused as a whole word only (with the forms listed): shorter, or a
# piece of innocent words ("spicy", "Japan", "Scunthorpe"). Not "dyke"
# (Van Dyke, a surname; a dike) nor "kike" (Kike, Spanish for Enrique),
# though "kikes" is.
LATIN_WORDS = {
    # anti-Black
    "nig", "nigs", "nignog", "darkie", "darkies", "darky", "golliwog", "gollywog", "negrata", "negratas",
    "mayate", "mayates",
    # anti-Latino
    "spic", "spics", "beaner", "beaners", "sudaca", "sudacas",
    # anti-Asian
    "chink", "chinks", "chinky", "gook", "gooks", "jap", "japs", "chinaman", "chinamen",
    # anti-Jewish
    "kikes", "kyke", "heeb", "heebs", "hymie", "yid", "yids",
    # anti-Native American
    "injun", "injuns", "redskin", "redskins", "squaw", "squaws",
    # against other ethnic groups
    "wop", "wops", "dago", "dagos", "dagoes", "polack", "polacks", "paki", "pakis",
    # anti-gay, anti-trans
    "fag", "fags", "faggy", "tranny", "trannies", "trannys", "lesbo",
    "maricon", "maricones", "joto", "jotos",
    # against disabled people
    "retard", "retards", "retarded", "mongoloid", "mongoloids", "mongolico", "mongolicos", "spaz", "spazz",
    # against women
    "cunt", "cunts",
    # hate groups
    "kkk",
}

# Old place names still carry some of them: Squaw Creek, Big Injun Lake,
# Chinaman Lake, Darky Branch (all on file, 2026-10-31). Followed by one of
# these words, such a term is the place's name, which people write to say
# where they fished.
PLACE_NAME_TERMS = {
    "squaw", "injun", "redskin", "chinaman", "darkies", "darky", "dago", "polack", "beaner", "fag", "gook",
}
PLACE_WORDS = {
    "lake", "lakes", "pond", "ponds", "pool", "reservoir", "creek", "creeks", "branch", "run", "river", "fork",
    "slough", "bayou", "spring", "springs", "brook", "marsh", "swamp", "bay", "cove", "canyon", "hollow", "gulch",
    "draw", "gap", "valley", "point", "island", "dam", "ramp", "landing", "access", "park", "town", "county",
    "road", "rd", "trail", "hill", "mountain", "peak", "ridge", "flat", "flats", "mill", "falls",
}

# Whole words in a row.
LATIN_PHRASES = {
    "porch monkey", "jungle bunny", "camel jockey", "slant eye", "slant eyes",
    "heil hitler", "sieg heil", "gas the jews",
}

# Chinese, Japanese and Korean: refused wherever they appear, as these
# scripts don't put spaces between words. Only terms that aren't also a
# piece of common words: not 棒子 (corn cob), チョン, ホモ (homogenized),
# おかま (rice pot), 튀기 (frying), 새끼 (a fish's young) or 니거 ("yours").
CJK = {
    # Chinese
    "黑鬼", "尼哥", "支那", "支畜", "印度阿三", "高丽棒子", "高麗棒子", "小日本", "日本鬼子", "洋鬼子", "台巴子",
    "死基佬", "人妖",
    # Japanese
    "ニガー", "黒んぼ", "くろんぼ", "クロンボ", "ジャップ", "チョン公", "キチガイ", "きちがい", "気違い", "ガイジ",
    "穢多", "オカマ",
    # Korean
    "깜둥이", "짱깨", "짱개", "쪽바리", "똥남아", "병신", "븅신", "한남충", "김치녀", "맘충", "똥꼬충", "틀딱",
}
CJK_ALLOWED = {
    "ガイジ": ("ガイジン",),  # 外人, a foreigner
}

# Letters from other alphabets that look like Latin ones.
_LOOKALIKE = str.maketrans({
    "а": "a", "в": "b", "е": "e", "ё": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c",
    "т": "t", "у": "y", "х": "x", "і": "i", "ї": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ɡ": "g",
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "χ": "x",
})
# l33t: digits and signs written for letters, read inside a word.
_LEET = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "9": "g",
    "@": "a", "$": "s", "!": "i", "|": "i", "€": "e",
})
_VOWELS = "aeiou"


def _pattern(term: str, stretch: str = "") -> str:
    """`term` as a regex. A vowel may be starred out (n*gger). Stretched
    letters (niiigger): with stretch="any", a letter may be typed any number
    of extra times; with "plain", only past doubling, since a doubled letter
    is often another word ("pollack", a fish, isn't "polack")."""
    out = []
    for letter, run in itertools.groupby(term):
        n = len(list(run))
        if letter == " ":
            out.append(" ")
            continue
        one = f"[{letter}*]" if letter in _VOWELS else re.escape(letter)
        if stretch == "any" or (stretch == "plain" and n > 1):
            out.append(f"{one}{{{n},}}")
        elif stretch == "plain":
            out.append(f"(?:{one}|{one}{{3,}})")
        else:
            out.append(one * n)
    return "".join(out)


def _alternation(terms: set[str], stretch) -> re.Pattern[str]:
    # Longest first, so a regex alternation prefers "niggers" to "nigger".
    ordered = sorted(terms, key=lambda t: (-len(t), t))
    return re.compile("|".join(f"(?:{_pattern(t, stretch(t))})" for t in ordered))


_ANYWHERE_RE = _alternation(LATIN_ANYWHERE, lambda t: "any")
# A short word stretched is too often another word ("woop" isn't "wop").
_WORD_RE = _alternation(LATIN_WORDS, lambda t: "plain" if len(t) >= 5 else "")
_PLACE_TERM_RE = re.compile("|".join(PLACE_NAME_TERMS))
_PHRASE_RE = re.compile(r"(?:^| )(?:" + "|".join(_pattern(p) for p in sorted(LATIN_PHRASES)) + r")(?= |$)")
_CJK = sorted({unicodedata.normalize("NFKC", t) for t in CJK}, key=len, reverse=True)


def _spelled_out(tokens: list[str], shortest: int) -> list[str]:
    """Runs of one-character tokens joined: "n i g g e r", "黑 鬼"."""
    joined, run = [], []
    for tok in [*tokens, ""]:
        if len(tok) == 1:
            run.append(tok)
            continue
        if len(run) >= shortest:
            joined.append("".join(run))
        run = []
    return joined


def _latin_tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFKC", text).casefold().translate(_LOOKALIKE)
    t = "".join(
        ch for ch in unicodedata.normalize("NFKD", t) if not unicodedata.combining(ch) and unicodedata.category(ch) != "Cf"
    )
    tokens = []
    for raw in re.findall(r"[a-z0-9@$!|€*]+", t):
        word = raw.strip("!|*")
        if any("a" <= ch <= "z" for ch in word):  # a word, maybe in l33t; not a number
            tokens.append(word.translate(_LEET))
    return tokens


def _cjk_tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFKC", text).casefold()
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    return re.findall(r"[^\W_]+", t)


def _without(word: str, allowed: tuple[str, ...]) -> str:
    for ok in allowed:
        word = word.replace(ok, " ")
    return word


def _anywhere(word: str) -> str | None:
    """A LATIN_ANYWHERE slur in `word`, unless only inside an allowed word."""
    for m in _ANYWHERE_RE.finditer(word):
        term = next((t for t in LATIN_ANYWHERE if re.fullmatch(_pattern(t, "any"), m.group(0))), "")
        if _ANYWHERE_RE.search(_without(word, LATIN_ALLOWED.get(term, ()))):
            return m.group(0)
    return None


def blocked_word(text: str | None) -> str | None:
    """The slur or hate slogan in `text`, as matched, or None."""
    if not text:
        return None
    tokens = _latin_tokens(text)
    for i, word in enumerate(tokens):
        place = _PLACE_TERM_RE.fullmatch(word) and tokens[i + 1 : i + 2] and tokens[i + 1] in PLACE_WORDS
        if (m := _WORD_RE.fullmatch(word)) and not place:
            return m.group(0)
        if hit := _anywhere(word):
            return hit
    for run in _spelled_out(tokens, 3):
        # Spelled out, it may run on into a word next to it ("a k i k e s").
        if m := _WORD_RE.search(run):
            return m.group(0)
        if hit := _anywhere(run):
            return hit
    if m := _PHRASE_RE.search(" ".join(tokens)):
        return m.group(0).strip()
    pieces = _cjk_tokens(text)
    for piece in [*pieces, *_spelled_out(pieces, 2)]:
        for term in _CJK:
            if term in piece and term in _without(piece, CJK_ALLOWED.get(term, ())):
                return term
    return None
