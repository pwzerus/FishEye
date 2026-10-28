"""Named OpenStreetMap water with no water=* tag: is it a lake?

docs/adr/0036-untyped-named-water.md; the rules are also the skill
docs/skills/fisheye-osm-lakes/SKILL.md, which must change with this file.

`natural=water` says only "there is water here". Mappers add `water=lake`,
`reservoir`, `pond`, `river`, `canal`, `wastewater`… to say what kind. Older
and bulk-imported water often has no `water=*` at all: in Minnesota 7,409
named elements against 2,228 tagged as lakes, reservoirs or ponds. Such water
is imported only when its name says it is a lake and nothing says otherwise.
Each rule below either keeps it or gives the reason it is left out; the
first rule that fails decides.

1. tags        no tag says it is something else: intermittent or seasonal,
               salt, tidal, a swimming pool or water park, a fountain, a
               basin, any man_made, golf, covered or underground, disused or
               abandoned, a wetland, a zoo, theme park or attraction.
2. not_fishing no word in the name says it is not water to fish: retention,
               detention, stormwater, wastewater, sewage, treatment, settling,
               sediment, tailings, waste, industrial, acid, drainage,
               evaporation, swimming, golf, "fire pond", "cooling pond", "koi
               pond", "lakebed", "(historical)", "dry lake" and the like
               (NOT_FISHING).
   facility    a name with a facility word (club, school, cemetery, church,
               hospital, prison, inn, hotel, estates, apartments, mall,
               office, plant, airport, zoo…; FACILITY_NAMES) is the water of
               a facility, and left out, when either
               - OpenStreetMap maps that kind of facility within
                 FACILITY_NEAR_M of the water (FACILITY_TAGS; found by
                 geofabrik_lakes.extract, passed in as `facilities_near`):
                 "Athens Country Club Lake" beside a golf course; or
   facility_name - the name names one particular facility: a proper name
                 before the facility word ("Salisbury School Pond",
                 "Fin and Feathers Club Lake", "Lakeside Estates Lake"),
                 even where OpenStreetMap hasn't mapped it — unless that
                 phrase is a place mapped nearby (`places_near`: "Ball
                 Club Lake" by the town of Ball Club, Minnesota).
               A facility word leading the name is a place name and stays:
               "School Lake" (often a school land section), "Church Lake",
               "Lower Church Lake", "Club Lake", "Lake Seminary". Without the
               nearby check (an older payload) every facility name goes.
3. not_lake    the name's head word is a lake word (LAKE_WORDS): "Mud Lake",
               "Hay Creek Flowage", "Colton Flow", "Whortleberry Pond"; or it
               starts with "Lake"/"Lago"/"Loch", perhaps behind a qualifier
               ("West Lake Ellen"), and does not end in another kind of water
               or place ("Lake Butler" yes, "Lake Creek", "Lake Shore Pool" no).
               "Smith Tank", "Pine River", "Mallard Marsh", "Blue Hole" are
               left out: the name doesn't say lake.
4. generic     after the lake word, numbering ("#2", "No. 3", "A", "II") and
               "the"/"of", something is left: "Pond 3", "The Pond", "Lake A"
               are left out.

What passes is still subject to the importer's other rules: the private-name
and access rules, the minimum size (200 m across for a lake or reservoir,
50 m for a pond), the state outline, and merging with other pieces of the
same lake.
"""
from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass

# Head words that say "lake", and the water_type each one gives.
LAKE_WORDS: dict[str, str] = {
    "lake": "lake",
    "lakes": "lake",
    "pond": "pond",
    "ponds": "pond",
    "reservoir": "reservoir",
    "reservoirs": "reservoir",
    "flowage": "lake",
    # Adirondack impoundments: "Colton Flow".
    "flow": "reservoir",
    "impoundment": "reservoir",
}
# "Lake Butler", "Lago Vista", "Loch Sheldrake": a lake word first, the name
# after it, perhaps behind a qualifier ("West Lake Ellen", "Upper Lake Mary").
LEADING_LAKE_WORDS = {"lake", "lago", "loch", "reservoir"}
QUALIFIERS = {
    "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest",
    "upper", "lower", "middle", "little", "big", "old", "new", "inner", "outer",
}

# A name ending in one of these is another kind of water or a place, even
# when it starts with "Lake" ("Lake Creek", "Lake Shore Pool").
OTHER_HEADS = {
    "river", "creek", "brook", "run", "branch", "fork", "stream", "kill",
    "canal", "ditch", "channel", "drain", "raceway", "flume",
    "bayou", "slough", "marsh", "swamp", "bog", "fen", "wetland", "wetlands",
    "lagoon", "bay", "harbor", "harbour", "marina", "inlet", "cove", "sound", "estuary",
    "pool", "pools", "fountain", "basin", "cistern", "tank", "spring", "springs",
    "falls", "dam", "park", "trail", "beach", "island", "point", "outlet",
}

NOT_FISHING = re.compile(
    r"\b("
    r"retention|detention|storm\s*water|storm\s+(?:pond|basin|drain)|"
    r"waste\s*water|sewage|sewer|septic|treatment|effluent|sludge|clarifier|leachate|"
    r"settling|sediment(?:ation)?|silt|tailings?|slurry|slimes|"
    r"waste|industrial|acid|drainage|catch\s+(?:pond|basin)|"
    r"evaporation|infiltration|percolation|"
    r"swimming|splash|water\s*park|aquarium|exhibit|golf|water\s+hazard|hole\s+\d+|"
    r"(?:fire|cooling|holding|koi|ash|reflecting|ornamental|decorative)\s+(?:pond|pool|basin)|"
    r"lake\s*bed|lakebed|historical|drained|former|dry\s+lakes?"
    r")\b",
    re.I,
)

# Water at a facility (a club, school, cemetery, hotel, housing development,
# office, plant) is not a place people go to fish, and is often private
# ground. But many such names are only place names: "Church Lake", "School
# Lake" (a school land section), "Lake Seminary". So a facility word counts
# only when OpenStreetMap maps that kind of facility near the water.
# Each kind: the words that name it, and the OSM tags that map it (None:
# any value).
FACILITY_NAMES: dict[str, str] = {
    "club": r"clubs?|country\s+club",
    "education": r"schools?|college|university|campus|academy|seminary",
    "cemetery": r"cemetery|cemeteries|memorial\s+gardens?",
    "worship": r"church|chapel|monastery|convent",
    "health": r"hospital|sanitarium|sanatorium",
    "prison": r"prison|correctional",
    "lodging": r"inn|hotel|motel|resort",
    "housing": r"estates?|subdivision|homeowners?|hoa|apartments?|condos?|condominiums?|townhomes?",
    "commerce": r"mall|plaza|shopping|offices?|corporate|business\s+park",
    "industry": r"plant",
    # "Factory Pond", "Tack Factory Pond": mostly 19th-century mill ponds. A
    # working factory is mapped (landuse=industrial), so only that counts.
    "factory": r"factory",
    "airport": r"airport",
    "zoo": r"zoo",
    "museum": r"museum",
}
FACILITY_TAGS: dict[str, tuple[tuple[str, str | None], ...]] = {
    "club": (("club", None), ("leisure", "golf_course"), ("leisure", "sports_centre"), ("sport", "shooting")),
    "education": (("amenity", "school"), ("amenity", "college"), ("amenity", "university"),
                  ("amenity", "kindergarten"), ("landuse", "education")),
    "cemetery": (("landuse", "cemetery"), ("amenity", "grave_yard")),
    "worship": (("amenity", "place_of_worship"), ("amenity", "monastery"), ("landuse", "religious")),
    "health": (("amenity", "hospital"), ("amenity", "clinic"), ("healthcare", "hospital")),
    "prison": (("amenity", "prison"),),
    "lodging": (("tourism", "hotel"), ("tourism", "motel"), ("tourism", "guest_house"), ("tourism", "hostel"),
                ("tourism", "chalet"), ("leisure", "resort")),
    "housing": (("landuse", "residential"), ("place", "neighbourhood"), ("place", "suburb"), ("place", "quarter")),
    "commerce": (("shop", "mall"), ("landuse", "retail"), ("landuse", "commercial"), ("office", None)),
    "industry": (("landuse", "industrial"), ("man_made", "works"), ("man_made", "water_works"),
                 ("man_made", "wastewater_plant"), ("power", "plant")),
    "airport": (("aeroway", "aerodrome"),),
    "zoo": (("tourism", "zoo"),),
    "museum": (("tourism", "museum"),),
}
FACILITY_TAGS["factory"] = FACILITY_TAGS["industry"]
# Kinds a facility word names only when that facility is mapped near (rule
# a), never by a proper name before it (rule b).
MAPPED_ONLY = {"factory"}
# How far from the water's bounding box the facility may be mapped.
FACILITY_NEAR_M = 300.0
# How far a settlement named in the water's name may be ("Little Ball Club
# Lake" is 10 km from the hamlet of Ball Club). Neighbourhoods don't count:
# "Winter Valley Estates" is the housing estate itself.
PLACE_NEAR_M = 20_000.0
PLACE_VALUES = ("city", "town", "village", "hamlet", "locality")
_FACILITY_RES = {kind: re.compile(rf"\b({words})\b", re.I) for kind, words in FACILITY_NAMES.items()}


def named_facilities(name: str) -> set[str]:
    """The kinds of facility a name names: "Salisbury School Pond" → {"education"}."""
    return {kind for kind, rx in _FACILITY_RES.items() if rx.search(name)}


def facility_kinds(tags: Mapping[str, str]) -> set[str]:
    """The kinds of facility an OSM feature with these tags is."""
    return {
        kind
        for kind, pairs in FACILITY_TAGS.items()
        if any(key in tags and (value is None or tags[key] == value) for key, value in pairs)
    }

_YES = {"yes", "true", "1"}


def _tag_reason(tags: Mapping[str, str]) -> str | None:
    def yes(key: str) -> bool:
        return tags.get(key, "").strip().lower() in _YES

    if yes("intermittent") or yes("seasonal"):
        return "intermittent"
    if yes("salt") or yes("tidal"):
        return "salt_or_tidal"
    if tags.get("leisure") in {"swimming_pool", "water_park", "swimming_area"} or tags.get("amenity") == "fountain":
        return "pool_or_fountain"
    if tags.get("landuse") == "basin" or "basin" in tags or "man_made" in tags:
        return "man_made"
    if "golf" in tags:
        return "golf"
    if yes("covered") or tags.get("location") in {"underground", "indoor"}:
        return "covered"
    if yes("disused") or yes("abandoned") or any(
        k.startswith(("disused:", "abandoned:", "was:", "demolished:", "razed:")) for k in tags
    ):
        return "disused"
    if "wetland" in tags:
        return "wetland"
    if tags.get("tourism") in {"zoo", "theme_park", "aquarium"} or "zoo" in tags or "attraction" in tags:
        return "attraction"
    return None


_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_NUMBERING = re.compile(
    r"^(?:\d+[a-z]?|[a-z]|[ivx]+|no|number|num|one|two|three|four|five|six|seven|eight|nine|ten)$"
)
_FILLER = {"the", "of", "a"}


def name_words(name: str) -> list[str]:
    # Parentheticals are notes ("Argo Lake (Hamilton County)"); drop them.
    return _WORD.findall(re.sub(r"\([^)]*\)", " ", name).lower())


@dataclass(frozen=True)
class Verdict:
    # lake | reservoir | pond when the water is kept; None when left out.
    water_type: str | None
    # "ok", or why it is left out: one of the rule names above, or a tag reason.
    reason: str


def contains_words(words: list[str], part: list[str]) -> bool:
    return any(words[i:i + len(part)] == part for i in range(len(words) - len(part) + 1))


def names_one_facility(name: str, places_near: Collection[str] = ()) -> bool:
    """Does the name name one particular facility, a proper name before the
    facility word ("Salisbury School Pond", "Fin and Feathers Club Lake")?
    Not when the facility word leads ("School Lake", "Lower Church Lake",
    "Lake Seminary"), nor when the words are a place mapped nearby ("Ball
    Club Lake" by Ball Club, Minnesota), nor for a MAPPED_ONLY kind. A
    housing word is never rescued by a place: the estate is the place."""
    matches = [(kind, m) for kind, rx in _FACILITY_RES.items() if (m := rx.search(name))]
    if not matches:
        return False
    kind, first = min(matches, key=lambda km: km[1].start())
    if kind in MAPPED_ONLY:
        return False
    before = [w for w in name_words(name[: first.start()])
              if w not in QUALIFIERS and w not in LAKE_WORDS and w not in LEADING_LAKE_WORDS and w not in _FILLER]
    if not before:
        return False
    words, facility_words = name_words(name), name_words(first.group(0))
    for place in () if kind == "housing" else places_near:
        place_words = name_words(place)
        if contains_words(words, place_words) and set(facility_words) & set(place_words):
            return False
    return True


def judge(
    name: str,
    tags: Mapping[str, str],
    facilities_near: Collection[str] | None = None,
    places_near: Collection[str] = (),
) -> Verdict:
    """Is this named, untyped natural=water a lake FishEye should show?

    `facilities_near`: the kinds of facility mapped near the water, or None
    when nobody checked; `places_near`: names of places mapped near it (both
    from geofabrik_lakes.extract, for names with a facility word)."""
    reason = _tag_reason(tags)
    if reason:
        return Verdict(None, reason)
    if NOT_FISHING.search(name):
        return Verdict(None, "not_fishing")
    named = named_facilities(name)
    if named and (facilities_near is None or named & set(facilities_near)):
        return Verdict(None, "facility")
    if named and names_one_facility(name, places_near):
        return Verdict(None, "facility_name")
    words = name_words(name)
    # Trailing numbering is not the head word: "Jesse McNeel Lake Number 2".
    while words and (_NUMBERING.match(words[-1]) or words[-1] in _FILLER):
        words.pop()
    if not words:
        return Verdict(None, "not_lake")
    lead = 0
    while lead < len(words) - 1 and words[lead] in QUALIFIERS:
        lead += 1
    if words[-1] in LAKE_WORDS:
        water_type = LAKE_WORDS[words[-1]]
    elif words[lead] in LEADING_LAKE_WORDS and len(words) > lead + 1 and words[-1] not in OTHER_HEADS:
        water_type = LAKE_WORDS.get(words[lead], "lake")
    else:
        return Verdict(None, "not_lake")
    rest = [w for w in words if w not in LAKE_WORDS and w not in LEADING_LAKE_WORDS
            and w not in _FILLER and not _NUMBERING.match(w)]
    if not rest:
        return Verdict(None, "generic")
    return Verdict(water_type, "ok")
