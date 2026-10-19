"""Rank guide passages for a question.

Why BM25 and not embeddings (the long version is ADR 0014)
-----------------------------------------------------------
The corpus is ~110 short passages of reviewed text with a small, very
specific vocabulary — species names, "jig", "slip bobber", "cast net". That
is the case lexical ranking is good at, and the retrieval eval
(app/eval/rag_cases.py) measures it rather than assuming it. Embeddings
would need either a model download or a vendor key and network access on
every machine the demo runs on, which buys a dependency before there's a
measured miss to justify it. The `Retriever` protocol is the seam an
embedding or hybrid retriever plugs into once the eval shows lexical
matching falling short.

Two things are added on top of plain BM25, both small and both visible:

1. **Species routing.** A question that names a fish ("crappie", or the
   Texas nickname "sand bass") only searches that fish's passages plus the
   shared ones. Without this, "what bait for crappie" ranks the *catfish*
   bait list well too — both are bait lists — and the answer would quote
   the wrong fish. Nicknames are listed explicitly in SPECIES_ALIASES.
2. **A short synonym list** for the words beginners use that the guides
   don't ("gear" for rod/reel, "feed on" for eats). It's a list, not a
   model, so it can be read in full and tested.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Protocol

from app.services.rag import zh
from app.services.rag.chunking import SHARED_SLUG, Passage, build_passages

# BM25 defaults from the literature; the eval did not show a reason to tune them.
K1 = 1.2
B = 0.75

STOPWORDS = frozenset(
    """a an and are as at be but by can do does for from go good how i if in
    into is it its me my of on or should so some that the their them then there
    these they this to use using up was we what which who will with you
    your best catch fish fishing texas about me know info information more
    anything much many""".split()
)
# "tell me about X" asks for an overview; a bare "tell" ("tell them apart")
# asks how to recognise a fish. The phrase is removed before tokenising so
# the two don't collide.
_QUERY_NOISE_RE = re.compile(r"\btell me\b")
# "What does it look like" asks how to recognise a fish. Only the phrase is
# rewritten: a bare "look" usually means where to search ("where should I
# look for crappie"), so it can't be a single-word synonym.
_LOOK_LIKE_RE = re.compile(r"\blooks? like\b")
# "What do sand bass eat" asks about the diet; "are sand bass good to eat"
# asks about the table. Only the second phrasing is rewritten, to the words
# the guides' cooking passages use ("On the table: cleaning and cooking it").
# "Going bad", "spoil", "stay fresh": the handbook calls that ice and a
# cooler, so say so in the query (docs/adr/0026).
_SPOIL_RE = re.compile(r"\b(?:go(?:ing|es)?|went)\s+bad\b|\bspoil(?:ing|s|ed)?\b|\bstay\s+fresh\b|\brot(?:ting|s)?\b")
_TABLE_RE = re.compile(r"\b(?:good|safe|ok|okay|fit)\s+to\s+eat\b|\beat(?:ing)?\s+(?:it|them|one)\b|\btable\s+fare\b")
# "why" is not a stopword: "why use minnows for crappie" should find the
# "Why these baits work" passage, whose title says so (docs/adr/0024).
# "fish", "catch", "fishing", "texas", "best" appear in nearly every question
# and carry no signal about which passage answers it. They are still matched
# inside passages through species names like "catfish" and "bait fish".

# Words beginners use -> words the guides use. Applied to the query only.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "feed": ("eat",),
    "food": ("eat",),
    "diet": ("eat",),
    "gear": ("rod", "reel", "setup"),
    "tackle": ("rod", "reel", "setup"),
    "equipment": ("rod", "reel", "setup"),
    "pole": ("rod",),
    "rig": ("hook", "rig"),
    "tie": ("hook", "rig"),
    "artificial": ("lure",),
    "lure": ("lure", "jig"),
    "where": ("where", "find"),
    "spot": ("where", "find"),
    "locate": ("where", "find"),
    "season": ("when", "spring", "summer", "fall", "winter"),
    "time": ("when",),
    "month": ("when",),
    "legal": ("legal", "unlawful", "rule"),
    "law": ("legal", "unlawful", "rule"),
    "allowed": ("legal", "unlawful", "rule"),
    "illegal": ("legal", "unlawful", "rule"),
    "regulation": ("legal", "unlawful", "rule"),
    "identify": ("recognise",),
    "recognize": ("recognise",),
    "apart": ("recognise",),
    "difference": ("recognise",),
    "easy": ("beginner",),
    "easiest": ("beginner",),
    "easier": ("beginner",),
    "kid": ("beginner",),
    "net": ("net", "cast"),
    "tell": ("recognise",),
    "deep": ("deep", "ft"),  # depths in the guides are written "5 ft", "10 ft deep"
    "depth": ("deep", "ft"),
    "shallow": ("deep", "ft"),
    # Cleaning, keeping and eating a catch (handbook, docs/adr/0024)
    "clean": ("clean", "fillet", "skin", "scale"),
    "gut": ("gut", "clean"),
    "kill": ("kill", "bleed", "stun"),
    "dispatch": ("kill", "bleed", "stun"),
    "cook": ("cook", "eat"),
    "cooked": ("cook", "eat"),
    "hurt": ("harm", "hurt"),
    "harm": ("harm",),
    "taste": ("taste", "flavor", "eat"),
    "fresh": ("fresh", "ice"),
    # Telling fish apart
    "whisker": ("whisker", "barbel"),
    "vs": ("recognise",),
    "versus": ("recognise",),
    "compare": ("recognise",),
    "differ": ("recognise",),
    # Habitat and habits
    "habitat": ("habitat", "live"),
    "behavior": ("habit", "behavior"),
    "behave": ("habit", "behavior"),
    "habit": ("habit", "behavior"),
    # Why a bait works
    "reason": ("why",),
    "advantage": ("why",),
    "benefit": ("why",),
    # The vocabulary of the topics added in docs/adr/0026
    "windy": ("wind", "windblown"),
    "breeze": ("wind", "windblown"),
    "breezy": ("wind", "windblown"),
    "cloudy": ("cloud", "overcast", "light"),
    "overcast": ("cloud", "light"),
    "sunny": ("sun", "bright", "light"),
    "hide": ("cover", "shelter", "hold"),
    "hiding": ("cover", "shelter", "hold"),
    "stabbed": ("spine", "barb", "fin"),
    "stab": ("spine", "barb", "fin"),
    "stung": ("spine", "barb", "fin"),
    "sting": ("spine", "barb", "fin"),
    "poke": ("spine", "barb", "fin"),
    "backlashing": ("backlash", "spool", "thumb"),
    "tangle": ("backlash", "tangle"),
    "licence": ("license",),
    # The guides spell it "licence"; most people asking type "license".
    "license": ("licence",),
    "licenses": ("licence",),
    "permit": ("license",),
    "muddy": ("muddy", "stain", "clarity"),
    "murky": ("muddy", "stain", "clarity"),
    "clarity": ("clarity", "clear", "stain"),
    # "which line is hardest for fish to see" is about invisible line, not
    # about water clarity: say "invisible", which is the guides' word.
    "see": ("see", "invisible", "visible"),
    "invisible": ("invisible", "visible"),
    "freezer": ("freeze", "frozen"),
    "frozen": ("freeze", "frozen"),
    "defrost": ("thaw",),
    "fridge": ("refrigerator", "refrigerate"),
    "beginner": ("beginner", "start", "first"),
    "never": ("start", "first", "beginner"),
    # Found by rephrasing the eval questions (STRESS_CASES, docs/adr/0025)
    "prepare": ("clean", "fillet", "cook"),
    "menu": ("eat", "diet"),
    "edible": ("eat", "table", "cook"),
    "let": ("release",),
}

# A question that names no fish must read as a fishing question to be
# searched at all. Without this gate, "recommend a good pizza place" matches
# "the easiest place to start" and gets a confident answer about catfish.
#
# Two lists, because many fishing words are everyday words too. One FISHING
# word is enough ("where can I fish near Austin", "what rod for a
# beginner"). AMBIGUOUS words count only in pairs: "line" alone is line
# dancing, "boat" alone is a boat motor, "tie" alone is a necktie ("how to
# tie a tie" outscored a real knot question), but "hook and line" or
# "worms off the bank" is fishing. Question words ("where", "when",
# "easy", "legal") never count: they used to, and "where is the nearest
# hospital" was searched as a fishing question.
#
# The gate reads the raw question, not the query tokens: "fish", "fishing"
# and "catch" are stopwords for ranking (they are in nearly every question)
# but they are exactly the words that say a question is about fishing.
FISHING_TERMS = frozenset(
    # Fishing itself
    """fish fishing fished fisherman fishermen angler angling spawn spawning
    """
    # Baits (a fish named in SPECIES_ALIASES is routed before the gate runs)
    # Casting, playing a fish, conditions, safety and the rules (ADR 0026).
    # "cast" itself stays ambiguous (a cast on a broken arm, a film cast).
    """backlash casting baitcasting spincast overhand bail spool drag reel
    livewell bilge trotline juglines jugline bowfishing creel tacklebox
    bluebird windblown
    """
    # Baits (a fish named in SPECIES_ALIASES is routed before the gate runs)
    """bait baitfish nightcrawler crawler redworm mealworm waxworm leech minnow
    shiner crawfish crayfish crawdad grasshopper stinkbait powerbait boilie
    """
    # Lures
    """lure jig jighead crankbait spinnerbait buzzbait jerkbait swimbait
    topwater
    """
    # Tackle and knots
    """rod reel tackle hook bobber sinker spincast baitcaster baitcasting
    monofilament fluorocarbon livewell palomar
    """
    # Other fish people catch that have no guide yet: the gate admits the
    # question, and retrieval says honestly what the guides don't cover.
    """panfish gamefish walleye sauger gar pike muskie muskellunge smallmouth
    warmouth longear bowfin bullhead""".split()
)
AMBIGUOUS_TERMS = frozenset(
    """line tie knot clinch arbor net cast rig boat bank shore dock pier lake
    pond river reservoir creek troll drift worm cricket shrimp liver corn
    cheese dough chum eat feed food diet deep shallow depth cover brush
    school slab spoon plug popper grub spinner gear pole equipment float slip
    leader swivel braid mono shot weight catch caught bite water pound lb
    release stringer cooler clean fillet gut scale skin bleed cook
    farther further distance accuracy backlashes tangle tangles drift
    license licence permit legal endorsement warden
    jacket vest drown drowning safety spine spines barb barbs
    front fronts pressure barometer barometric clarity stained murky muddy
    clear visibility wind windy breeze cloudy overcast sunny
    structure point points ledge dropoff flat flats timber laydown
    freeze freezer frozen thaw thawed fridge refrigerator vacuum glaze
    measure measuring length ruler mount
    drain dry invasive mussel mussels zebra trailer launch ramp
    monofilament recycle recycling discard discarded""".split()
)
# Two everyday words that together name a piece of tackle or a practice.
FISHING_PHRASES = (
    "clean drain dry",
    "life jacket",
    "life jackets",
    "fishing license",
    "fishing licence",
    "cold front",
    "drop off",
    "drop-off",
    "cast farther",
    "cast further",
    "my catch",
    "the catch",
    "split shot",
    "slip bobber",
    "circle hook",
    "treble hook",
    "cast net",
    "catch and release",
    "texas rig",
    "carolina rig",
    "drop shot",
    "ned rig",
    "punch bait",
    "dip bait",
    "cut bait",
)
_GATE_WORD_RE = re.compile(r"[a-z]+")


def is_on_topic(question: str) -> bool:
    lowered = question.lower()
    if zh.is_on_topic(lowered):
        return True
    if any(phrase in lowered for phrase in FISHING_PHRASES):
        return True
    words = {stem(w) for w in _GATE_WORD_RE.findall(lowered)}
    words |= {w for w in _GATE_WORD_RE.findall(lowered)}
    if words & FISHING_TERMS:
        return True
    return len(words & AMBIGUOUS_TERMS) >= 2


# Phrase -> species slugs. Longest phrases are matched first and consumed,
# so "white crappie" never also counts as a bare "crappie".
SPECIES_ALIASES: dict[str, tuple[str, ...]] = {
    "largemouth bass": ("largemouth-bass",),
    "largemouth": ("largemouth-bass",),
    "bigmouth": ("largemouth-bass",),
    "spotted bass": ("spotted-bass",),
    "kentucky bass": ("spotted-bass",),
    "white bass": ("white-bass",),
    "sand bass": ("white-bass",),
    "sandbass": ("white-bass",),
    "sandies": ("white-bass",),
    "hybrid striped bass": ("hybrid-striped-bass",),
    "hybrid striper": ("hybrid-striped-bass",),
    "wipers": ("hybrid-striped-bass",),
    "wiper": ("hybrid-striped-bass",),
    "striped bass": ("striped-bass",),
    "stripers": ("striped-bass",),
    "striper": ("striped-bass",),
    "channel catfish": ("channel-catfish",),
    "channel cats": ("channel-catfish",),
    "channel cat": ("channel-catfish",),
    "blue catfish": ("blue-catfish",),
    "blue cats": ("blue-catfish",),
    "blue cat": ("blue-catfish",),
    "catfish": ("channel-catfish", "blue-catfish", "flathead-catfish"),
    "white crappie": ("white-crappie",),
    "black crappie": ("black-crappie",),
    "crappies": ("white-crappie", "black-crappie"),
    "crappie": ("white-crappie", "black-crappie"),
    "sac-a-lait": ("white-crappie", "black-crappie"),
    "papermouth": ("white-crappie", "black-crappie"),
    "bluegills": ("bluegill",),
    "bluegill": ("bluegill",),
    "bream": ("bluegill",),
    "brim": ("bluegill",),
    "sunfish": ("bluegill", "redear-sunfish"),
    "perch": ("bluegill",),
    "gizzard shad": ("gizzard-shad",),
    "threadfin shad": ("threadfin-shad",),
    "threadfin": ("threadfin-shad",),
    "yellowtails": ("threadfin-shad",),
    "shad": ("gizzard-shad", "threadfin-shad"),
    # Added with the expansion (docs/adr/0024). Other names are TPWD's.
    "flathead catfish": ("flathead-catfish",),
    "flatheads": ("flathead-catfish",),
    "flathead": ("flathead-catfish",),
    "yellow cats": ("flathead-catfish",),
    "yellow cat": ("flathead-catfish",),
    "opelousas": ("flathead-catfish",),
    "mud cat": ("flathead-catfish",),
    "shovelhead": ("flathead-catfish",),
    "guadalupe bass": ("guadalupe-bass",),
    "guadalupe spotted bass": ("guadalupe-bass",),
    "guads": ("guadalupe-bass",),
    "state fish": ("guadalupe-bass",),
    "redear sunfish": ("redear-sunfish",),
    "redears": ("redear-sunfish",),
    "redear": ("redear-sunfish",),
    "shellcrackers": ("redear-sunfish",),
    "shellcracker": ("redear-sunfish",),
    "rainbow trout": ("rainbow-trout",),
    "rainbows": ("rainbow-trout",),
    "trout": ("rainbow-trout",),
    "freshwater drum": ("freshwater-drum",),
    "gaspergou": ("freshwater-drum",),
    "common carp": ("common-carp",),
    "carp": ("common-carp",),
    # Anglers' nicknames, found by rephrasing the eval questions: "best bait
    # for slabs" used to answer with white and striped bass.
    "strawberry bass": ("black-crappie",),
    "barfish": ("white-bass",),
    "appaloosa": ("flathead-catfish",),
    "chinquapin": ("redear-sunfish",),
    "chinkapin": ("redear-sunfish",),
    "sunperch": ("bluegill",),
    "bucketmouths": ("largemouth-bass",),
    "bucketmouth": ("largemouth-bass",),
    "green trout": ("largemouth-bass",),
    "sunnies": ("bluegill", "redear-sunfish"),
    "whiskerfish": ("channel-catfish", "blue-catfish", "flathead-catfish"),
    "catfishing": ("channel-catfish", "blue-catfish", "flathead-catfish"),
    "linesides": ("striped-bass",),
    "lineside": ("striped-bass",),
    # A bare "bass" means the black basses, as it does in TPWD's own usage
    # ("black bass" regulations). Before this, "what bait for bass" routed
    # nowhere and the shad bait lists won, because they repeat "striped bass
    # and hybrid striped bass". Longer names ("white bass", "striped bass")
    # match first and are removed, so they never fall through to this.
    "black basses": ("largemouth-bass", "spotted-bass", "guadalupe-bass"),
    "black bass": ("largemouth-bass", "spotted-bass", "guadalupe-bass"),
}

# Fish people catch that have no guide, including ones whose names contain
# a guided fish's name ("red drum", "speckled trout", "smallmouth bass",
# "yellow perch"). They are removed before the aliases above are matched,
# so "red drum" is never read as freshwater drum; a question that names
# only these gets the "not covered" answer instead of whichever passages
# happen to mention the shared word.
UNGUIDED_FISH = (
    # Saltwater and out-of-state fish Texans ask about, and names that would
    # otherwise be read as a guided fish ("specks" is speckled trout here,
    # "goggle-eye" a warmouth or rock bass).
    "specks", "speck", "sand trout", "gafftopsail", "gafftop", "hardhead catfish",
    "goggle-eye", "goggleye", "croaker", "bluefish", "snook", "tarpon", "grouper",
    "smallmouth bass", "smallmouths", "smallmouth", "peacock bass", "sea bass",
    "rock bass", "yellow bass", "red drum", "black drum", "redfish",
    "speckled trout", "spotted seatrout", "seatrout", "sea trout", "brown trout",
    "brook trout", "cutthroat trout", "yellow perch", "white perch", "walleye",
    "sauger", "alligator gar", "gar", "northern pike", "pike", "muskellunge",
    "muskie", "bowfin", "bullheads", "bullhead", "warmouth", "longear sunfish",
    "longear", "green sunfish", "flounder", "sheepshead", "tilapia", "salmon",
    "tuna", "snapper", "mackerel", "shark", "sharks", "buffalo fish",
)
# Chinese names (docs/adr/0025). Chinese has no spaces, so these match as
# substrings, longest first, with the same masking as above: "红鼓鱼" (red
# drum) is blanked before "鼓鱼" (drum) can match. The names are the ones
# Chinese-language fishing writing uses for these North American species;
# a bare "鲈鱼" means the black basses, like a bare "bass".
_BLACK_BASSES = ("largemouth-bass", "spotted-bass", "guadalupe-bass")
ZH_SPECIES_ALIASES: dict[str, tuple[str, ...]] = {
    "大口黑鲈": ("largemouth-bass",),
    "大嘴鲈": ("largemouth-bass",),
    "加州鲈": ("largemouth-bass",),
    "斑点黑鲈": ("spotted-bass",),
    "斑点鲈": ("spotted-bass",),
    "瓜达鲁佩鲈": ("guadalupe-bass",),
    "瓜达卢佩鲈": ("guadalupe-bass",),
    "白鲈": ("white-bass",),
    "杂交条纹鲈": ("hybrid-striped-bass",),
    "杂交鲈": ("hybrid-striped-bass",),
    "条纹鲈": ("striped-bass",),
    "条纹狼鲈": ("striped-bass",),
    "美洲狼鲈": ("striped-bass",),
    "黑鲈": _BLACK_BASSES,
    "鲈鱼": _BLACK_BASSES,
    "斑点叉尾鮰": ("channel-catfish",),
    "斑点叉尾鲴": ("channel-catfish",),
    "沟鲶": ("channel-catfish",),
    "蓝鮰": ("blue-catfish",),
    "蓝鲶": ("blue-catfish",),
    "长鳍叉尾鮰": ("blue-catfish",),
    "扁头鮰": ("flathead-catfish",),
    "扁头鲶": ("flathead-catfish",),
    "平头鲶": ("flathead-catfish",),
    "鲶鱼": ("channel-catfish", "blue-catfish", "flathead-catfish"),
    "鲇鱼": ("channel-catfish", "blue-catfish", "flathead-catfish"),
    "鮰鱼": ("channel-catfish", "blue-catfish", "flathead-catfish"),
    "白莓鲈": ("white-crappie",),
    "黑莓鲈": ("black-crappie",),
    "莓鲈": ("white-crappie", "black-crappie"),
    "刺盖太阳鱼": ("white-crappie", "black-crappie"),
    "蓝鳃太阳鱼": ("bluegill",),
    "蓝鳃鱼": ("bluegill",),
    "蓝鳃": ("bluegill",),
    "红耳太阳鱼": ("redear-sunfish",),
    "红耳": ("redear-sunfish",),
    "太阳鱼": ("bluegill", "redear-sunfish"),
    "美洲真鰶": ("gizzard-shad",),
    "大肚鲥": ("gizzard-shad",),
    "线鳍鲥": ("threadfin-shad",),
    "线鳍真鰶": ("threadfin-shad",),
    "鲥鱼": ("gizzard-shad", "threadfin-shad"),
    "虹鳟": ("rainbow-trout",),
    "鳟鱼": ("rainbow-trout",),
    "淡水鼓鱼": ("freshwater-drum",),
    "淡水石首鱼": ("freshwater-drum",),
    "鼓鱼": ("freshwater-drum",),
    "鲤鱼": ("common-carp",),
}
ZH_UNGUIDED_FISH = (
    "小口黑鲈", "小嘴鲈", "红鼓鱼", "红鼓", "黑鼓", "海鳟", "斑点海鳟", "黄金鲈", "黄鲈",
    "白梭吻鲈", "梭鱼", "狗鱼", "雀鳝", "弓鳍鱼", "罗非鱼", "鲑鱼", "三文鱼", "金枪鱼",
    "鲨鱼", "比目鱼", "鲈鲉", "海鲈",
)
_ZH_ALIASES = sorted(ZH_SPECIES_ALIASES.items(), key=lambda kv: -len(kv[0]))
_ZH_UNGUIDED = sorted(ZH_UNGUIDED_FISH, key=len, reverse=True)

_UNGUIDED_PATTERNS = [
    re.compile(rf"\b{re.escape(name)}\b") for name in sorted(UNGUIDED_FISH, key=len, reverse=True)
]
_ALIAS_PATTERNS = [
    (re.compile(rf"\b{re.escape(alias)}\b"), slugs)
    for alias, slugs in sorted(SPECIES_ALIASES.items(), key=lambda kv: -len(kv[0]))
]

# Names that are also everyday words. "Bass" is a guitar, "drum" an
# instrument, "spots" places, "blues" music, "hybrid" a car, "slab"
# concrete, "cats" pets. Each used to route unconditionally, so "I play bass
# in a band" and "how do I tune a drum" were answered with fish passages.
#
# They are matched only after the unambiguous names (so "white bass" and
# "freshwater drum" still win), and then only kept when the question reads
# as being about the fish. Two ways to decide that, in `resolve_species`:
# with the embedding model, the question is compared against the fish's own
# passages and against the decoy sentences below, and the closer side wins —
# a comparison, not a threshold, which is what makes it reliable (ADR 0026);
# without the model, another fishing word has to appear in the question.
@dataclass(frozen=True)
class AmbiguousName:
    """A fish name that is also an everyday word.

    `decoys` are sentences in the everyday sense. With the embedding model
    the question is compared against the fish's own passages and against
    these, and the closer side wins (hybrid.py): a comparison rather than a
    threshold, which is what makes it reliable (ADR 0026).

    `everyday` and `fish_by_default` are the fallback when the model isn't
    installed, and they are cruder on purpose: a word from `everyday`
    anywhere in the question means the everyday sense; otherwise the name
    counts as the fish if `fish_by_default` (the word is mostly a fish in a
    fishing app) and only with a clear fishing word if not."""

    slugs: tuple[str, ...]
    decoys: tuple[str, ...]
    everyday: frozenset[str]
    fish_by_default: bool


_MUSIC = "guitar guitars bassist amp amps amplifier speaker speakers subwoofer treble clef band bands music song songs singer solo pedal pedals string strings tab tabs tune tuned tuning note notes play playing played album albums concert"
_BASSES_ = ("largemouth-bass", "spotted-bass", "guadalupe-bass")
_CATS_ = ("channel-catfish", "blue-catfish", "flathead-catfish")
_CRAPPIE_ = ("white-crappie", "black-crappie")

AMBIGUOUS_ALIASES: dict[str, AmbiguousName] = {
    "bass": AmbiguousName(
        _BASSES_,
        ("A bass guitar, bass strings, playing bass in a band, a bassist.",
         "Bass and treble, low frequencies, a subwoofer, turning the bass up.",
         "A bass singer, the bass part in a choir, bass clef."),
        frozenset(f"{_MUSIC} boost drop deep woofer stereo".split()),
        True,
    ),
    "basses": AmbiguousName(
        _BASSES_,
        ("Bass guitars, double basses, instruments in an orchestra.",),
        frozenset(f"{_MUSIC} orchestra instrument instruments".split()),
        True,
    ),
    "drum": AmbiguousName(
        ("freshwater-drum",),
        ("A drum kit, drumsticks, drumming, a snare drum, a drum solo.",
         "An oil drum, a barrel, a drum of chemicals.",
         "A brake drum, a washing machine drum."),
        frozenset(f"{_MUSIC} kit snare percussion beat beats drummer drumstick drumsticks roll oil barrel brake washing washer machine".split()),
        True,
    ),
    "drums": AmbiguousName(
        ("freshwater-drum",),
        ("Drums, a drum kit, percussion, playing drums in a band.",),
        frozenset(f"{_MUSIC} kit snare percussion drummer".split()),
        True,
    ),
    "hybrid": AmbiguousName(
        ("hybrid-striped-bass",),
        ("A hybrid car, a plug-in hybrid, hybrid engines and fuel economy.",
         "A hybrid plant or animal, hybrid seeds, a hybrid working week."),
        frozenset("car cars vehicle vehicles engine electric petrol gas mpg battery seed seeds plant plants crop corn breed office work working remote cloud app model".split()),
        True,
    ),
    "hybrids": AmbiguousName(
        ("hybrid-striped-bass",),
        ("Hybrid cars, electric and hybrid vehicles.",),
        frozenset("car cars vehicle vehicles engine electric battery seed seeds plant plants breed".split()),
        True,
    ),
    "slab": AmbiguousName(
        _CRAPPIE_,
        ("A concrete slab, a slab foundation, a stone slab, a slab of meat.",),
        frozenset("concrete cement foundation foundations stone granite marble patio driveway garage tile pour poured thick meat ribs butter".split()),
        True,
    ),
    "slabs": AmbiguousName(
        _CRAPPIE_,
        ("Concrete slabs, stone slabs, a slab foundation.",),
        frozenset("concrete cement foundation foundations stone granite marble patio driveway garage tile pour poured thick meat ribs".split()),
        True,
    ),
    "whites": AmbiguousName(
        ("white-bass",),
        ("The colour white, white paint, white clothes, whites in the wash.",),
        frozenset("white wash washing laundry bleach paint colour color shirt shirts shoes teeth eggs".split()),
        True,
    ),
    "yellows": AmbiguousName(
        ("flathead-catfish",),
        ("The colour yellow, yellow paint, shades of yellow.",),
        frozenset("paint colour color shade shades leaves light lights".split()),
        True,
    ),
    # Everyday words first, fish second: these need a clear fishing word
    # when the model isn't there to judge.
    "blues": AmbiguousName(
        ("blue-catfish",),
        ("Blues music, a blues guitar riff, a blues band playing in a bar.",
         "Feeling blue, sadness, having the blues.",
         "The colour blue, blue paint, blue clothes."),
        frozenset(f"{_MUSIC} riff bar sad sadness feeling mood paint colour color".split()),
        False,
    ),
    "spots": AmbiguousName(
        ("spotted-bass",),
        ("Parking spots, a good spot to eat, tourist spots to visit.",
         "A spot on a shirt, a stain, a mark, a skin spot."),
        frozenset("parking park tourist visit city town restaurant restaurants eat picnic hotel stain shirt skin face mark remove".split()),
        False,
    ),
    "cats": AmbiguousName(
        _CATS_,
        ("Pet cats, kittens, cat food, a cat on the sofa, vets and cats.",
         "CAT machinery, a caterpillar excavator."),
        frozenset("pet pets kitten kittens vet vets litter sofa purr meow dog dogs excavator machinery bowl kibble".split()),
        False,
    ),
    "cat": AmbiguousName(
        _CATS_,
        ("A pet cat, a kitten, cat food, taking a cat to the vet.",),
        frozenset("pet pets kitten kittens vet vets litter sofa purr meow dog dogs bowl kibble her his".split()),
        False,
    ),
}
_AMBIGUOUS_PATTERNS = [
    (alias, re.compile(rf"\b{re.escape(alias)}\b"), name)
    for alias, name in sorted(AMBIGUOUS_ALIASES.items(), key=lambda kv: -len(kv[0]))
]

_TOKEN_RE = re.compile(r"[a-z]+|\d+(?:/\d+)?")


def stem(word: str) -> str:
    """A deliberately light stemmer: plurals and -ing. The corpus is small
    and hand-written, so a full Porter stemmer's over-merging ("bass" ->
    "bas", "lure" -> "lur") costs more than it finds."""
    if len(word) <= 3 or word.endswith(("ss", "us")):
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-1]  # crappies -> crappie, fries -> frie (harmless)
    if word.endswith(("shes", "ches", "xes")):
        return word[:-2]  # inches -> inch
    if word.endswith("ing") and len(word) > 5:
        root = word[:-3]
        if len(root) > 2 and root[-1] == root[-2] and root[-1] not in "ls":
            root = root[:-1]  # jigging -> jig
        return root
    if word.endswith("s"):
        return word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    # Single letters are dropped: "what's" splits into "what" and "s", and a
    # lone "s" matched every possessive in the guides ("catfish's"), ranking
    # unrelated passages up. Digits are kept ("5 ft").
    return [
        stem(t)
        for t in _TOKEN_RE.findall(text.lower())
        if t not in STOPWORDS and (len(t) > 1 or t.isdigit())
    ]


def tokenize_query(text: str) -> list[str]:
    text = _QUERY_NOISE_RE.sub(" ", text.lower())
    text = _TABLE_RE.sub(lambda m: f" {m.group(0)} table cook ", text)
    text = _SPOIL_RE.sub(lambda m: f" {m.group(0)} fresh ice cooler keep ", text)
    return tokenize(_LOOK_LIKE_RE.sub(" recognise ", text))


_COMPARE_RE = re.compile(r"\b(?:or|vs\.?|versus)\b|还是|区别|不同")
_COMPARE_FILLER = frozenset({"know", "tell", "way", "sure", "one", "difference", "apart", "which", "identify", "how"})


def query_terms(question: str, residual: str, named: tuple[str, ...]) -> list[str]:
    """The ranking terms: the question (minus any fish names it routed on),
    with English added for Chinese terms (zh.with_english), tokenised and
    expanded with synonyms.

    "Is this a white bass or a wiper" names two fish and asks nothing else:
    that is an identification question even without "tell apart" in it."""
    tokens = tokenize_query(zh.with_english(residual if named else question))
    if len(named) >= 2 and _COMPARE_RE.search(question.lower()) and set(tokens) <= _COMPARE_FILLER:
        tokens.append("recognise")
    return expand_query(tokens)


# "How can I fish a bass": a fish's name plus nothing narrower than how to
# catch it. The answer is the four sections that make a plan (bait, lures, a
# rig, where and when) for the fish named first, not the four passages that
# happen to repeat "catch" or "fish".
_HOWTO_INTENT = frozenset({"catch", "catching", "fish", "fishing", "tip", "tips", "technique", "techniques"})
_HOWTO_EXTRA = frozenset(
    {"tip", "way", "ways", "start", "beginner", "help", "advice", "technique", "method", "target", "try",
     "learn", "easy", "good", "easiest", "go"}
)
HOWTO_SECTIONS: tuple[tuple[str, ...], ...] = (
    ("live_baits", "why_these_baits"),
    ("lures",),
    ("setup-1",),
    ("where_and_when",),
)


def wants_howto(residual: str) -> bool:
    """Asks how to catch the fish in some form ("teach me to catch a bass"),
    whatever else it says. Used only when nothing else in the question
    matched a passage: a fish's name plus "catch" is never "not covered"."""
    if zh.has_chinese(residual):
        return any(w in residual for w in ("钓", "抓"))
    return bool(set(_TOKEN_RE.findall(residual.lower())) & _HOWTO_INTENT)


def is_howto(residual: str) -> bool:
    if zh.has_chinese(residual):
        return zh.is_howto(residual)
    words = set(_TOKEN_RE.findall(residual.lower()))
    if not words & _HOWTO_INTENT or words & {"about", "tell", "what", "which", "where", "when", "why"}:
        return False
    return set(tokenize_query(residual)) <= _HOWTO_EXTRA


def expand_query(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        out.append(t)
        out.extend(SYNONYMS.get(t, ()))
    return out


def split_species(question: str) -> tuple[tuple[str, ...], str]:
    """(species slugs named in the question, the question with those names
    removed). Slugs are ordered longest-alias-first, which puts a specific
    name ("white crappie") ahead of a family one ("crappie")."""
    text = question.lower()
    # Names are matched on a copy with the unguided fish blanked out, so
    # "red drum" never routes to freshwater drum, but the residual keeps
    # them ("smallmouth" in "smallmouth vs largemouth" is still a word the
    # black bass comparison can be found by).
    masked = mask_unguided(text)
    found: list[str] = []
    for pattern, slugs in _ALIAS_PATTERNS:
        spans = [m.span() for m in pattern.finditer(masked)]
        if spans:
            for slug in slugs:
                if slug not in found:
                    found.append(slug)
            for start, end in reversed(spans):
                masked = masked[:start] + " " * (end - start) + masked[end:]
                text = text[:start] + " " * (end - start) + text[end:]
    for name, slugs in _ZH_ALIASES:
        start = masked.find(name)
        while start != -1:
            for slug in slugs:
                if slug not in found:
                    found.append(slug)
            end = start + len(name)
            masked = masked[:start] + " " * len(name) + masked[end:]
            text = text[:start] + " " * len(name) + text[end:]
            start = masked.find(name)
    return tuple(found), text


# What an empty result means. Ask turns these into different answers: a
# question that was never searched is not the same as one the guides have
# nothing for, and saying so is more honest than one "not covered" for both.
EMPTY_OFF_TOPIC = "off_topic"  # read as not a fishing question, or not understood
EMPTY_UNGUIDED_FISH = "unguided_fish"  # a fish with no guide ("smallmouth", "红鼓鱼")
EMPTY_NOT_COVERED = "not_covered"  # a fishing question the guides don't answer


def mask_unguided(text: str) -> str:
    """`text` with the fish that have no guide blanked out, keeping offsets.
    Everything that matches a name afterwards is matching the real name, not
    a piece of a longer one: the "bass" of "smallmouth bass" never counts."""
    for pattern in _UNGUIDED_PATTERNS:
        text = pattern.sub(lambda m: "#" * len(m.group()), text)
    for name in _ZH_UNGUIDED:
        text = text.replace(name, "#" * len(name))
    return text


def ambiguous_matches(text: str) -> list[tuple[str, AmbiguousName]]:
    """Every AMBIGUOUS_ALIASES name in `text`, longest alias first."""
    masked = mask_unguided(text)
    return [(alias, name) for alias, pattern, name in _AMBIGUOUS_PATTERNS if pattern.search(masked)]


def _strip(text: str, alias: str) -> str:
    return re.sub(rf"\b{re.escape(alias)}\b", " ", text)


def about_the_fish_by_rule(question: str, alias: str, name: AmbiguousName) -> bool:
    """The fallback described on AmbiguousName, used when the embedding
    model isn't installed."""
    rest = _strip(question.lower(), alias)
    if set(_TOKEN_RE.findall(rest)) & name.everyday:
        return False
    if name.fish_by_default:
        return True
    return is_on_topic(rest) or bool(split_species(rest)[0])


def resolve_species(
    question: str,
    decide: Callable[[str, str, AmbiguousName], bool] = about_the_fish_by_rule,
) -> tuple[tuple[str, ...], str]:
    """split_species, plus the ambiguous nicknames `decide` accepts.

    `decide(question, alias, name) -> bool`; the default is the rule above,
    and HybridRetriever passes one that uses the model instead. Either way
    the alias leaves the residual, so it never also ranks as a word."""
    named, residual = split_species(question)
    for alias, name in ambiguous_matches(residual):
        if decide(question, alias, name):
            named += tuple(slug for slug in name.slugs if slug not in named)
        residual = _strip(residual, alias)
    return named, residual


def explain_empty(question: str, named: tuple[str, ...], species: tuple[str, ...] | None) -> str:
    """Why a search came back empty (EMPTY_*), for Ask's answer."""
    if named or species:
        return EMPTY_NOT_COVERED
    if names_unguided_fish(question):
        return EMPTY_UNGUIDED_FISH
    if not is_on_topic(question):
        return EMPTY_OFF_TOPIC
    return EMPTY_NOT_COVERED


def unguided_fish_named(question: str) -> str | None:
    """The first fish-with-no-guide named in the question, as written, so
    Ask can say which one it means ("no guide for smallmouth bass yet")."""
    text = question.lower()
    for pattern in _UNGUIDED_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group()
    return next((n for n in _ZH_UNGUIDED if n in text), None)


def names_unguided_fish(question: str) -> bool:
    return unguided_fish_named(question) is not None


def detect_species(question: str) -> tuple[str, ...]:
    return split_species(question)[0]


# Order used when a question names a fish and nothing else ("tell me about
# bluegill"): there are no words left to rank on, so show the passages a
# beginner needs first.
SECTION_ORDER = (
    "overview",
    "diet",
    "where_and_when",
    "live_baits",
    "lures",
    "setup",
    "identification",
    "habitat",
    "habits",
    "why_these_baits",
    "how_to_get",
    "bait_for",
    "tips",
    "eating",
    "bait_rules",
)


# Questions about the angler rather than the fish, even when a fish is
# named: "how do I hold a catfish without getting stabbed" is answered by
# the handbook, not by three catfish guides (docs/adr/0026). The best
# shared passage leads instead of filling a leftover slot.
_SHARED_FIRST_WORDS = frozenset(
    """legal illegal law laws allowed regulation rule permit license licence
    spine barb stabbed stab stung sting hurt safe safety jacket drown
    backlash cast casting drag knot tie""".split()
)


def _section_rank(p: Passage) -> int:
    base = p.section.split("-")[0]
    return SECTION_ORDER.index(base) if base in SECTION_ORDER else len(SECTION_ORDER)


def _interleave(hits: list[ScoredPassage], k: int) -> list[ScoredPassage]:
    """Round-robin across species, strongest species first.

    "What gear for catfish" is about two fish; plain top-k hands all four
    slots to whichever one's passages happen to score a little higher, and
    the answer silently covers only blue catfish. Hits must already be
    sorted best-first."""
    groups: dict[str, list[ScoredPassage]] = {}
    for h in hits:
        groups.setdefault(h.passage.species_slug, []).append(h)
    # dict order = order of each group's best hit. The shared bait rules
    # only fill slots the fish themselves left empty, so they never displace
    # the fish the question was about.
    shared = groups.pop(SHARED_SLUG, [])
    queues = list(groups.values())
    out: list[ScoredPassage] = []
    while len(out) < k and any(queues):
        for q in queues:
            if q and len(out) < k:
                out.append(q.pop(0))
    return out + shared[: k - len(out)]


def arrange_routed(hits: list[ScoredPassage], query: list[str], k: int) -> list[ScoredPassage]:
    """Top k of a routed search's hits (sorted best-first): one fish after
    another, shared passages filling what's left."""
    if not hits:
        return []
    if _SHARED_FIRST_WORDS & set(query):
        # "Is it legal to use a small bass as bait", "how do I hold a
        # catfish without getting stabbed": the answer is a rule or a
        # handling technique, both of which live in the shared passages.
        shared = [h for h in hits if h.passage.species_slug == SHARED_SLUG][:1]
        rest = [h for h in hits if h not in shared]
        return shared + _interleave(rest, k - len(shared))
    return _interleave(hits, k)


@dataclass(frozen=True)
class ScoredPassage:
    passage: Passage
    score: float


class Retriever(Protocol):
    def search(
        self, question: str, k: int = 4, species: tuple[str, ...] | None = None
    ) -> list[ScoredPassage]: ...

    def why_empty(self, question: str, species: tuple[str, ...] | None = None) -> str:
        """One of the EMPTY_* reasons, for an empty `search`."""
        ...


class BM25Retriever:
    def __init__(self, passages: list[Passage]) -> None:
        self.passages = passages
        self._docs = [Counter(tokenize(p.text)) for p in passages]
        self._lengths = [sum(d.values()) for d in self._docs]
        self._avg_len = sum(self._lengths) / len(self._lengths)
        df: Counter[str] = Counter()
        for d in self._docs:
            df.update(d.keys())
        n = len(passages)
        # BM25+ style idf floor at 0: a term in most passages adds nothing,
        # rather than a negative amount.
        self._idf = {t: max(0.0, math.log((n - f + 0.5) / (f + 0.5) + 1)) for t, f in df.items()}

    def _score(self, i: int, query: list[str]) -> float:
        doc, length = self._docs[i], self._lengths[i]
        score = 0.0
        for term in query:
            tf = doc.get(term, 0)
            if tf == 0:
                continue
            denom = tf + K1 * (1 - B + B * length / self._avg_len)
            score += self._idf.get(term, 0.0) * tf * (K1 + 1) / denom
        return score

    def search(
        self, question: str, k: int = 4, species: tuple[str, ...] | None = None
    ) -> list[ScoredPassage]:
        """Top-k passages, best first; empty means "the guides don't cover this".

        Routing: fish named in the question win; otherwise `species` (the
        page the question was asked from) is used. Once the search is
        limited to those fish, their names are dropped from the query —
        every routed passage is about that fish already, so the name only
        rewards passages that happen to repeat it.

        Once routed, the search never widens. A question that names a fish
        but matches none of that fish's passages gets an empty result (the
        "not covered" answer), not the best matches from other fish.
        Widening used to be the fallback, and it answered "how do I tell
        white bass from hybrid striped bass" — which no guide covers — with
        the threadfin shad bait list, because that passage happens to say
        "striped bass and hybrid striped bass". Retrieval only reaches this
        point when a name *was* recognised, so there is no misread nickname
        to recover from; an unrecognised name never routes and is searched
        across the whole index below.
        """
        named, residual = self.resolve(question)
        routed = named or species or ()

        if routed:
            allowed = set(routed) | {SHARED_SLUG}
            if is_howto(residual if named else question):
                return self.howto(routed[0], k)
            query = query_terms(question, residual, named)
            if not query:
                return self._by_section(routed, k)
            hits = self._rank(query, allowed)
            if not hits and wants_howto(residual if named else question):
                return self.howto(routed[0], k)
            return arrange_routed(hits, query, k)

        if not is_on_topic(question) or names_unguided_fish(question):
            return []
        query = query_terms(question, question, ())
        return self._rank(query, None)[:k] if query else []

    def resolve(self, question: str) -> tuple[tuple[str, ...], str]:
        """Which fish the question is about. HybridRetriever overrides the
        ambiguous-nickname half of this with the model."""
        return resolve_species(question)

    def why_empty(self, question: str, species: tuple[str, ...] | None = None) -> str:
        return explain_empty(question, self.resolve(question)[0], species)

    def howto(self, slug: str, k: int) -> list[ScoredPassage]:
        """Bait, lures, a rig, where and when, for one fish. Score 0.0 like
        _by_section: chosen by section, not by text match."""
        by_section = {p.section: p for p in self.passages if p.species_slug == slug}
        out: list[ScoredPassage] = []
        for choices in HOWTO_SECTIONS:
            passage = next((by_section[c] for c in choices if c in by_section), None)
            if passage:
                out.append(ScoredPassage(passage, 0.0))
        return out[:k]

    def _rank(self, query: list[str], allow: set[str] | None) -> list[ScoredPassage]:
        hits = [
            ScoredPassage(p, self._score(i, query))
            for i, p in enumerate(self.passages)
            if allow is None or p.species_slug in allow
        ]
        hits = [h for h in hits if h.score > 0]
        # Stable tiebreak on id keeps results (and the eval) deterministic.
        hits.sort(key=lambda h: (-h.score, h.passage.id))
        return hits

    def _by_section(self, species: tuple[str, ...], k: int) -> list[ScoredPassage]:
        """Score 0.0 on purpose: these are ordered by SECTION_ORDER, not by
        any text match, and a trace reader should be able to tell."""
        chosen = [p for p in self.passages if p.species_slug in species]
        chosen.sort(key=lambda p: (_section_rank(p), species.index(p.species_slug), p.id))
        return _interleave([ScoredPassage(p, 0.0) for p in chosen], k)


_bm25: BM25Retriever | None = None
_default: Retriever | None = None


def bm25_retriever() -> BM25Retriever:
    """The keyword index, built once per process — the guides only change
    with a deploy, so there is nothing to invalidate."""
    global _bm25
    if _bm25 is None:
        _bm25 = BM25Retriever(build_passages())
    return _bm25


def default_retriever() -> Retriever:
    """What Ask searches with: keyword + semantic when the embedding model is
    installed and RAG_SEMANTIC isn't "off" (docs/adr/0025), keyword alone
    otherwise. Decided once per process."""
    global _default
    if _default is None:
        from app.core.config import get_settings

        mode = get_settings().rag_semantic
        _default = bm25_retriever()
        if mode != "off":
            from app.services.rag.embeddings import load_embedder

            # load_embedder returns None (and logs why) when the semantic
            # packages or the model files are missing; hybrid.py needs numpy,
            # so it is only imported once an embedder has loaded.
            embedder = load_embedder()
            if embedder is not None:
                from app.services.rag.hybrid import HybridRetriever

                _default = HybridRetriever(bm25_retriever(), embedder)
            elif mode == "on":
                raise RuntimeError("RAG_SEMANTIC=on but the embedding model could not be loaded")
    return _default
