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
_ELASMO = "Animalia Chordata Elasmobranchii"
_ELASMO_ORDERS = {
    "Carcharhiniformes", "Orectolobiformes", "Squaliformes", "Heterodontiformes", "Myliobatiformes",
    "Rhinopristiformes", "Rajiformes",
}

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
    FishClass("golden-trout", "Golden Trout", "Oncorhynchus aguabonita", "Salmoniformes", "Salmonidae", group="trout", group_label="a trout"),
    FishClass("kokanee-salmon", "Kokanee Salmon", "Oncorhynchus nerka", "Salmoniformes", "Salmonidae", group="salmon", group_label="a salmon"),
    FishClass("brown-bullhead", "Brown Bullhead", "Ameiurus nebulosus", "Siluriformes", "Ictaluridae", group="catfish", group_label="a catfish"),
    # ---- fish with no guide ---------------------------------------------
    FishClass("walleye", "Walleye", "Sander vitreus", "Perciformes", "Percidae"),
    FishClass("sauger", "Sauger", "Sander canadensis", "Perciformes", "Percidae", OTHER_FISH),
    FishClass("yellow-perch", "Yellow Perch", "Perca flavescens", "Perciformes", "Percidae"),
    FishClass("white-perch", "White Perch", "Morone americana", "Perciformes", "Moronidae", OTHER_FISH),
    FishClass("northern-pike", "Northern Pike", "Esox lucius", "Esociformes", "Esocidae"),
    FishClass("muskellunge", "Muskellunge", "Esox masquinongy", "Esociformes", "Esocidae", OTHER_FISH),
    FishClass("chain-pickerel", "Chain Pickerel", "Esox niger", "Esociformes", "Esocidae", OTHER_FISH),
    FishClass("longnose-gar", "Longnose Gar", "Lepisosteus osseus", "Lepisosteiformes", "Lepisosteidae", OTHER_FISH),
    FishClass("spotted-gar", "Spotted Gar", "Lepisosteus oculatus", "Lepisosteiformes", "Lepisosteidae", OTHER_FISH),
    FishClass("alligator-gar", "Alligator Gar", "Atractosteus spatula", "Lepisosteiformes", "Lepisosteidae", OTHER_FISH),
    FishClass("bowfin", "Bowfin", "Amia calva", "Amiiformes", "Amiidae", OTHER_FISH),
    FishClass("brown-trout", "Brown Trout", "Salmo trutta", "Salmoniformes", "Salmonidae", GUIDE, group="trout", group_label="a trout"),
    FishClass("brook-trout", "Brook Trout", "Salvelinus fontinalis", "Salmoniformes", "Salmonidae", GUIDE, group="trout", group_label="a trout"),
    FishClass("cutthroat-trout", "Cutthroat Trout", "Oncorhynchus clarkii", "Salmoniformes", "Salmonidae", GUIDE, group="trout", group_label="a trout"),
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
    FishClass("tilapia", "Tilapia", "Oreochromis aureus", "Perciformes", "Cichlidae", OTHER_FISH),
    # Added 2026-11-06: lake and Great Lakes fish anglers asked about
    # (salmon, steelhead, sturgeon…), so the answer can name them.
    # Steelhead is a rainbow trout that went to sea (or to a Great Lake) and
    # came back: the same species, so it has no taxon of its own. Its photos
    # are ones their source calls steelhead (fish_id_photos.STEELHEAD), and
    # a steelhead backs a claim of rainbow trout (SAME_FISH).
    FishClass("steelhead", "Steelhead", "Oncorhynchus mykiss", "Salmoniformes", "Salmonidae", OTHER_FISH, group="trout"),
    FishClass("chinook-salmon", "Chinook Salmon", "Oncorhynchus tshawytscha", "Salmoniformes", "Salmonidae", OTHER_FISH, group="salmon"),
    FishClass("coho-salmon", "Coho Salmon", "Oncorhynchus kisutch", "Salmoniformes", "Salmonidae", OTHER_FISH, group="salmon"),
    FishClass("pink-salmon", "Pink Salmon", "Oncorhynchus gorbuscha", "Salmoniformes", "Salmonidae", OTHER_FISH, group="salmon"),
    FishClass("atlantic-salmon", "Atlantic Salmon", "Salmo salar", "Salmoniformes", "Salmonidae", OTHER_FISH, group="salmon"),
    FishClass("bull-trout", "Bull Trout", "Salvelinus confluentus", "Salmoniformes", "Salmonidae", OTHER_FISH, group="trout"),
    FishClass("arctic-grayling", "Arctic Grayling", "Thymallus arcticus", "Salmoniformes", "Salmonidae", OTHER_FISH),
    FishClass("lake-whitefish", "Lake Whitefish", "Coregonus clupeaformis", "Salmoniformes", "Salmonidae", OTHER_FISH, group="whitefish", group_label="a whitefish or cisco"),
    FishClass("cisco", "Cisco", "Coregonus artedi", "Salmoniformes", "Salmonidae", OTHER_FISH, group="whitefish"),
    FishClass("lake-sturgeon", "Lake Sturgeon", "Acipenser fulvescens", "Acipenseriformes", "Acipenseridae", OTHER_FISH, group="sturgeon", group_label="a sturgeon"),
    FishClass("white-sturgeon", "White Sturgeon", "Acipenser transmontanus", "Acipenseriformes", "Acipenseridae", OTHER_FISH, group="sturgeon"),
    FishClass("shovelnose-sturgeon", "Shovelnose Sturgeon", "Scaphirhynchus platorynchus", "Acipenseriformes", "Acipenseridae", OTHER_FISH, group="sturgeon"),
    FishClass("paddlefish", "Paddlefish", "Polyodon spathula", "Acipenseriformes", "Polyodontidae", OTHER_FISH),
    FishClass("burbot", "Burbot", "Lota lota", "Gadiformes", "Lotidae", OTHER_FISH),
    FishClass("rainbow-smelt", "Rainbow Smelt", "Osmerus mordax", "Osmeriformes", "Osmeridae", OTHER_FISH),
    FishClass("alewife", "Alewife", "Alosa pseudoharengus", "Clupeiformes", "Alosidae", OTHER_FISH),
    FishClass("round-goby", "Round Goby", "Neogobius melanostomus", "Gobiiformes", "Gobiidae", OTHER_FISH),
    FishClass("northern-snakehead", "Northern Snakehead", "Channa argus", "Anabantiformes", "Channidae", OTHER_FISH),
    FishClass("peacock-bass", "Butterfly Peacock Bass", "Cichla ocellaris", "Cichliformes", "Cichlidae", OTHER_FISH),
    FishClass("shorthead-redhorse", "Shorthead Redhorse", "Moxostoma macrolepidotum", "Cypriniformes", "Catostomidae", OTHER_FISH),
    FishClass("shortnose-gar", "Shortnose Gar", "Lepisosteus platostomus", "Lepisosteiformes", "Lepisosteidae", OTHER_FISH),
    # ---- added 2026-11-18: freshwater fish anglers meet (the US/Canada list) --
    FishClass("golden-shiner", "Golden Shiner", "Notemigonus crysoleucas", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow", group_label="a minnow or shiner"),
    FishClass("creek-chub", "Creek Chub", "Semotilus atromaculatus", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow"),
    FishClass("fallfish", "Fallfish", "Semotilus corporalis", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow"),
    FishClass("fathead-minnow", "Fathead Minnow", "Pimephales promelas", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow"),
    FishClass("bluntnose-minnow", "Bluntnose Minnow", "Pimephales notatus", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow"),
    FishClass("common-shiner", "Common Shiner", "Luxilus cornutus", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow"),
    FishClass("emerald-shiner", "Emerald Shiner", "Notropis atherinoides", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow"),
    FishClass("central-stoneroller", "Central Stoneroller", "Campostoma anomalum", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow"),
    FishClass("northern-pikeminnow", "Northern Pikeminnow", "Ptychocheilus oregonensis", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="minnow"),
    FishClass("silver-carp", "Silver Carp", "Hypophthalmichthys molitrix", "Cypriniformes", "Cyprinidae", OTHER_FISH, group="carp"),
    FishClass("florida-gar", "Florida Gar", "Lepisosteus platyrhincus", "Lepisosteiformes", "Lepisosteidae", OTHER_FISH),
    FishClass("redfin-pickerel", "Redfin Pickerel", "Esox americanus", "Esociformes", "Esocidae", OTHER_FISH),
    FishClass("chum-salmon", "Chum Salmon", "Oncorhynchus keta", "Salmoniformes", "Salmonidae", OTHER_FISH, group="salmon"),
    FishClass("spotted-sunfish", "Spotted Sunfish", "Lepomis punctatus", "Perciformes", "Centrarchidae", OTHER_FISH, group="sunfish"),
    FishClass("redspotted-sunfish", "Redspotted Sunfish", "Lepomis miniatus", "Perciformes", "Centrarchidae", OTHER_FISH, group="sunfish"),
    FishClass("dollar-sunfish", "Dollar Sunfish", "Lepomis marginatus", "Perciformes", "Centrarchidae", OTHER_FISH, group="sunfish"),
    FishClass("mayan-cichlid", "Mayan Cichlid", "Mayaheros urophthalmus", "Cichliformes", "Cichlidae", OTHER_FISH),
    FishClass("rio-grande-cichlid", "Rio Grande Cichlid", "Herichthys cyanoguttatus", "Cichliformes", "Cichlidae", OTHER_FISH),
    FishClass("oscar", "Oscar", "Astronotus ocellatus", "Cichliformes", "Cichlidae", OTHER_FISH),
    FishClass("northern-hog-sucker", "Northern Hog Sucker", "Hypentelium nigricans", "Cypriniformes", "Catostomidae", OTHER_FISH),
    FishClass("golden-redhorse", "Golden Redhorse", "Moxostoma erythrurum", "Cypriniformes", "Catostomidae", OTHER_FISH),
    FishClass("longnose-sucker", "Longnose Sucker", "Catostomus catostomus", "Cypriniformes", "Catostomidae", OTHER_FISH),
    FishClass("stonecat", "Stonecat", "Noturus flavus", "Siluriformes", "Ictaluridae", OTHER_FISH, group="catfish"),
    # ---- added 2026-11-18: shore and inshore saltwater fish, all US coasts,
    # Alaska and Hawaii (no guides yet). Keep them the last fish: SEA_ONLY is
    # every fish from spotted-seatrout on ----------------------------------
    FishClass("spotted-seatrout", "Spotted Seatrout", "Cynoscion nebulosus", "Perciformes", "Sciaenidae", OTHER_FISH, group="seatrout", group_label="a seatrout or weakfish"),
    FishClass("sand-seatrout", "Sand Seatrout", "Cynoscion arenarius", "Perciformes", "Sciaenidae", OTHER_FISH, group="seatrout"),
    FishClass("weakfish", "Weakfish", "Cynoscion regalis", "Perciformes", "Sciaenidae", OTHER_FISH, group="seatrout"),
    FishClass("black-drum", "Black Drum", "Pogonias cromis", "Perciformes", "Sciaenidae", OTHER_FISH),
    FishClass("atlantic-croaker", "Atlantic Croaker", "Micropogonias undulatus", "Perciformes", "Sciaenidae", OTHER_FISH, group="croaker", group_label="a croaker or kingfish"),
    FishClass("spot", "Spot", "Leiostomus xanthurus", "Perciformes", "Sciaenidae", OTHER_FISH, group="croaker"),
    FishClass("silver-perch", "Silver Perch", "Bairdiella chrysoura", "Perciformes", "Sciaenidae", OTHER_FISH, group="croaker"),
    FishClass("southern-kingfish", "Southern Kingfish", "Menticirrhus americanus", "Perciformes", "Sciaenidae", OTHER_FISH, group="croaker"),
    FishClass("northern-kingfish", "Northern Kingfish", "Menticirrhus saxatilis", "Perciformes", "Sciaenidae", OTHER_FISH, group="croaker"),
    FishClass("white-croaker", "White Croaker", "Genyonemus lineatus", "Perciformes", "Sciaenidae", OTHER_FISH, group="croaker"),
    FishClass("california-corbina", "California Corbina", "Menticirrhus undulatus", "Perciformes", "Sciaenidae", OTHER_FISH, group="croaker"),
    FishClass("yellowfin-croaker", "Yellowfin Croaker", "Umbrina roncador", "Perciformes", "Sciaenidae", OTHER_FISH, group="croaker"),
    FishClass("pinfish", "Pinfish", "Lagodon rhomboides", "Perciformes", "Sparidae", OTHER_FISH, group="porgy", group_label="a porgy"),
    FishClass("sheepshead", "Sheepshead", "Archosargus probatocephalus", "Perciformes", "Sparidae", OTHER_FISH, group="porgy"),
    FishClass("scup", "Scup", "Stenotomus chrysops", "Perciformes", "Sparidae", OTHER_FISH, group="porgy"),
    FishClass("summer-flounder", "Summer Flounder", "Paralichthys dentatus", "Pleuronectiformes", "Paralichthyidae", OTHER_FISH, group="flounder", group_label="a flounder or halibut"),
    FishClass("southern-flounder", "Southern Flounder", "Paralichthys lethostigma", "Pleuronectiformes", "Paralichthyidae", OTHER_FISH, group="flounder"),
    FishClass("gulf-flounder", "Gulf Flounder", "Paralichthys albigutta", "Pleuronectiformes", "Paralichthyidae", OTHER_FISH, group="flounder"),
    FishClass("california-halibut", "California Halibut", "Paralichthys californicus", "Pleuronectiformes", "Paralichthyidae", OTHER_FISH, group="flounder"),
    FishClass("speckled-sanddab", "Speckled Sanddab", "Citharichthys stigmaeus", "Pleuronectiformes", "Paralichthyidae", OTHER_FISH, group="flounder"),
    FishClass("starry-flounder", "Starry Flounder", "Platichthys stellatus", "Pleuronectiformes", "Pleuronectidae", OTHER_FISH, group="flounder"),
    FishClass("winter-flounder", "Winter Flounder", "Pseudopleuronectes americanus", "Pleuronectiformes", "Pleuronectidae", OTHER_FISH, group="flounder"),
    FishClass("rock-sole", "Rock Sole", "Lepidopsetta bilineata", "Pleuronectiformes", "Pleuronectidae", OTHER_FISH, group="flounder"),
    FishClass("english-sole", "English Sole", "Parophrys vetulus", "Pleuronectiformes", "Pleuronectidae", OTHER_FISH, group="flounder"),
    FishClass("pacific-halibut", "Pacific Halibut", "Hippoglossus stenolepis", "Pleuronectiformes", "Pleuronectidae", OTHER_FISH, group="flounder"),
    FishClass("peacock-flounder", "Peacock Flounder", "Bothus mancus", "Pleuronectiformes", "Bothidae", OTHER_FISH, group="flounder"),
    FishClass("gray-snapper", "Gray Snapper", "Lutjanus griseus", "Perciformes", "Lutjanidae", OTHER_FISH, group="snapper", group_label="a snapper"),
    FishClass("lane-snapper", "Lane Snapper", "Lutjanus synagris", "Perciformes", "Lutjanidae", OTHER_FISH, group="snapper"),
    FishClass("red-snapper", "Red Snapper", "Lutjanus campechanus", "Perciformes", "Lutjanidae", OTHER_FISH, group="snapper"),
    FishClass("yellowtail-snapper", "Yellowtail Snapper", "Ocyurus chrysurus", "Perciformes", "Lutjanidae", OTHER_FISH, group="snapper"),
    FishClass("schoolmaster", "Schoolmaster", "Lutjanus apodus", "Perciformes", "Lutjanidae", OTHER_FISH, group="snapper"),
    FishClass("mutton-snapper", "Mutton Snapper", "Lutjanus analis", "Perciformes", "Lutjanidae", OTHER_FISH, group="snapper"),
    FishClass("bluestripe-snapper", "Bluestripe Snapper", "Lutjanus kasmira", "Perciformes", "Lutjanidae", OTHER_FISH, group="snapper"),
    FishClass("blacktail-snapper", "Blacktail Snapper", "Lutjanus fulvus", "Perciformes", "Lutjanidae", OTHER_FISH, group="snapper"),
    FishClass("gag", "Gag", "Mycteroperca microlepis", "Perciformes", "Serranidae", OTHER_FISH, group="grouper", group_label="a grouper"),
    FishClass("black-grouper", "Black Grouper", "Mycteroperca bonaci", "Perciformes", "Serranidae", OTHER_FISH, group="grouper"),
    FishClass("goliath-grouper", "Goliath Grouper", "Epinephelus itajara", "Perciformes", "Serranidae", OTHER_FISH, group="grouper"),
    FishClass("graysby", "Graysby", "Cephalopholis cruentata", "Perciformes", "Serranidae", OTHER_FISH, group="grouper"),
    FishClass("peacock-grouper", "Peacock Grouper", "Cephalopholis argus", "Perciformes", "Serranidae", OTHER_FISH, group="grouper"),
    FishClass("black-sea-bass", "Black Sea Bass", "Centropristis striata", "Perciformes", "Serranidae", OTHER_FISH, group="sea-bass", group_label="a sea bass"),
    FishClass("kelp-bass", "Kelp Bass", "Paralabrax clathratus", "Perciformes", "Serranidae", OTHER_FISH, group="sea-bass"),
    FishClass("barred-sand-bass", "Barred Sand Bass", "Paralabrax nebulifer", "Perciformes", "Serranidae", OTHER_FISH, group="sea-bass"),
    FishClass("spotted-sand-bass", "Spotted Sand Bass", "Paralabrax maculatofasciatus", "Perciformes", "Serranidae", OTHER_FISH, group="sea-bass"),
    FishClass("crevalle-jack", "Crevalle Jack", "Caranx hippos", "Carangiformes", "Carangidae", OTHER_FISH, group="jack", group_label="a jack or trevally"),
    FishClass("blue-runner", "Blue Runner", "Caranx crysos", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("bar-jack", "Bar Jack", "Caranx ruber", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("horse-eye-jack", "Horse-eye Jack", "Caranx latus", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("yellow-jack", "Yellow Jack", "Carangoides bartholomaei", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("giant-trevally", "Giant Trevally", "Caranx ignobilis", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("bluefin-trevally", "Bluefin Trevally", "Caranx melampygus", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("greater-amberjack", "Greater Amberjack", "Seriola dumerili", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("yellowtail-amberjack", "Yellowtail Amberjack", "Seriola lalandi", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("almaco-jack", "Almaco Jack", "Seriola rivoliana", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("lookdown", "Lookdown", "Selene vomer", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("atlantic-bumper", "Atlantic Bumper", "Chloroscombrus chrysurus", "Carangiformes", "Carangidae", OTHER_FISH, group="jack"),
    FishClass("florida-pompano", "Florida Pompano", "Trachinotus carolinus", "Carangiformes", "Carangidae", OTHER_FISH, group="pompano", group_label="a pompano or permit"),
    FishClass("permit", "Permit", "Trachinotus falcatus", "Carangiformes", "Carangidae", OTHER_FISH, group="pompano"),
    FishClass("palometa", "Palometa", "Trachinotus goodei", "Carangiformes", "Carangidae", OTHER_FISH, group="pompano"),
    FishClass("spanish-mackerel", "Spanish Mackerel", "Scomberomorus maculatus", "Scombriformes", "Scombridae", OTHER_FISH, group="mackerel", group_label="a mackerel"),
    FishClass("king-mackerel", "King Mackerel", "Scomberomorus cavalla", "Scombriformes", "Scombridae", OTHER_FISH, group="mackerel"),
    FishClass("atlantic-mackerel", "Atlantic Mackerel", "Scomber scombrus", "Scombriformes", "Scombridae", OTHER_FISH, group="mackerel"),
    FishClass("chub-mackerel", "Pacific Chub Mackerel", "Scomber japonicus", "Scombriformes", "Scombridae", OTHER_FISH, group="mackerel"),
    FishClass("jack-mackerel", "Pacific Jack Mackerel", "Trachurus symmetricus", "Carangiformes", "Carangidae", OTHER_FISH, group="mackerel"),
    FishClass("copper-rockfish", "Copper Rockfish", "Sebastes caurinus", "Scorpaeniformes", "Sebastidae", OTHER_FISH, group="rockfish", group_label="a rockfish"),
    FishClass("quillback-rockfish", "Quillback Rockfish", "Sebastes maliger", "Scorpaeniformes", "Sebastidae", OTHER_FISH, group="rockfish"),
    FishClass("black-rockfish", "Black Rockfish", "Sebastes melanops", "Scorpaeniformes", "Sebastidae", OTHER_FISH, group="rockfish"),
    FishClass("blue-rockfish", "Blue Rockfish", "Sebastes mystinus", "Scorpaeniformes", "Sebastidae", OTHER_FISH, group="rockfish"),
    FishClass("brown-rockfish", "Brown Rockfish", "Sebastes auriculatus", "Scorpaeniformes", "Sebastidae", OTHER_FISH, group="rockfish"),
    FishClass("lingcod", "Lingcod", "Ophiodon elongatus", "Scorpaeniformes", "Hexagrammidae", OTHER_FISH),
    FishClass("kelp-greenling", "Kelp Greenling", "Hexagrammos decagrammus", "Scorpaeniformes", "Hexagrammidae", OTHER_FISH, group="greenling", group_label="a greenling"),
    FishClass("painted-greenling", "Painted Greenling", "Oxylebius pictus", "Scorpaeniformes", "Hexagrammidae", OTHER_FISH, group="greenling"),
    FishClass("cabezon", "Cabezon", "Scorpaenichthys marmoratus", "Scorpaeniformes", "Cottidae", OTHER_FISH, group="sculpin", group_label="a sculpin"),
    FishClass("staghorn-sculpin", "Pacific Staghorn Sculpin", "Leptocottus armatus", "Scorpaeniformes", "Cottidae", OTHER_FISH, group="sculpin"),
    FishClass("buffalo-sculpin", "Buffalo Sculpin", "Enophrys bison", "Scorpaeniformes", "Cottidae", OTHER_FISH, group="sculpin"),
    FishClass("red-irish-lord", "Red Irish Lord", "Hemilepidotus hemilepidotus", "Scorpaeniformes", "Cottidae", OTHER_FISH, group="sculpin"),
    FishClass("shiner-perch", "Shiner Perch", "Cymatogaster aggregata", "Perciformes", "Embiotocidae", OTHER_FISH, group="surfperch", group_label="a surfperch"),
    FishClass("barred-surfperch", "Barred Surfperch", "Amphistichus argenteus", "Perciformes", "Embiotocidae", OTHER_FISH, group="surfperch"),
    FishClass("black-perch", "Black Perch", "Embiotoca jacksoni", "Perciformes", "Embiotocidae", OTHER_FISH, group="surfperch"),
    FishClass("pile-perch", "Pile Perch", "Rhacochilus vacca", "Perciformes", "Embiotocidae", OTHER_FISH, group="surfperch"),
    FishClass("walleye-surfperch", "Walleye Surfperch", "Hyperprosopon argenteum", "Perciformes", "Embiotocidae", OTHER_FISH, group="surfperch"),
    FishClass("pigfish", "Pigfish", "Orthopristis chrysoptera", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt", group_label="a grunt"),
    FishClass("white-grunt", "White Grunt", "Haemulon plumierii", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt"),
    FishClass("bluestriped-grunt", "Bluestriped Grunt", "Haemulon sciurus", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt"),
    FishClass("french-grunt", "French Grunt", "Haemulon flavolineatum", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt"),
    FishClass("tomtate", "Tomtate", "Haemulon aurolineatum", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt"),
    FishClass("sailors-grunt", "Sailor's Grunt", "Haemulon parra", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt"),
    FishClass("porkfish", "Porkfish", "Anisotremus virginicus", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt"),
    FishClass("black-margate", "Black Margate", "Anisotremus surinamensis", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt"),
    FishClass("sargo", "Sargo", "Anisotremus davidsonii", "Perciformes", "Haemulidae", OTHER_FISH, group="grunt"),
    FishClass("striped-mullet", "Striped Mullet", "Mugil cephalus", "Mugiliformes", "Mugilidae", OTHER_FISH, group="mullet", group_label="a mullet"),
    FishClass("white-mullet", "White Mullet", "Mugil curema", "Mugiliformes", "Mugilidae", OTHER_FISH, group="mullet"),
    FishClass("hardhead-catfish", "Hardhead Catfish", "Ariopsis felis", "Siluriformes", "Ariidae", OTHER_FISH, group="sea-catfish", group_label="a sea catfish"),
    FishClass("gafftopsail-catfish", "Gafftopsail Catfish", "Bagre marinus", "Siluriformes", "Ariidae", OTHER_FISH, group="sea-catfish"),
    FishClass("opaleye", "Opaleye", "Girella nigricans", "Perciformes", "Kyphosidae", OTHER_FISH, group="sea-chub", group_label="a sea chub"),
    FishClass("halfmoon", "Halfmoon", "Medialuna californiensis", "Perciformes", "Kyphosidae", OTHER_FISH, group="sea-chub"),
    FishClass("bermuda-sea-chub", "Bermuda Sea Chub", "Kyphosus sectatrix", "Perciformes", "Kyphosidae", OTHER_FISH, group="sea-chub"),
    FishClass("highfin-chub", "Highfin Chub", "Kyphosus cinerascens", "Perciformes", "Kyphosidae", OTHER_FISH, group="sea-chub"),
    FishClass("brassy-chub", "Brassy Chub", "Kyphosus vaigiensis", "Perciformes", "Kyphosidae", OTHER_FISH, group="sea-chub"),
    FishClass("tautog", "Tautog", "Tautoga onitis", "Perciformes", "Labridae", OTHER_FISH),
    FishClass("cunner", "Cunner", "Tautogolabrus adspersus", "Perciformes", "Labridae", OTHER_FISH),
    FishClass("california-sheephead", "California Sheephead", "Semicossyphus pulcher", "Perciformes", "Labridae", OTHER_FISH),
    FishClass("hogfish", "Hogfish", "Lachnolaimus maximus", "Perciformes", "Labridae", OTHER_FISH),
    FishClass("bluefish", "Bluefish", "Pomatomus saltatrix", "Perciformes", "Pomatomidae", OTHER_FISH),
    FishClass("tarpon", "Tarpon", "Megalops atlanticus", "Elopiformes", "Megalopidae", OTHER_FISH),
    FishClass("ladyfish", "Ladyfish", "Elops saurus", "Elopiformes", "Elopidae", OTHER_FISH),
    FishClass("bonefish", "Bonefish", "Albula vulpes", "Albuliformes", "Albulidae", OTHER_FISH),
    FishClass("common-snook", "Common Snook", "Centropomus undecimalis", "Perciformes", "Centropomidae", OTHER_FISH),
    FishClass("cobia", "Cobia", "Rachycentron canadum", "Perciformes", "Rachycentridae", OTHER_FISH),
    FishClass("tripletail", "Tripletail", "Lobotes surinamensis", "Perciformes", "Lobotidae", OTHER_FISH),
    FishClass("atlantic-spadefish", "Atlantic Spadefish", "Chaetodipterus faber", "Perciformes", "Ephippidae", OTHER_FISH),
    FishClass("great-barracuda", "Great Barracuda", "Sphyraena barracuda", "Perciformes", "Sphyraenidae", OTHER_FISH, group="barracuda", group_label="a barracuda"),
    FishClass("pacific-barracuda", "Pacific Barracuda", "Sphyraena argentea", "Perciformes", "Sphyraenidae", OTHER_FISH, group="barracuda"),
    FishClass("atlantic-needlefish", "Atlantic Needlefish", "Strongylura marina", "Beloniformes", "Belonidae", OTHER_FISH, group="needlefish", group_label="a needlefish"),
    FishClass("redfin-needlefish", "Redfin Needlefish", "Strongylura notata", "Beloniformes", "Belonidae", OTHER_FISH, group="needlefish"),
    FishClass("houndfish", "Houndfish", "Tylosurus crocodilus", "Beloniformes", "Belonidae", OTHER_FISH, group="needlefish"),
    FishClass("keeltail-needlefish", "Keeltail Needlefish", "Platybelone argalus", "Beloniformes", "Belonidae", OTHER_FISH, group="needlefish"),
    FishClass("atlantic-menhaden", "Atlantic Menhaden", "Brevoortia tyrannus", "Clupeiformes", "Clupeidae", OTHER_FISH),
    FishClass("pacific-herring", "Pacific Herring", "Clupea pallasii", "Clupeiformes", "Clupeidae", OTHER_FISH),
    FishClass("jacksmelt", "Jacksmelt", "Atherinopsis californiensis", "Atheriniformes", "Atherinopsidae", OTHER_FISH, group="silverside", group_label="a silverside or smelt"),
    FishClass("topsmelt", "Topsmelt", "Atherinops affinis", "Atheriniformes", "Atherinopsidae", OTHER_FISH, group="silverside"),
    FishClass("california-grunion", "California Grunion", "Leuresthes tenuis", "Atheriniformes", "Atherinopsidae", OTHER_FISH, group="silverside"),
    FishClass("atlantic-silverside", "Atlantic Silverside", "Menidia menidia", "Atheriniformes", "Atherinopsidae", OTHER_FISH, group="silverside"),
    FishClass("eulachon", "Eulachon", "Thaleichthys pacificus", "Osmeriformes", "Osmeridae", OTHER_FISH),
    FishClass("oyster-toadfish", "Oyster Toadfish", "Opsanus tau", "Batrachoidiformes", "Batrachoididae", OTHER_FISH, group="toadfish", group_label="a toadfish"),
    FishClass("gulf-toadfish", "Gulf Toadfish", "Opsanus beta", "Batrachoidiformes", "Batrachoididae", OTHER_FISH, group="toadfish"),
    FishClass("plainfin-midshipman", "Plainfin Midshipman", "Porichthys notatus", "Batrachoidiformes", "Batrachoididae", OTHER_FISH, group="toadfish"),
    FishClass("northern-puffer", "Northern Puffer", "Sphoeroides maculatus", "Tetraodontiformes", "Tetraodontidae", OTHER_FISH, group="puffer", group_label="a puffer"),
    FishClass("checkered-puffer", "Checkered Puffer", "Sphoeroides testudineus", "Tetraodontiformes", "Tetraodontidae", OTHER_FISH, group="puffer"),
    FishClass("bandtail-puffer", "Bandtail Puffer", "Sphoeroides spengleri", "Tetraodontiformes", "Tetraodontidae", OTHER_FISH, group="puffer"),
    FishClass("gray-triggerfish", "Gray Triggerfish", "Balistes capriscus", "Tetraodontiformes", "Balistidae", OTHER_FISH, group="triggerfish", group_label="a triggerfish"),
    FishClass("black-durgon", "Black Durgon", "Melichthys niger", "Tetraodontiformes", "Balistidae", OTHER_FISH, group="triggerfish"),
    FishClass("pinktail-triggerfish", "Pinktail Triggerfish", "Melichthys vidua", "Tetraodontiformes", "Balistidae", OTHER_FISH, group="triggerfish"),
    FishClass("striped-searobin", "Striped Searobin", "Prionotus evolans", "Scorpaeniformes", "Triglidae", OTHER_FISH, group="searobin", group_label="a searobin"),
    FishClass("northern-searobin", "Northern Searobin", "Prionotus carolinus", "Scorpaeniformes", "Triglidae", OTHER_FISH, group="searobin"),
    FishClass("inshore-lizardfish", "Inshore Lizardfish", "Synodus foetens", "Aulopiformes", "Synodontidae", OTHER_FISH),
    FishClass("yellowfin-mojarra", "Yellowfin Mojarra", "Gerres cinereus", "Perciformes", "Gerreidae", OTHER_FISH),
    FishClass("atlantic-cod", "Atlantic Cod", "Gadus morhua", "Gadiformes", "Gadidae", OTHER_FISH, group="cod", group_label="a cod or pollock"),
    FishClass("pacific-cod", "Pacific Cod", "Gadus macrocephalus", "Gadiformes", "Gadidae", OTHER_FISH, group="cod"),
    FishClass("pollock", "Pollock", "Pollachius virens", "Gadiformes", "Gadidae", OTHER_FISH, group="cod"),
    FishClass("atlantic-tomcod", "Atlantic Tomcod", "Microgadus tomcod", "Gadiformes", "Gadidae", OTHER_FISH, group="cod"),
    FishClass("yellowstripe-goatfish", "Yellowstripe Goatfish", "Mulloidichthys flavolineatus", "Perciformes", "Mullidae", OTHER_FISH, group="goatfish", group_label="a goatfish"),
    FishClass("yellowfin-goatfish", "Yellowfin Goatfish", "Mulloidichthys vanicolensis", "Perciformes", "Mullidae", OTHER_FISH, group="goatfish"),
    FishClass("manybar-goatfish", "Manybar Goatfish", "Parupeneus multifasciatus", "Perciformes", "Mullidae", OTHER_FISH, group="goatfish"),
    FishClass("yellowsaddle-goatfish", "Yellowsaddle Goatfish", "Parupeneus cyclostomus", "Perciformes", "Mullidae", OTHER_FISH, group="goatfish"),
    FishClass("convict-tang", "Convict Tang", "Acanthurus triostegus", "Acanthuriformes", "Acanthuridae", OTHER_FISH, group="surgeonfish", group_label="a surgeonfish"),
    FishClass("brown-surgeonfish", "Brown Surgeonfish", "Acanthurus nigrofuscus", "Acanthuriformes", "Acanthuridae", OTHER_FISH, group="surgeonfish"),
    FishClass("orangeband-surgeonfish", "Orangeband Surgeonfish", "Acanthurus olivaceus", "Acanthuriformes", "Acanthuridae", OTHER_FISH, group="surgeonfish"),
    FishClass("ringtail-surgeonfish", "Ringtail Surgeonfish", "Acanthurus blochii", "Acanthuriformes", "Acanthuridae", OTHER_FISH, group="surgeonfish"),
    FishClass("yellowfin-surgeonfish", "Yellowfin Surgeonfish", "Acanthurus xanthopterus", "Acanthuriformes", "Acanthuridae", OTHER_FISH, group="surgeonfish"),
    FishClass("eyestripe-surgeonfish", "Eyestripe Surgeonfish", "Acanthurus dussumieri", "Acanthuriformes", "Acanthuridae", OTHER_FISH, group="surgeonfish"),
    FishClass("bluespine-unicornfish", "Bluespine Unicornfish", "Naso unicornis", "Acanthuriformes", "Acanthuridae", OTHER_FISH, group="surgeonfish"),
    FishClass("orangespine-unicornfish", "Orangespine Unicornfish", "Naso lituratus", "Acanthuriformes", "Acanthuridae", OTHER_FISH, group="surgeonfish"),
    FishClass("hawaiian-flagtail", "Hawaiian Flagtail", "Kuhlia xenura", "Perciformes", "Kuhliidae", OTHER_FISH, group="flagtail", group_label="a flagtail (aholehole)"),
    FishClass("reticulated-flagtail", "Reticulated Flagtail", "Kuhlia sandvicensis", "Perciformes", "Kuhliidae", OTHER_FISH, group="flagtail"),
    FishClass("bigeye-emperor", "Bigeye Emperor", "Monotaxis grandoculis", "Perciformes", "Lethrinidae", OTHER_FISH),
    FishClass("milkfish", "Milkfish", "Chanos chanos", "Gonorynchiformes", "Chanidae", OTHER_FISH),
    FishClass("epaulette-soldierfish", "Epaulette Soldierfish", "Myripristis kuntee", "Holocentriformes", "Holocentridae", OTHER_FISH),
    FishClass("leopard-shark", "Leopard Shark", "Triakis semifasciata", "Carcharhiniformes", "Triakidae", OTHER_FISH, group="shark", group_label="a shark"),
    FishClass("smooth-dogfish", "Smooth Dogfish", "Mustelus canis", "Carcharhiniformes", "Triakidae", OTHER_FISH, group="shark"),
    FishClass("gray-smoothhound", "Gray Smoothhound", "Mustelus californicus", "Carcharhiniformes", "Triakidae", OTHER_FISH, group="shark"),
    FishClass("bonnethead", "Bonnethead", "Sphyrna tiburo", "Carcharhiniformes", "Sphyrnidae", OTHER_FISH, group="shark"),
    FishClass("scalloped-hammerhead", "Scalloped Hammerhead", "Sphyrna lewini", "Carcharhiniformes", "Sphyrnidae", OTHER_FISH, group="shark"),
    FishClass("blacktip-shark", "Blacktip Shark", "Carcharhinus limbatus", "Carcharhiniformes", "Carcharhinidae", OTHER_FISH, group="shark"),
    FishClass("spinner-shark", "Spinner Shark", "Carcharhinus brevipinna", "Carcharhiniformes", "Carcharhinidae", OTHER_FISH, group="shark"),
    FishClass("bull-shark", "Bull Shark", "Carcharhinus leucas", "Carcharhiniformes", "Carcharhinidae", OTHER_FISH, group="shark"),
    FishClass("sandbar-shark", "Sandbar Shark", "Carcharhinus plumbeus", "Carcharhiniformes", "Carcharhinidae", OTHER_FISH, group="shark"),
    FishClass("lemon-shark", "Lemon Shark", "Negaprion brevirostris", "Carcharhiniformes", "Carcharhinidae", OTHER_FISH, group="shark"),
    FishClass("atlantic-sharpnose-shark", "Atlantic Sharpnose Shark", "Rhizoprionodon terraenovae", "Carcharhiniformes", "Carcharhinidae", OTHER_FISH, group="shark"),
    FishClass("tiger-shark", "Tiger Shark", "Galeocerdo cuvier", "Carcharhiniformes", "Carcharhinidae", OTHER_FISH, group="shark"),
    FishClass("nurse-shark", "Nurse Shark", "Ginglymostoma cirratum", "Orectolobiformes", "Ginglymostomatidae", OTHER_FISH, group="shark"),
    FishClass("spiny-dogfish", "Spiny Dogfish", "Squalus acanthias", "Squaliformes", "Squalidae", OTHER_FISH, group="shark"),
    FishClass("horn-shark", "Horn Shark", "Heterodontus francisci", "Heterodontiformes", "Heterodontidae", OTHER_FISH, group="shark"),
    FishClass("atlantic-stingray", "Atlantic Stingray", "Hypanus sabinus", "Myliobatiformes", "Dasyatidae", OTHER_FISH, group="ray", group_label="a stingray, skate or ray"),
    FishClass("southern-stingray", "Southern Stingray", "Hypanus americanus", "Myliobatiformes", "Dasyatidae", OTHER_FISH, group="ray"),
    FishClass("diamond-stingray", "Diamond Stingray", "Hypanus dipterurus", "Myliobatiformes", "Dasyatidae", OTHER_FISH, group="ray"),
    FishClass("yellow-stingray", "Yellow Stingray", "Urobatis jamaicensis", "Myliobatiformes", "Urotrygonidae", OTHER_FISH, group="ray"),
    FishClass("bat-ray", "Bat Ray", "Myliobatis californica", "Myliobatiformes", "Myliobatidae", OTHER_FISH, group="ray"),
    FishClass("cownose-ray", "Cownose Ray", "Rhinoptera bonasus", "Myliobatiformes", "Myliobatidae", OTHER_FISH, group="ray"),
    FishClass("spotted-eagle-ray", "Spotted Eagle Ray", "Aetobatus narinari", "Myliobatiformes", "Myliobatidae", OTHER_FISH, group="ray"),
    FishClass("shovelnose-guitarfish", "Shovelnose Guitarfish", "Pseudobatos productus", "Rhinopristiformes", "Rhinobatidae", OTHER_FISH, group="ray"),
    FishClass("thornback-ray", "Thornback", "Platyrhinoidis triseriata", "Myliobatiformes", "Platyrhinidae", OTHER_FISH, group="ray"),
    FishClass("clearnose-skate", "Clearnose Skate", "Raja eglanteria", "Rajiformes", "Rajidae", OTHER_FISH, group="ray"),
    FishClass("little-skate", "Little Skate", "Leucoraja erinacea", "Rajiformes", "Rajidae", OTHER_FISH, group="ray"),
    FishClass("big-skate", "Big Skate", "Beringraja binoculata", "Rajiformes", "Rajidae", OTHER_FISH, group="ray"),
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
CLAIM_GROUPS: dict[str, str] = {
    "hybrid-striped-bass": "temperate-bass",
}

# Classes that are one guide species under another name: a steelhead is a
# rainbow trout. Seen in a photo, it confirms a claim of that species, and
# the answer names both.
SAME_FISH: dict[str, str] = {"steelhead": "rainbow-trout"}

# Fish a photo can't tell from a guide fish's group: a USFWS photo of a white
# bass read as a white perch (2026-11-02), and the angler was told it wasn't one.
LOOK_ALIKES: dict[str, str] = {"white-perch": "temperate-bass"}

# Fish the built model knows as other_fish that have since got a guide. A
# class's kind is part of what the model was built for (classes_digest), so
# changing it here would mean rebuilding and retraining: until the next
# rebuild they stay other_fish, and this says they are on the list now.
GUIDED_SINCE_BUILD: frozenset[str] = frozenset()

BY_SLUG: dict[str, FishClass] = {c.slug: c for c in CLASSES}

# Fish of the sea a catch far from it can't be (services/coast.py,
# docs/adr/0063): the saltwater fish, less those that swim far up rivers into
# fresh water (mullet and snook in Lake Okeechobee, Atlantic stingrays in the
# St. Johns, bull sharks up the Mississippi, flounder, tomcod and eulachon
# upriver).
UP_RIVERS: frozenset[str] = frozenset({
    "striped-mullet", "common-snook", "tarpon", "atlantic-needlefish", "crevalle-jack", "southern-flounder",
    "starry-flounder", "bull-shark", "atlantic-stingray", "atlantic-tomcod", "eulachon",
})
_FIRST_SEA = next(i for i, c in enumerate(CLASSES) if c.slug == "spotted-seatrout")
SEA_ONLY: frozenset[str] = frozenset(c.slug for c in CLASSES[_FIRST_SEA:] if c.kind != NOT_FISH) - UP_RIVERS


def group_label(group: str | None) -> str | None:
    """What a group is, for people: "a black bass", "a catfish"."""
    return next((c.group_label for c in CLASSES if c.group == group and c.group_label), None)


def prompts(c: FishClass) -> list[str]:
    """BioCLIP's text forms for a taxon (Stevens et al. 2024): common name,
    scientific name, and the taxonomic string with the common name."""
    if c.kind == NOT_FISH:
        kingdom_up = _taxon_head(c)
    elif c.order in _ELASMO_ORDERS:
        kingdom_up = _ELASMO  # sharks, skates and rays (added 2026-11-18)
    else:
        kingdom_up = _ACTINO
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
