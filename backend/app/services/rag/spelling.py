"""Misspelled fishing words in an English question.

"waht bate for catfsh" used to come back as not a fishing question. A word
nothing in the guides contains is replaced by the fishing word it's one slip
from. Every other word is left alone: a real word is never a typo, so "salon"
stays "salon" and "tell me a story" doesn't become a question about storms. Only
what is searched changes, never the question as shown.
"""
from __future__ import annotations

import difflib
import re
from functools import lru_cache

from app.services.rag.chunking import build_passages
from app.services.rag.retriever import AMBIGUOUS_TERMS, FISHING_TERMS, SPECIES_ALIASES

_WORD = re.compile(r"[A-Za-z]+")
# Too short for closeness to mean anything: the misspellings people actually make.
_SHORT = {"bate": "bait", "baite": "bait", "lour": "lure", "lurre": "lure", "hok": "hook", "hoook": "hook", "fsh": "fish", "fishin": "fishing"}
MIN_LENGTH = 5
CUTOFF = 0.8

# What a word may be corrected to: words that only mean fishing. Not every word
# of FISHING_TERMS: "white", "state", "cover" and "storm" are one slip from
# "write", "stale", "comer" and "story".
_TARGETS = tuple(sorted(frozenset("""
    appaloosa barfish bigmouth bluegill bluegills bronzeback bronzebacks brookie brookies bucketmouth bucketmouths
    bullhead bullheads bullpout catfish catfishing chinkapin chinquapin crappie crappies cutthroat flathead flatheads
    gaspergou gizzard guadalupe kokanee lahontan largemouth lineside linesides opelousas papermouth perch redear redears
    salmon sandbass shellcracker shellcrackers shovelhead smallie smallies smallmouth smallmouths striper stripers
    sturgeon sunfish sunperch threadfin trout walleye walleyes warmouth whiskerfish muskellunge muskie steelhead sauger
    bowfin longear panfish angler angling baitcaster baitcasting baitfish bobber boilie bowfishing buzzbait canoe canoes
    crankbait crawdad crawfish crawler crayfish creel dropoff fishing fisherman fishermen fluorocarbon gamefish
    grasshopper hookset hooksets hypothermia invasive jerkbait jighead jugline juglines kayak kayaks license licence
    livewell mealworm minnow monofilament mussel mussels nightcrawler palomar powerbait quagga redworm reservoir shiner
    shrimp sinker spawn spawning spincast spincasting spinner spinnerbait stinkbait stringer swimbait swivel swivels
    tackle tacklebox topwater trotline tungsten waxworm zebco beginner beginners permit
""".split())))

# Real English words one slip from a target, so never corrected. Found by running
# an English spelling dictionary (125,000 words) through fix(): if _TARGETS
# changes, run tools/spelling/real_words.py again.
_REAL_WORDS = frozenset("""
    angelina angeline anger angering angled angles anglings ankling antler appaloosas bandfish batfish beardfish
    bigmouths blobbier bluebill bobbed boffin bomber bookie bookies bowfins broodier broodiest brooke brookes brooking
    brooklet brooklets brookside bulkhead bulkheads bullheaded burrfish canes cannes canoed canoeist canon canoness
    canons canopies catfight catfighting catfishes chappie chappies coalfish cradler crappier crappiest crapping
    crawdads crawled crawlers crawley crawlier crawlies crayfished crayfishes crayfishing creed creels creep crees
    crenel crewel cruel cutthroats faithing famishing fatheads filching finishing fishings flashing flatbeds flatbread
    flatbreads fleshing fluorocarbons flushing foisting frisking gizzards guadeloupe hyperthermia hypothermal
    hypothermias hypothermic juggling licences licensee licensees licenser licensor longhair longueur metalwork
    muskellunges muskier muskies muskiest mussed musses parch peach percha percy perth porch powerboat redbeard redcar
    redheads rehear rehears rehearse relearns sager sallie sallies salmons salomon salon saloon salton sandbags
    sandbanks sandbars sandblast sandblasts sanger sauber scrimp shawn shier shine shined shines shinier shoveled
    shovelled shrimped shrimper shrimpers shrimps shriner shrinker shrivels sicker sinner sinter skinner skinners
    skinnier slinkier smallish smallness smelliest snivel snivels spahn spain spanking spanner spanners spanning spinier
    spinnaker spinneret spinney spinneys spinster splinter spraining sprawling springer springers springier sprinter
    stinger stingers stingier stinker stinkers stinkier strainer strainers stranger strangers strangler stricter strider
    strieber striker strikers strimmer strimmers stringed stringent stringers stringier stripey stripier stripped
    stripper strippers striver strivers sturgeons sunfishes surgeons swiveled tackled tackler tacklers tackles threading
    tickle trouts tryout walleyed waxwork waxworks
""".split())


@lru_cache(maxsize=1)
def _known() -> frozenset[str]:
    known: set[str] = set(_TARGETS) | _REAL_WORDS | set(FISHING_TERMS) | set(AMBIGUOUS_TERMS)
    known.update(w for alias in SPECIES_ALIASES for w in alias.split())
    for p in build_passages():
        known.update(w.lower() for w in _WORD.findall(p.text))
    return frozenset(known)


def _slips(a: str, b: str) -> int:
    """How many letters were typed wrong: added, dropped, changed, or two swapped."""
    rows = [[max(i, j) if not (i and j) else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            rows[i][j] = min(rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                rows[i][j] = min(rows[i][j], rows[i - 2][j - 2] + 1)
    return rows[-1][-1]


def fix(question: str) -> str:
    known = _known()

    def repair(match: re.Match[str]) -> str:
        word = match.group(0)
        lowered = word.lower()
        if lowered in _SHORT:
            return _SHORT[lowered]
        if len(lowered) < MIN_LENGTH or lowered in known:
            return word
        # A typo rarely gets the first letter wrong, and this keeps the guesses few.
        close = difflib.get_close_matches(lowered, [t for t in _TARGETS if t[0] == lowered[0]], n=1, cutoff=CUTOFF)
        if close and _slips(lowered, close[0]) <= (1 if len(lowered) <= 7 else 2):
            return close[0]
        return word

    return _WORD.sub(repair, question)
