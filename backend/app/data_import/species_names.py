"""One name per fish, whatever a source calls it.

Agency datasets write the same fish many ways: "Bass, Largemouth" (TPWD and
Georgia record lists), "bass, largemouth" (CDFW's record list), "Large mouth
bass" (CDFW ds102), "Rainbow Trout" (CDFW's stocking plan). `canonical()`
turns any of them into the name FishEye stores (Species.common_name) and its
scientific name.

The canonical name is the species guide's name where there is a guide
(app/knowledge/species_guides.py), so those link to "how to catch it". Other
fish anglers target are kept under their usual name with no guide. Minnows,
dace, suckers, hybrids between species and "unknown" are not mapped: the
importers count them as skipped rather than guess.
"""
from __future__ import annotations

import re

# canonical common name -> scientific name. Guide species first.
SPECIES: dict[str, str] = {
    "Largemouth Bass": "Micropterus salmoides",
    "Smallmouth Bass": "Micropterus dolomieu",
    "Spotted Bass": "Micropterus punctulatus",
    "Guadalupe Bass": "Micropterus treculii",
    "White Bass": "Morone chrysops",
    "Striped Bass": "Morone saxatilis",
    "Hybrid Striped Bass": "Morone saxatilis × Morone chrysops",
    "Channel Catfish": "Ictalurus punctatus",
    "Blue Catfish": "Ictalurus furcatus",
    "Flathead Catfish": "Pylodictis olivaris",
    "White Crappie": "Pomoxis annularis",
    "Black Crappie": "Pomoxis nigromaculatus",
    "Bluegill": "Lepomis macrochirus",
    "Redear Sunfish": "Lepomis microlophus",
    "Gizzard Shad": "Dorosoma cepedianum",
    "Threadfin Shad": "Dorosoma petenense",
    "Rainbow Trout": "Oncorhynchus mykiss",
    "Freshwater Drum": "Aplodinotus grunniens",
    "Common Carp": "Cyprinus carpio",
    # No guide yet.
    "Alabama Bass": "Micropterus henshalli",
    "Shoal Bass": "Micropterus cataractae",
    "Redeye Bass": "Micropterus coosae",
    "Suwannee Bass": "Micropterus notius",
    "Rock Bass": "Ambloplites rupestris",
    "Yellow Bass": "Morone mississippiensis",
    "Brown Trout": "Salmo trutta",
    "Brook Trout": "Salvelinus fontinalis",
    "Lake Trout": "Salvelinus namaycush",
    "Bull Trout": "Salvelinus confluentus",
    "Golden Trout": "Oncorhynchus mykiss aguabonita",
    "Cutthroat Trout": "Oncorhynchus clarkii",
    "Lahontan Cutthroat Trout": "Oncorhynchus clarkii henshawi",
    "Kokanee Salmon": "Oncorhynchus nerka",
    "Chinook Salmon": "Oncorhynchus tshawytscha",
    "Coho Salmon": "Oncorhynchus kisutch",
    "Arctic Grayling": "Thymallus arcticus",
    "Mountain Whitefish": "Prosopium williamsoni",
    "White Catfish": "Ameiurus catus",
    "Brown Bullhead": "Ameiurus nebulosus",
    "Yellow Bullhead": "Ameiurus natalis",
    "Black Bullhead": "Ameiurus melas",
    "Green Sunfish": "Lepomis cyanellus",
    "Pumpkinseed": "Lepomis gibbosus",
    "Warmouth": "Lepomis gulosus",
    "Redbreast Sunfish": "Lepomis auritus",
    "Longear Sunfish": "Lepomis megalotis",
    "Spotted Sunfish": "Lepomis punctatus",
    "Flier": "Centrarchus macropterus",
    "Sacramento Perch": "Archoplites interruptus",
    "Yellow Perch": "Perca flavescens",
    "Walleye": "Sander vitreus",
    "Sauger": "Sander canadensis",
    "Northern Pike": "Esox lucius",
    "Muskellunge": "Esox masquinongy",
    "Chain Pickerel": "Esox niger",
    "Redfin Pickerel": "Esox americanus",
    "Longnose Gar": "Lepisosteus osseus",
    "Spotted Gar": "Lepisosteus oculatus",
    "Shortnose Gar": "Lepisosteus platostomus",
    "Alligator Gar": "Atractosteus spatula",
    "Bowfin": "Amia calva",
    "Smallmouth Buffalo": "Ictiobus bubalus",
    "Bigmouth Buffalo": "Ictiobus cyprinellus",
    "Grass Carp": "Ctenopharyngodon idella",
    "American Shad": "Alosa sapidissima",
    "Hickory Shad": "Alosa mediocris",
    "Sacramento Pikeminnow": "Ptychocheilus grandis",
    "Striped Mullet": "Mugil cephalus",
    "Tilapia": "Oreochromis spp.",
    # Stocking schedules that name only the kind of fish (CDFW's Fish
    # Planting Schedule says "Trout" or "Catfish"). Kept as what they are,
    # never turned into a species the source didn't name.
    "Trout": "Salmonidae (species not given)",
    "Catfish": "Ictaluridae (species not given)",
}

# Extra spellings, written already normalised (see _norm): lower case, no
# punctuation, "family, kind" turned around to "kind family".
_ALIASES: dict[str, str] = {
    "large mouth bass": "Largemouth Bass",
    "florida largemouth bass": "Largemouth Bass",
    "small mouth bass": "Smallmouth Bass",
    "spotted alabama bass": "Spotted Bass",
    "hybrid bass": "Hybrid Striped Bass",
    "hybrid striped bass": "Hybrid Striped Bass",
    "striped white bass hybrid": "Hybrid Striped Bass",
    "sunshine bass": "Hybrid Striped Bass",
    "palmetto bass": "Hybrid Striped Bass",
    "black crappie": "Black Crappie",
    "white crappie": "White Crappie",
    "bluegill sunfish": "Bluegill",
    "redear sunfish": "Redear Sunfish",
    "shellcracker": "Redear Sunfish",
    "green sunfish": "Green Sunfish",
    "pumpkinseed sunfish": "Pumpkinseed",
    "warmouth sunfish": "Warmouth",
    "flier sunfish": "Flier",
    "shadow bass sunfish": "Rock Bass",
    "sacramento perch sunfish": "Sacramento Perch",
    "redbreast sunfish": "Redbreast Sunfish",
    "longear sunfish": "Longear Sunfish",
    "spotted sunfish": "Spotted Sunfish",
    "brown bullhead catfish": "Brown Bullhead",
    "yellow bullhead catfish": "Yellow Bullhead",
    "black bullhead catfish": "Black Bullhead",
    "carp": "Common Carp",
    "carp minnow": "Common Carp",
    "common carp": "Common Carp",
    "grass carp": "Grass Carp",
    "eagle lake trout": "Rainbow Trout",
    "mccloud river redband trout": "Rainbow Trout",
    "redband trout": "Rainbow Trout",
    "rainbow trout": "Rainbow Trout",
    "golden rainbow hybrid": "Rainbow Trout",
    "steelhead rainbow trout": "Rainbow Trout",
    "domestic rainbow trout": "Rainbow Trout",
    "california golden trout": "Golden Trout",
    "golden trout": "Golden Trout",
    "lahontan cutthroat trout": "Lahontan Cutthroat Trout",
    "wild cutthroat trout": "Cutthroat Trout",
    "cutthroat trout": "Cutthroat Trout",
    "brook trout": "Brook Trout",
    "brown trout": "Brown Trout",
    "lake trout": "Lake Trout",
    "mackinaw": "Lake Trout",
    "bull trout": "Bull Trout",
    "kokanee": "Kokanee Salmon",
    "kokanee salmon": "Kokanee Salmon",
    "chinook salmon": "Chinook Salmon",
    "inland chinook salmon": "Chinook Salmon",
    "coho salmon": "Coho Salmon",
    "inland coho salmon": "Coho Salmon",
    "arctic grayling": "Arctic Grayling",
    "mountain whitefish": "Mountain Whitefish",
    "northern pike": "Northern Pike",
    "chain pickerel": "Chain Pickerel",
    "redfin pickerel": "Redfin Pickerel",
    "longnose gar": "Longnose Gar",
    "spotted gar": "Spotted Gar",
    "shortnose gar": "Shortnose Gar",
    "alligator gar": "Alligator Gar",
    "smallmouth buffalo": "Smallmouth Buffalo",
    "bigmouth buffalo": "Bigmouth Buffalo",
    "yellow perch": "Yellow Perch",
    "american shad": "American Shad",
    "hickory shad": "Hickory Shad",
    "sacramento pikeminnow": "Sacramento Pikeminnow",
    "freshwater drum": "Freshwater Drum",
    "white catfish": "White Catfish",
    "trout": "Trout",
    "catfish": "Catfish",
}

_PUNCT = re.compile(r"[^a-z ]+")
# Qualifiers some lists add that don't change which fish it is.
_NOISE = re.compile(r"\b(tie|inland|wild|domestic|all)\b")


def _norm(text: str) -> str:
    """'Bass, Largemouth (TIE)' -> 'largemouth bass'; 'catfish, bullhead,
    brown' -> 'brown bullhead catfish'."""
    t = re.sub(r"\(.*?\)", " ", text.lower())
    parts = [p.strip() for p in t.split(",") if p.strip()]
    t = " ".join(reversed(parts)) if len(parts) > 1 else (parts[0] if parts else "")
    t = _PUNCT.sub(" ", t.replace("/", " "))
    return " ".join(t.split())


_BY_NORM: dict[str, str] = {_norm(name): name for name in SPECIES}
_BY_NORM.update(_ALIASES)


def canonical(raw: str | None) -> tuple[str, str] | None:
    """(common name, scientific name), or None for a fish not mapped here
    (a hybrid of two species, a minnow, "unknown")."""
    if not raw or not raw.strip():
        return None
    key = _norm(raw)
    name = _BY_NORM.get(key) or _BY_NORM.get(" ".join(_NOISE.sub(" ", key).split()))
    if name is None and " x " in f" {key} ":
        return None  # a cross between two species, other than the named hybrids above
    return (name, SPECIES[name]) if name else None


def by_scientific_name(scientific: str | None) -> str | None:
    """Canonical common name for a scientific name ("Micropterus salmoides")."""
    if not scientific:
        return None
    s = " ".join(scientific.lower().split()[:2])
    for name, sci in SPECIES.items():
        if " ".join(sci.lower().split()[:2]) == s and "species not given" not in sci:
            return name
    return None


_FAMILY_WORDS = ("bass", "catfish", "crappie", "sunfish", "trout", "gar", "shad", "buffalo", "bullhead", "perch", "pickerel")
# A list item that names only the kind of fish ("Crappie", "Sunfish").
GENERIC_NAMES = frozenset(w.capitalize() for w in _FAMILY_WORDS)


def species_list(items: list[str]) -> list[str]:
    """An agency's list of fish ("Channel & flathead catfish", "White &
    striped bass", "Sunfish") as FishEye's own list: one canonical name per
    fish, a generic word kept as a word, sorted. Facts survive (which fish);
    the agency's wording and order don't (data-sourcing rule 3)."""
    out: set[str] = set()
    for item in items:
        text = re.sub(r"\(.*?\)", " ", item).strip()
        family = next((w for w in _FAMILY_WORDS if re.search(rf"\b{w}(es)?\s*$", text, re.I)), None)
        parts = [p.strip() for p in re.split(r"\s*(?:&|,|/|\band\b)\s*", text, flags=re.I) if p.strip()]
        for part in parts:
            if family and not re.search(rf"\b{family}", part, re.I):
                part = f"{part} {family}"
            hit = canonical(part)
            out.add(hit[0] if hit else " ".join(w.capitalize() for w in part.split()))
    return sorted(out)
