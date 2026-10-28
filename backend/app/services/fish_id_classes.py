"""What the fish recognizer can answer, and which answers back up a claim.

Plain data, no imports beyond the standard library: the model-building tool
(app/cli/build_fish_id_model.py) runs in its own PyTorch environment and
reads this too, so the classes the model was built with and the ones the
app checks claims against cannot drift apart.

Three kinds of class:
- **guide**: the species FishEye has a guide for, the ones a catch can name;
- **other_fish**: fish an angler may well catch that have no guide. Without
  them a walleye would come out as whichever guide species it looks least
  unlike; with them it comes out as "a walleye, not one of ours";
- **not_fish**: what else a photo at a lake shows. A catch needs a fish.

`group` gathers fish that photos often can't tell apart (a spotted bass from
a largemouth, a channel catfish from a bullhead, a common carp from a grass
carp), guide species and fish with no guide alike. services/fish_id.py uses
it to tell "a different fish altogether" (always refused) from "the same
kind of fish, species unsure" (accepted, with the species marked as the
angler's own call, never as confirmed). Measured: docs/adr/0037.
"""
from __future__ import annotations

from dataclasses import dataclass

GUIDE = "guide"
OTHER_FISH = "other_fish"
NOT_FISH = "not_fish"


@dataclass(frozen=True)
class FishClass:
    slug: str
    common: str
    scientific: str
    # Order and family, as in the GBIF backbone, for BioCLIP's taxonomic prompt.
    order: str
    family: str
    kind: str = GUIDE
    group: str | None = None
    # Shown to people in place of "species not confirmed": what the group is.
    group_label: str | None = None


_ACTINO = "Animalia Chordata Actinopterygii"

CLASSES: tuple[FishClass, ...] = (
    # ---- guide species --------------------------------------------------
    FishClass("largemouth-bass", "Largemouth Bass", "Micropterus salmoides", "Perciformes", "Centrarchidae", group="black-bass", group_label="a black bass"),
    FishClass("smallmouth-bass", "Smallmouth Bass", "Micropterus dolomieu", "Perciformes", "Centrarchidae", group="black-bass", group_label="a black bass"),
    FishClass("spotted-bass", "Spotted Bass", "Micropterus punctulatus", "Perciformes", "Centrarchidae", group="black-bass", group_label="a black bass"),
    FishClass("guadalupe-bass", "Guadalupe Bass", "Micropterus treculii", "Perciformes", "Centrarchidae", group="black-bass", group_label="a black bass"),
    FishClass("white-bass", "White Bass", "Morone chrysops", "Perciformes", "Moronidae", group="temperate-bass", group_label="a white or striped bass"),
    FishClass("striped-bass", "Striped Bass", "Morone saxatilis", "Perciformes", "Moronidae", group="temperate-bass", group_label="a white or striped bass"),
    FishClass("channel-catfish", "Channel Catfish", "Ictalurus punctatus", "Siluriformes", "Ictaluridae", group="catfish", group_label="a catfish"),
    FishClass("blue-catfish", "Blue Catfish", "Ictalurus furcatus", "Siluriformes", "Ictaluridae", group="catfish", group_label="a catfish"),
    FishClass("flathead-catfish", "Flathead Catfish", "Pylodictis olivaris", "Siluriformes", "Ictaluridae", group="flathead-catfish"),
    FishClass("white-crappie", "White Crappie", "Pomoxis annularis", "Perciformes", "Centrarchidae", group="crappie", group_label="a crappie"),
    FishClass("black-crappie", "Black Crappie", "Pomoxis nigromaculatus", "Perciformes", "Centrarchidae", group="crappie", group_label="a crappie"),
    FishClass("bluegill", "Bluegill", "Lepomis macrochirus", "Perciformes", "Centrarchidae", group="sunfish", group_label="a sunfish"),
    FishClass("redear-sunfish", "Redear Sunfish", "Lepomis microlophus", "Perciformes", "Centrarchidae", group="sunfish", group_label="a sunfish"),
    FishClass("gizzard-shad", "Gizzard Shad", "Dorosoma cepedianum", "Clupeiformes", "Clupeidae", group="shad", group_label="a shad"),
    FishClass("threadfin-shad", "Threadfin Shad", "Dorosoma petenense", "Clupeiformes", "Clupeidae", group="shad", group_label="a shad"),
    FishClass("rainbow-trout", "Rainbow Trout", "Oncorhynchus mykiss", "Salmoniformes", "Salmonidae", group="trout", group_label="a trout"),
    FishClass("freshwater-drum", "Freshwater Drum", "Aplodinotus grunniens", "Perciformes", "Sciaenidae", group="freshwater-drum"),
    FishClass("common-carp", "Common Carp", "Cyprinus carpio", "Cypriniformes", "Cyprinidae", group="carp", group_label="a carp"),
    # ---- fish with no guide ---------------------------------------------
    FishClass("walleye", "Walleye", "Sander vitreus", "Perciformes", "Percidae", OTHER_FISH),
    FishClass("sauger", "Sauger", "Sander canadensis", "Perciformes", "Percidae", OTHER_FISH),
    FishClass("yellow-perch", "Yellow Perch", "Perca flavescens", "Perciformes", "Percidae", OTHER_FISH),
    FishClass("white-perch", "White Perch", "Morone americana", "Perciformes", "Moronidae", OTHER_FISH),
    FishClass("northern-pike", "Northern Pike", "Esox lucius", "Esociformes", "Esocidae", OTHER_FISH),
    FishClass("muskellunge", "Muskellunge", "Esox masquinongy", "Esociformes", "Esocidae", OTHER_FISH),
    FishClass("chain-pickerel", "Chain Pickerel", "Esox niger", "Esociformes", "Esocidae", OTHER_FISH),
    FishClass("longnose-gar", "Longnose Gar", "Lepisosteus osseus", "Lepisosteiformes", "Lepisosteidae", OTHER_FISH),
    FishClass("spotted-gar", "Spotted Gar", "Lepisosteus oculatus", "Lepisosteiformes", "Lepisosteidae", OTHER_FISH),
    FishClass("alligator-gar", "Alligator Gar", "Atractosteus spatula", "Lepisosteiformes", "Lepisosteidae", OTHER_FISH),
    FishClass("bowfin", "Bowfin", "Amia calva", "Amiiformes", "Amiidae", OTHER_FISH),
    FishClass("brown-trout", "Brown Trout", "Salmo trutta", "Salmoniformes", "Salmonidae", OTHER_FISH, group="trout"),
    FishClass("brook-trout", "Brook Trout", "Salvelinus fontinalis", "Salmoniformes", "Salmonidae", OTHER_FISH, group="trout"),
    FishClass("cutthroat-trout", "Cutthroat Trout", "Oncorhynchus clarkii", "Salmoniformes", "Salmonidae", OTHER_FISH, group="trout"),
    FishClass("lake-trout", "Lake Trout", "Salvelinus namaycush", "Salmoniformes", "Salmonidae", OTHER_FISH, group="trout"),
    FishClass("green-sunfish", "Green Sunfish", "Lepomis cyanellus", "Perciformes", "Centrarchidae", OTHER_FISH, group="sunfish"),
    FishClass("warmouth", "Warmouth", "Lepomis gulosus", "Perciformes", "Centrarchidae", OTHER_FISH, group="sunfish"),
    FishClass("pumpkinseed", "Pumpkinseed", "Lepomis gibbosus", "Perciformes", "Centrarchidae", OTHER_FISH, group="sunfish"),
    FishClass("redbreast-sunfish", "Redbreast Sunfish", "Lepomis auritus", "Perciformes", "Centrarchidae", OTHER_FISH, group="sunfish"),
    FishClass("longear-sunfish", "Longear Sunfish", "Lepomis megalotis", "Perciformes", "Centrarchidae", OTHER_FISH, group="sunfish"),
    FishClass("rock-bass", "Rock Bass", "Ambloplites rupestris", "Perciformes", "Centrarchidae", OTHER_FISH),
    FishClass("smallmouth-buffalo", "Smallmouth Buffalo", "Ictiobus bubalus", "Cypriniformes", "Catostomidae", OTHER_FISH),
    FishClass("bigmouth-buffalo", "Bigmouth Buffalo", "Ictiobus cyprinellus", "Cypriniformes", "Catostomidae", OTHER_FISH),
    FishClass("white-sucker", "White Sucker", "Catostomus commersonii", "Cypriniformes", "Catostomidae", OTHER_FISH),
    FishClass("black-bullhead", "Black Bullhead", "Ameiurus melas", "Siluriformes", "Ictaluridae", OTHER_FISH, group="catfish"),
    FishClass("yellow-bullhead", "Yellow Bullhead", "Ameiurus natalis", "Siluriformes", "Ictaluridae", OTHER_FISH, group="catfish"),
    FishClass("grass-carp", "Grass Carp", "Ctenopharyngodon idella", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="carp"),
    FishClass("bighead-carp", "Bighead Carp", "Hypophthalmichthys nobilis", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="carp"),
    FishClass("goldfish", "Goldfish", "Carassius auratus", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="carp"),
    FishClass("american-eel", "American Eel", "Anguilla rostrata", "Anguilliformes", "Anguillidae", OTHER_FISH),
    FishClass("red-drum", "Red Drum", "Sciaenops ocellatus", "Perciformes", "Sciaenidae", OTHER_FISH),
    FishClass("tilapia", "Blue Tilapia", "Oreochromis aureus", "Perciformes", "Cichlidae", OTHER_FISH),
    # ---- not a fish -----------------------------------------------------
    FishClass("person", "Human", "Homo sapiens", "Primates", "Hominidae", NOT_FISH),
    FishClass("dog", "Dog", "Canis lupus familiaris", "Carnivora", "Canidae", NOT_FISH),
    FishClass("turtle", "Pond Slider", "Trachemys scripta", "Testudines", "Emydidae", NOT_FISH),
    FishClass("bullfrog", "American Bullfrog", "Lithobates catesbeianus", "Anura", "Ranidae", NOT_FISH),
    FishClass("crayfish", "Red Swamp Crayfish", "Procambarus clarkii", "Decapoda", "Cambaridae", NOT_FISH),
    FishClass("heron", "Great Blue Heron", "Ardea herodias", "Pelecaniformes", "Ardeidae", NOT_FISH),
    FishClass("alligator", "American Alligator", "Alligator mississippiensis", "Crocodylia", "Alligatoridae", NOT_FISH),
    FishClass("water-snake", "Northern Water Snake", "Nerodia sipedon", "Squamata", "Colubridae", NOT_FISH),
)

# Not taxa: photos of the trip, not of a catch. BioCLIP was trained on
# taxonomic text, so these are weaker classes; they help, and the fish
# classes still have to win on their own.
SCENES: tuple[tuple[str, str], ...] = (
    ("scene-lake", "a photo of a lake with no fish"),
    ("scene-lure", "a photo of a fishing lure or fishing tackle"),
    ("scene-boat", "a photo of a boat on the water"),
    ("scene-screen", "a screenshot of a phone screen"),
    ("scene-drawing", "a drawing or cartoon of a fish"),
)

# The hybrid has no class of its own: from a photo it is a white or striped
# bass, and a claim of it is checked as one of the group.
CLAIM_GROUPS: dict[str, str] = {"hybrid-striped-bass": "temperate-bass"}

BY_SLUG: dict[str, FishClass] = {c.slug: c for c in CLASSES}


def group_label(group: str | None) -> str | None:
    """What a group is, for people: "a black bass", "a catfish"."""
    return next((c.group_label for c in CLASSES if c.group == group and c.group_label), None)


def prompts(c: FishClass) -> list[str]:
    """BioCLIP's text forms for a taxon (Stevens et al. 2024): common name,
    scientific name, and the taxonomic string with the common name."""
    kingdom_up = _ACTINO if c.kind != NOT_FISH else _taxon_head(c)
    taxonomic = f"{kingdom_up} {c.order} {c.family} {c.scientific}"
    return [
        f"a photo of {c.common}.",
        f"a photo of {c.scientific}.",
        f"a photo of {taxonomic} with common name {c.common}.",
    ]


def _taxon_head(c: FishClass) -> str:
    if c.order == "Decapoda":
        return "Animalia Arthropoda Malacostraca"
    vertebrate_class = {
        "Primates": "Mammalia", "Carnivora": "Mammalia", "Testudines": "Reptilia", "Crocodylia": "Reptilia",
        "Squamata": "Reptilia", "Anura": "Amphibia", "Pelecaniformes": "Aves",
    }[c.order]
    return f"Animalia Chordata {vertebrate_class}"
