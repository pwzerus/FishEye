"""How to catch each species: diet, where to look, baits, tackle setups.

This is reviewed reference content, written for a first-time angler, and
kept in code rather than scraped because every line was checked against a
named source (docs/adr/0011-species-guides.md). Three rules it follows:

- Every tackle setup names the sources it came from (`TackleSetup.source_ids`),
  and the page shows them. Non-agency sources (a fishing guide's website) are
  marked `kind="guide"` so the UI can say so.
- No invented numbers. Where no source gave a hook size (white bass,
  spotted bass, hybrids), a setup describes the jighead or lure weight
  instead of guessing a hook.
- No regulations beyond two legal basics that affect how bait is used.
  Size and bag limits change and vary by lake; every guide links to TPWD's
  own limits page instead (PRD §4.7: regulations are high-risk, summary +
  official link only).

`common_name` must match `Species.common_name` exactly; tests enforce that
every species the TPWD scraper can create has a guide.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

TPWD_LIMITS_URL = (
    "https://tpwd.texas.gov/regulations/outdoor-annual/fishing/freshwater-fishing/bag-length-limits"
)


@dataclass(frozen=True)
class Source:
    id: str
    label: str
    url: str
    kind: str  # "agency" | "publication" | "guide"


SOURCES: dict[str, Source] = {
    s.id: s
    for s in [
        # Texas Parks and Wildlife
        Source("tpwd-lmb", "TPWD: Largemouth Bass", "https://tpwd.texas.gov/huntwild/wild/species/lmb/", "agency"),
        Source("tpwd-spb", "TPWD: Spotted Bass", "https://tpwd.texas.gov/huntwild/wild/species/spb/", "agency"),
        Source("tpwd-wtb", "TPWD: White Bass", "https://tpwd.texas.gov/huntwild/wild/species/wtb/", "agency"),
        Source("tpwd-ccf", "TPWD: Channel Catfish", "https://tpwd.texas.gov/huntwild/wild/species/ccf/", "agency"),
        Source("tpwd-blc", "TPWD: Blue Catfish", "https://tpwd.texas.gov/huntwild/wild/species/blc/", "agency"),
        Source("tpwd-wcp", "TPWD: White Crappie", "https://tpwd.texas.gov/huntwild/wild/species/wcp/", "agency"),
        Source("tpwd-bcp", "TPWD: Black Crappie", "https://tpwd.texas.gov/huntwild/wild/species/crappie/", "agency"),
        Source("tpwd-bgl", "TPWD: Bluegill", "https://tpwd.texas.gov/huntwild/wild/species/bgl/", "agency"),
        Source("tpwd-gsh", "TPWD: Gizzard Shad", "https://tpwd.texas.gov/huntwild/wild/species/gsh/", "agency"),
        Source("tpwd-tfs", "TPWD: Threadfin Shad", "https://tpwd.texas.gov/huntwild/wild/species/threadfinshad/", "agency"),
        Source("tpwd-tawakoni", "TPWD: Lake Tawakoni fishing guide", "https://tpwd.texas.gov/fishboat/fish/recreational/lakes/tawakoni/", "agency"),
        Source("tpwd-cedarcreek", "TPWD: Cedar Creek Reservoir fishing guide", "https://tpwd.texas.gov/fishboat/fish/recreational/lakes/cedar_creek/", "agency"),
        Source("tpwd-nf", "TPWD: Neighborhood Fishin'", "https://tpwd.texas.gov/fishboat/fish/programs/neighborhood-fishin/", "agency"),
        Source("tpwd-crappie-spots", "TPWD: fall crappie hot spots (2020)", "https://tpwd.texas.gov/newsmedia/releases/?req=20200915a", "agency"),
        Source("tpwd-regs-general", "TPWD Outdoor Annual: general fishing regulations", "https://tpwd.texas.gov/regulations/outdoor-annual/fishing/general-rules-regulations/general-fishing-regulations", "agency"),
        Source("tpwd-regs-devices", "TPWD Outdoor Annual: legal devices", "https://tpwd.texas.gov/regulations/outdoor-annual/fishing/general-rules-regulations/legal-devices-for-fish", "agency"),
        Source("tpwmag-texoma-2014", "Texas Parks & Wildlife magazine: Texoma stripers (2014)", "https://tpwmagazine.com/archive/2014/aug/ed_3_texomastripers/", "publication"),
        Source("tpwmag-texoma-2020", "Texas Parks & Wildlife magazine: Texoma (2020)", "https://tpwmagazine.com/archive/2020/mar/ed_1_texoma/index.phtml", "publication"),
        Source("tpwmag-hybrid-2014", "Texas Parks & Wildlife magazine: hybrid bass (2014)", "https://tpwmagazine.com/archive/2014/mar/ed_3_hybridbass/", "publication"),
        Source("tpwmag-bluecat-2020", "Texas Parks & Wildlife magazine: winter blue catfish (2020)", "https://tpwmagazine.com/archive/2020/dec/scout10_nicecatch/index.phtml", "publication"),
        Source("tpwd-bass-id", "TPWD Outdoor Annual: Bass identification", "https://tpwd.texas.gov/regulations/outdoor-annual/fishing/freshwater-fishing/bass-identification", "agency"),
        Source("tpwd-cat-id", "TPWD Outdoor Annual: Catfish identification", "https://tpwd.texas.gov/regulations/outdoor-annual/fishing/freshwater-fishing/catfish-identification", "agency"),
        Source("tamu-hsb", "Texas A&M Fisheries: Hybrid Striped Bass", "https://fisheries.tamu.edu/pond-management/species/hybrid-striped-bass/", "agency"),
        # Other state agencies
        Source("mn-lmb", "Minnesota DNR: How to catch largemouth bass", "https://www.dnr.state.mn.us/gofishing/how-catch-largemouth-bass.html", "agency"),
        Source("mn-ccf", "Minnesota DNR: How to catch channel catfish", "https://www.dnr.state.mn.us/gofishing/how-catch-channel-catfish.html", "agency"),
        Source("mn-crappie", "Minnesota DNR: How to catch crappie", "https://www.dnr.state.mn.us/gofishing/how-catch-crappie.html", "agency"),
        Source("fwc-bass", "Florida FWC: Pro tips for bass", "https://myfwc.com/fishing/freshwater/fishing-tips/protipsbass/", "agency"),
        Source("mdc-bass", "Missouri Conservationist: What, where, when (2006)", "https://mdc.mo.gov/magazines/conservationist/2006-04/what-where-when", "agency"),
        Source("mdc-cat", "Missouri Dept. of Conservation: Catfish tips", "https://mdc.mo.gov/fishing/species/catfish/catfish-tips-fishing", "agency"),
        Source("mdc-bigcat", "Missouri Dept. of Conservation: Big-river catfishing", "https://mdc.mo.gov/fishing/species/catfish/big-river-catfishing", "agency"),
        Source("mdc-crappie", "Missouri Dept. of Conservation: Crappie tips", "https://mdc.mo.gov/fishing/species/crappie/crappie-tips-fishing", "agency"),
        Source("mdc-bluegill", "Missouri Dept. of Conservation: Bluegill tips", "https://mdc.mo.gov/fishing/species/sunfish/sunfish-tips-bluegill-fishing", "agency"),
        Source("mdc-beginners", "Missouri Conservationist: Fishing for beginners (2014)", "https://mdc.mo.gov/magazines/conservationist/2014-06/fishing-beginners", "agency"),
        Source("odwc-whitebass", "Oklahoma Dept. of Wildlife Conservation: White bass angler guide", "https://www.wildlifedepartment.com/outdoorok/ooj/white-bass-angler-guide-top-tips-area-highlights", "agency"),
        Source("odwc-striper", "Oklahoma Dept. of Wildlife Conservation: Striped & hybrid bass angler guide", "https://www.wildlifedepartment.com/outdoorok/ooj/striped-hybrid-striped-bass-angler-guide-top-tips-area-highlights", "agency"),
        Source("odwc-striper-fg", "Oklahoma Dept. of Wildlife Conservation: Striped bass field guide", "https://www.wildlifedepartment.com/wildlife/field-guide/fish/bass-striped", "agency"),
        Source("odwc-hybrid-fg", "Oklahoma Dept. of Wildlife Conservation: Hybrid striped bass field guide", "https://www.wildlifedepartment.com/wildlife/field-guide/fish/bass-striped-hybrid", "agency"),
        Source("odwc-wcp", "Oklahoma Dept. of Wildlife Conservation: White crappie field guide", "https://www.wildlifedepartment.com/wildlife/field-guide/fish/crappie-white", "agency"),
        Source("odwc-bcp", "Oklahoma Dept. of Wildlife Conservation: Black crappie field guide", "https://www.wildlifedepartment.com/wildlife/field-guide/fish/crappie-black", "agency"),
        Source("odwc-fish-id", "Oklahoma Dept. of Wildlife Conservation: Fish identification", "https://wildlifedepartment.com/outdoorok/ooj/chapter-5-fish-identification", "agency"),
        Source("va-crappie", "Virginia DWR: Four tactics for spring crappie", "https://dwr.virginia.gov/blog/four-great-tactics-for-spring-crappie-success/", "agency"),
        Source("agfc-hooks", "Arkansas Game & Fish: Getting to the point on hooks", "https://www.agfc.com/news/getting-to-the-point-on-fishing-hooks/", "agency"),
        Source("utah-cat", "Utah DWR: Catfish at Pole Creek", "https://wildlife.utah.gov/wildlife-news/647-pole-creek.html", "agency"),
        Source("al-tfs", "Outdoor Alabama: Threadfin Shad", "https://outdooralabama.com/other-species/threadfin-shad", "agency"),
        # Publications and guides
        Source("tmf-bass", "Take Me Fishing: Bass fishing tips", "https://www.takemefishing.org/how-to-fish/fishing-tips/bass-fishing-tips/", "publication"),
        Source("tmf-cat", "Take Me Fishing: How to catch catfish", "https://www.takemefishing.org/how-to-fish/how-to-catch-fish/how-to-catch-catfish/", "publication"),
        Source("tmf-bluegill", "Take Me Fishing: How to catch bluegill", "https://www.takemefishing.org/how-to-fish/how-to-catch-fish/how-to-catch-bluegill/", "publication"),
        Source("mercury-spb", "Mercury Marine Dockline: Spotted bass basics", "https://www.mercurymarine.com/us/en/lifestyle/dockline/spotted-bass-fishing-basics", "publication"),
        Source("coastal-sandbass", "Coastal Angler: The sand bass are running (reprints a 2024 TPWD release)", "https://coastalanglermag.com/the-sand-bass-are-running/", "publication"),
        Source("buckley-striper", "Buckley's Striper Guide: Live bait on Lake Texoma", "https://buckleystriperguide.com/complete-guide-to-live-bait-fishing-for-striped-bass-on-lake-texoma/", "guide"),
        Source("catfishedge-shad", "Catfish Edge: Shad as catfish bait", "https://www.catfishedge.com/shad-catfish-bait/", "guide"),
        Source("tacklevillage-shad", "Tackle Village: How to catch shad", "https://tacklevillage.com/how-to-catch-shad/", "guide"),
        # Added with the knowledge-base expansion (docs/adr/0024). Every page
        # below was opened and read; the facts taken from each are the ones
        # the guides and the handbook state.
        Source("tpwd-flc", "TPWD: Flathead Catfish", "https://tpwd.texas.gov/huntwild/wild/species/catfish", "agency"),
        Source("tpwd-gdb", "TPWD: Guadalupe Bass", "https://tpwd.texas.gov/huntwild/wild/species/gdb", "agency"),
        Source("tpwd-rsf", "TPWD: Redear Sunfish", "https://tpwd.texas.gov/huntwild/wild/species/sunfish/", "agency"),
        Source("tpwd-rbt", "TPWD: Rainbow Trout", "https://tpwd.texas.gov/huntwild/wild/species/rbt", "agency"),
        Source("tpwd-fwd", "TPWD: Freshwater Drum", "https://tpwd.texas.gov/huntwild/wild/species/fwd/", "agency"),
        Source("tpwd-crp", "TPWD: Common Carp", "https://tpwd.texas.gov/huntwild/wild/species/crp/", "agency"),
        Source("tpwd-sunfish-id", "TPWD: Texas sunfish identification sheet (2015)", "https://tpwd.texas.gov/publications/pwdpubs/media/pwd_lf_k0700_0692a.pdf", "agency"),
        Source("tpwd-trout-2025", "TPWD news release: rainbow trout stocking (Nov. 2025)", "https://tpwd.texas.gov/newsmedia/releases/?req=20251120b", "agency"),
        Source("tpwd-cr", "TPWD Outdoor Annual: catch and release tips", "https://tpwd.texas.gov/regulations/outdoor-annual/fishing/catch-release-tips", "agency"),
        Source("tpwd-consumption", "TPWD Outdoor Annual: fish consumption bans and advisories", "https://tpwd.texas.gov/regulations/outdoor-annual/fishing/general-rules-regulations/fish-consumption-bans-and-advisories", "agency"),
        Source("tamu-rsf", "Texas A&M Fisheries: Redear Sunfish", "https://fisheries.tamu.edu/pond-management/species/redear-sunfish", "agency"),
        Source("tamu-gdb", "Texas A&M AgriLife Extension: The state fish of Texas, Guadalupe bass", "https://extension.rwfm.tamu.edu/wp-content/uploads/sites/8/2013/09/The-State-Fish-of-Texas-Guadalupe-Bass.pdf", "agency"),
        Source("tamu-baits", "Take Me Fishing, via Texas A&M AgriLife Extension: Basic freshwater baits", "https://extension.rwfm.tamu.edu/wp-content/uploads/sites/8/2019/02/tmf_basic_freshwater_baits.pdf", "agency"),
        Source("tamu-hook-bait", "Texas A&M AgriLife Extension: How to hook bait", "https://extension.rwfm.tamu.edu/wp-content/uploads/sites/8/2013/09/How-to-Hook-Bait.pdf", "agency"),
        Source("mdc-bait-lures", "Missouri Dept. of Conservation: Bait and lures", "https://mdc.mo.gov/fishing/get-started-fishing/bait-lures", "agency"),
        Source("mdc-flathead", "Missouri Conservationist: Hunting flathead catfish (1997)", "https://mdc.mo.gov/magazines/conservationist/1997-05/hunting-flathead-catfish", "agency"),
        Source("mdc-trout", "Missouri Dept. of Conservation: Trout fishing tips", "https://mdc.mo.gov/index%2Ephp/fishing/species/trout/trout-fishing-tips", "agency"),
        Source("mdc-striper-fg", "Missouri Dept. of Conservation field guide: Striped Bass", "https://mdc.mo.gov/discover-nature/field-guide/striped-bass", "agency"),
        Source("mdc-hybrid-fg", "Missouri Dept. of Conservation field guide: Hybrid Striped Bass", "https://mdc.mo.gov/discover-nature/field-guide/hybrid-striped-bass-wiper-whiterock-bass", "agency"),
        Source("odwc-catfish", "Oklahoma Dept. of Wildlife Conservation: Catfish angler guide", "https://www.wildlifedepartment.com/outdoorok/ooj/catfish-angler-guide-top-tips-area-highlights", "agency"),
        Source("odwc-trout", "Oklahoma Dept. of Wildlife Conservation: How to catch trout", "https://wildlifedepartment.com/ooj/how-catch-trout", "agency"),
        Source("agfc-drum", "Arkansas Game & Fish: Drumming up spring fishing excitement", "https://www.agfc.com/news/drumming-up-spring-fishing-excitement/", "agency"),
        Source("kyfw-redear", "Kentucky Fish & Wildlife: May is a great time for redear sunfish (2021)", "https://fw.ky.gov/Fish/Pages/May-is-a-Great-Time-for-Redear-Sunfish.aspx", "agency"),
        Source("nydec-carp", "New York DEC: Carp fishing", "https://dec.ny.gov/things-to-do/freshwater-fishing/places-to-fish/statewide-opportunities/carp", "agency"),
        Source("ks-cleaning", "Kansas Dept. of Wildlife & Parks: Cleaning and preparing fish", "https://ksoutdoors.gov/Fishing/Special-Fishing-Programs-for-You/Pond-Management-Program/Producing-Fish-and-Wildlife-in-Kansas-Ponds/Fishing-the-Pond/Cleaning-and-Preparing-Fish", "agency"),
        Source("utah-clean-cat", "Utah DWR: How to clean and prepare catfish (2024)", "https://wildlife.utah.gov/blog/2024/05/03/how-to-clean-and-prepare-catfish", "agency"),
        Source("lsu-handling", "Louisiana Sea Grant: Handling offshore catch on board", "https://www.seagrantfish.lsu.edu/pdfs/factsheets/handling_offshorecatch.pdf", "agency"),
        Source("foodsafety-temps", "Hawaii Dept. of Health, from FoodSafety.gov: safe cooking temperatures", "https://www.health.hawaii.gov/food-drug/files/2024/02/Food-Safety-Control-Temperature-Updated.pdf", "agency"),
        Source("tmf-live-bait", "Take Me Fishing: What is good bait for freshwater fishing (2022)", "https://www.takemefishing.org/blog/december-2022/what-is-good-bait-for-freshwater-fishing/", "publication"),
        Source("tmf-lures", "Take Me Fishing: Lures every beginner should have (2019)", "https://www.takemefishing.org/blog/april-2019/lure-fishing-for-beginners-lures-every-angler-should-have/", "publication"),
        Source("tmf-reels", "Take Me Fishing: A brief guide to fishing reels (2022)", "https://www.takemefishing.org/blog/march-2022/a-brief-guide-to-fishing-reels/", "publication"),
        Source("tmf-weights", "Take Me Fishing: Fishing weights and bobbers", "https://www.takemefishing.org/how-to-fish/fishing-gear-and-tackle/fishing-weights-bobbers/", "publication"),
        Source("tmf-drum", "Take Me Fishing: Can you beat a drum? (2015)", "https://www.takemefishing.org/blog/june-2015/can-you-beat-a-drum/", "publication"),
        Source("fs-line", "Field & Stream: Fishing line types", "https://www.fieldandstream.com/gear/fishing-line-types/", "publication"),
        Source("meateater-rods", "MeatEater: Rod action and power explained", "https://themeateater.com/fish/general/conventional-fishing-rod-action-and-power-explained", "publication"),
        Source("zebco-knots", "Zebco Academy: Simple knots", "https://core-prod.zebco.com/en/academy/getting-started/simple-knots", "publication"),
        Source("flyfisherman-gdb", "Fly Fisherman: Hill Country bass", "https://www.flyfisherman.com/editorial/hill-country-bass/151717", "publication"),
        Source("texasmonthly-gdb", "Texas Monthly: How to catch Guadalupe bass", "https://www.texasmonthly.com/travel/how-to-catch-guadalupe-bass/", "publication"),
        Source("tpwmag-trout-2005", "Texas Parks & Wildlife magazine: winter trout (2005)", "https://tpwmagazine.com/archive/2005/jan/scout2/", "publication"),
        Source("torwicks-gdb", "Torwick's Guiding Service: Catching the Guadalupe bass", "https://www.torwicksguidingservice.com/single-post/how-to-target-and-catch-the-state-fish-of-texas-the-guadalupe-bass", "guide"),
        # Added with docs/adr/0026: casting, playing a fish, conditions,
        # safety, the licence and Texas rules, and cooking a catch.
        Source("tpwd-measure", "TPWD Outdoor Annual: measurement tips", "https://tpwd.texas.gov/regulations/outdoor-annual/fishing/measurement-tips", "agency"),
        Source("tpwd-license", "TPWD Outdoor Annual: fishing licenses and packages", "https://tpwd.texas.gov/regulations/outdoor-annual/licenses/fishing-licenses-stamps-tags-packages/fishing-licenses-and-packages", "agency"),
        Source("tpwd-beginners", "TPWD: Fishing for beginners", "https://tpwd.texas.gov/fishboat/fish/fishing-for-beginners/", "agency"),
        Source("tpwd-cdd", "TPWD: Protect our waters \u2014 clean, drain and dry", "https://tpwd.texas.gov/fishboat/boat/protect_water", "agency"),
        Source("tpwd-lifejacket", "TPWD Boater Education: life jackets", "https://tpwd.texas.gov/education/boater-education/lifejacket", "agency"),
        Source("nydec-where", "New York DEC: where to fish in lakes and ponds", "https://dec.ny.gov/things-to-do/freshwater-fishing/learn-to-fish/tips-skills/where-to-fish-lakes-ponds", "agency"),
        Source("indnr-when", "Indiana DNR: fishing tips \u2014 when and where", "https://www.in.gov/dnr/fish-and-wildlife/education-programs/learn-to-fish/fishing-tips-and-videos/fishing-tips-when-and-where/", "agency"),
        Source("kyfw-weather", "Kentucky Fish & Wildlife: best weather trends for spring fishing", "https://fw.ky.gov/Fish/Pages/Best-Weather-Trends-for-Spring-Fishing.aspx", "agency"),
        Source("umn-fish", "University of Minnesota Extension: safely choose, cook and store fish", "https://extension.umn.edu/preserving-and-preparing/safely-choose-cook-and-store-fish", "university"),
        Source("uaf-freezing", "University of Alaska Fairbanks Extension: home freezing of fish", "https://www.uaf.edu/ces/publications/database/food/freezing-fish.php", "university"),
        Source("tamu-catfish-cook", "Texas A&M AgriLife Extension / SRAC: You can do catfish", "https://extension.rwfm.tamu.edu/wp-content/uploads/sites/9/2010/04/6_You_Can_Do_Catfish.pdf", "university"),
        Source("tmf-cast", "Take Me Fishing: how to cast", "https://www.takemefishing.org/how-to-fish/how-to-catch-fish/how-to-cast/", "publication"),
        Source("tmf-drag", "Take Me Fishing: how to set the drag", "https://www.takemefishing.org/how-to-fish/how-to-catch-fish/how-to-set-the-drag/", "publication"),
        Source("tmf-shore", "Take Me Fishing: shore fishing", "https://takemefishing.org/how-to-fish/types-of-fishing/shore-fishing", "publication"),
        Source("tmf-line-recycle", "Take Me Fishing: recycling old fishing line", "https://www.takemefishing.org/how-to-fish/fishing-and-conservation/recycling-old-fishing-line/", "publication"),
        # Georgia (docs/adr/0028). The DNR's Wildlife Resources Division,
        # and the online edition of its 2026 regulations guide (the guide
        # carries the DNR Commissioner's message; WRD's own copy is a
        # flip-book that can't be cited by page).
        Source("gawrd-license", "Georgia WRD: what license do I need?", "https://georgiawildlife.com/licenses-permits-passes/choose", "agency"),
        Source("gawrd-angler", "Georgia WRD: fishing in Georgia", "https://georgiawildlife.com/fishing/angler-resources", "agency"),
        Source("gawrd-parkfishing", "Georgia State Parks: fishing and the tackle loaner program", "https://georgiawildlife.com/ParkFishing", "agency"),
        Source("gawrd-equipment", "Georgia WRD: required boating equipment", "https://georgiawildlife.com/required-equipment", "agency"),
        Source("gawrd-cdd", "Georgia WRD: practice Clean, Drain, Dry", "https://georgiawildlife.com/how-can-you-prevent-ans-practice-clean-drain-dry", "agency"),
        Source("garegs-license", "Georgia Fishing Regulations 2026: license requirements", "https://www.eregulations.com/georgia/fishing/license-requirements", "agency"),
        Source("garegs-general", "Georgia Fishing Regulations 2026: general freshwater regulations", "https://www.eregulations.com/georgia/fishing/general-regulations", "agency"),
        Source("garegs-methods", "Georgia Fishing Regulations 2026: fishing methods", "https://www.eregulations.com/georgia/fishing/fishing-methods", "agency"),
        Source("garegs-boating", "Georgia Fishing Regulations 2026: boating", "https://www.eregulations.com/georgia/fishing/boating", "agency"),
        Source("garegs-bordering", "Georgia Fishing Regulations 2026: agreements with bordering states", "https://www.eregulations.com/georgia/fishing/agreements-with-bordering-states", "agency"),
    ]
}


@dataclass(frozen=True)
class TackleSetup:
    name: str
    use_when: str
    method: str  # "lure" (artificial) | "bait" (live/natural) | "either" — which group this belongs in
    rod: str
    reel: str
    line: str
    terminal: str  # hook, rig, or lure — what goes on the end of the line
    source_ids: tuple[str, ...]


# What each species mainly eats, in one word for a UI badge. "carnivore"
# covers fish that eat mostly other animals (fish, crayfish, insects);
# "omnivore" eats a broad mix including plants; "filter_feeder" strains
# tiny food from the water rather than pursuing prey, and never really
# bites a hook (the forage fish here are both filter feeders).
DIET_TYPES = ("carnivore", "omnivore", "filter_feeder")

DIET_TYPE_LABEL = {
    "carnivore": "Carnivore",
    "omnivore": "Omnivore",
    "filter_feeder": "Filter feeder",
}


@dataclass(frozen=True)
class SpeciesGuide:
    common_name: str
    scientific_name: str
    role: str  # "sport" | "forage"
    difficulty: str | None  # "beginner" | "intermediate" | "advanced"; None for forage fish
    summary: str
    diet: str
    diet_type: str  # one of DIET_TYPES
    where_and_when: tuple[str, ...]
    live_baits: tuple[str, ...] = ()
    lures: tuple[str, ...] = ()
    setups: tuple[TackleSetup, ...] = ()
    tips: tuple[str, ...] = ()
    # How to tell this fish from the ones it's confused with. Written as
    # matching features across look-alikes (jaw vs eye, tooth patches,
    # stripes, dorsal spines, anal fin) so a question about two fish can be
    # answered by setting their passages side by side.
    identification: tuple[str, ...] = ()
    # Where it lives (water type, depth, bottom, temperature) and how it
    # behaves (schooling, feeding times, seasonal moves, spawning), mostly
    # from TPWD's own species pages. Kept apart from where_and_when, which is
    # angler advice on where to look.
    habitat: tuple[str, ...] = ()
    habits: tuple[str, ...] = ()
    # Why the baits above work for this fish: each reason ties a bait to
    # something a source says about what the fish eats or how it feeds.
    why_these_baits: tuple[str, ...] = ()
    # Cleaning and eating, where a source says something specific to this
    # fish. General cleaning steps are in the handbook (angling_handbook.py).
    eating: tuple[str, ...] = ()
    # Forage fish only: how anglers get them, and what they're bait for.
    how_to_get: tuple[str, ...] = ()
    bait_for: tuple[str, ...] = ()
    legal_notes: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = field(default=())

    @property
    def slug(self) -> str:
        return slugify(self.common_name)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# Rules that decide what may go on the hook and where. Paraphrased closely
# from TPWD's general fishing regulations (tpwd-regs-general), keeping every
# condition and exception, because a looser summary would be wrong.
BAIT_RULES = (
    "It is unlawful to use any game fish, or part of a game fish, as bait. Nongame "
    "fish, such as shad, are legal bait (TPWD).",
    "Live bait may not be carried away from the lake where it was caught, in or "
    "aboard a boat, in that lake's water. Keeping it in lake water while you fish "
    "from a boat on that same lake is allowed (TPWD).",
    "Store-bought live bait that has touched water from a public lake or river may "
    "only be used on that same water (TPWD).",
)

_CRAPPIE_SETUPS = (
    TackleSetup(
        name="Minnow under a bobber",
        use_when="The classic way, especially around brush piles and docks in spring.",
        method="bait",
        rod="6–7 ft light spinning rod",
        reel="Small spinning reel",
        line="4–8 lb",
        terminal=(
            "Thin-wire hook, size #2–#6 (sources range from #1 to #10), one or two "
            "split shot, and a 1½–2½ in live minnow. Set the bobber 6–10 ft deep; "
            "use a slip bobber to fish deeper."
        ),
        source_ids=("va-crappie", "agfc-hooks", "mn-crappie"),
    ),
    TackleSetup(
        name="Small jig",
        use_when="Casting to cover, or once you've found a school.",
        method="lure",
        rod="6–7 ft light spinning rod",
        reel="Small spinning reel",
        line="4–8 lb (6 lb mono is a good default)",
        terminal=(
            "1/32–1/16 oz jig with a small soft-plastic body. Try chartreuse, white, "
            "black, yellow or pink."
        ),
        source_ids=("mdc-crappie", "va-crappie", "mn-crappie"),
    ),
    TackleSetup(
        name="Long pole, straight down",
        use_when="Dipping a jig or minnow into thick brush without casting.",
        method="either",
        rod="9–10 ft or longer pole (a cane pole or fly rod works)",
        reel="None needed",
        line="4–8 lb",
        terminal="Jig or minnow lowered straight into the cover.",
        source_ids=("va-crappie",),
    ),
)

_BASE_GUIDES: tuple[SpeciesGuide, ...] = (
    SpeciesGuide(
        common_name="Largemouth Bass",
        scientific_name="Micropterus salmoides",
        role="sport",
        difficulty="beginner",
        summary=(
            "Texas's most sought-after freshwater fish. It hides in cover and ambushes "
            "prey, so fish your bait close to logs, weeds and docks."
        ),
        diet="Adults eat almost only other fish and crayfish.",
        diet_type="carnivore",
        identification=(
            "A dark stripe runs along each side.",
            "With the mouth closed, the jaw reaches well past the back edge of the eye. This is the quickest way to tell it from a spotted bass.",
            "Most have no tooth patch on the tongue.",
        ),
        where_and_when=(
            "Near cover: logs, rock ledges, weeds, docks, bridges, sunken trees and drop-offs.",
            "Spawns in spring when the water reaches about 60°F, anywhere from February "
            "to May in Texas, on nests 2–8 ft deep.",
            "Topwater lures work best early in the morning and toward dark.",
        ),
        live_baits=("Large live shiners (8–9 in) under a bobber.",),
        lures=(
            "Plastic worms",
            "Jigs",
            "Soft-plastic crayfish, frogs and lizards",
            "Spinnerbaits",
            "Crankbaits and ¼–½ oz lipless crankbaits",
            "Swimbaits",
            "Topwater lures",
        ),
        setups=(
            TackleSetup(
                name="Beginner spinning",
                use_when="Your first bass setup; open water and light cover.",
                method="lure",
                rod="Medium-action spinning rod",
                reel="Spinning reel",
                line="6–8 lb",
                terminal="Plastic grub on a 1/8–1/4 oz round jighead.",
                source_ids=("mdc-bass",),
            ),
            TackleSetup(
                name="Texas-rigged worm",
                use_when="Working a plastic worm around wood, docks and weeds.",
                method="lure",
                rod="6–8 ft baitcasting rod (7–7½ ft is a good all-round length)",
                reel="Baitcasting reel",
                line="15 lb or heavier",
                terminal="6–7 in plastic worm on a 3/0 worm hook with a 1/8 oz bullet sinker.",
                source_ids=("mn-lmb", "fwc-bass"),
            ),
            TackleSetup(
                name="Flipping heavy cover",
                use_when="Thick or matted weeds where a hooked fish has to be pulled out fast.",
                method="lure",
                rod="7'6\" or longer casting rod",
                reel="Baitcasting reel",
                line="65 lb braid or stronger",
                terminal="3/0–4/0 flipping hook with a soft-plastic bait.",
                source_ids=("fwc-bass",),
            ),
            TackleSetup(
                name="Live shiner",
                use_when="Big bass, fished slowly near cover.",
                method="bait",
                rod="A rod rated for 30 lb line",
                reel="Spinning or baitcasting reel",
                line="Heavy mono, around 30 lb",
                terminal="4/0–5/0 hook through both lips of an 8–9 in shiner, under a bobber.",
                source_ids=("fwc-bass",),
            ),
        ),
        tips=(
            "If fish are active near the surface, use bigger lures and reel faster. If "
            "they're holding near the bottom, slow down and go smaller.",
            "A bass will almost always eat a real shiner or crayfish faster than a "
            "plastic one — but an inactive bass may strike a fast-moving topwater plug "
            "or buzzbait out of annoyance when it would ignore a live shiner sitting "
            "still under a bobber. Use live bait for a bass you know is feeding; switch "
            "to lures to provoke one that isn't.",
        ),
        source_ids=(
            "tpwd-lmb",
            "mn-lmb",
            "tmf-bass",
            "fwc-bass",
            "mdc-bass",
            "tpwd-bass-id",
            "odwc-fish-id",
        ),
    ),
    SpeciesGuide(
        common_name="Spotted Bass",
        scientific_name="Micropterus punctulatus",
        role="sport",
        difficulty="intermediate",
        summary=(
            "A smaller cousin of the largemouth that likes current, rock and deeper water, "
            "and travels in schools. Light line and small soft plastics catch the most."
        ),
        diet="Fish and crayfish. It ambushes shad and crawfish where deep water rises to shallow.",
        diet_type="carnivore",
        identification=(
            "The side stripe is more broken than a largemouth bass's.",
            "With the mouth closed, the jaw ends at the back edge of the eye, not past it as on a largemouth bass.",
            "Rows of dark spots on the whitish belly look like thin stripes.",
            "Has a tooth patch on the tongue; most largemouth bass don't.",
        ),
        where_and_when=(
            "Likes more current than largemouth. Native to East Texas rivers such as the "
            "Sabine, Neches and Cypress.",
            "Spawns over rock or gravel when the water is 57–74°F.",
            "In reservoirs: main-lake points, creek mouths and the lower lake near the dam, "
            "5–15 ft deep, often suspended off the bottom in clearer water.",
        ),
        lures=(
            "4–6 in straight-tail worms (green pumpkin or watermelon) on a shaky head or drop shot",
            "5 in stick-style worms",
        ),
        setups=(
            TackleSetup(
                name="Shaky head",
                use_when="The go-to setup: dragged slowly along points and rock.",
                method="lure",
                rod="7 ft medium to medium-heavy spinning rod",
                reel="Spinning reel",
                line="6–10 lb",
                terminal="1/8–1/4 oz shaky-head jig with a 4–6 in straight-tail worm.",
                source_ids=("mercury-spb",),
            ),
            TackleSetup(
                name="Braid with a fluorocarbon leader",
                use_when="Deeper, clearer water where the fish can see heavy line.",
                method="lure",
                rod="7'1\" medium spinning rod",
                reel="Spinning reel",
                line="12 lb braid main line, 8 lb fluorocarbon leader",
                terminal="Drop-shot rig or shaky head.",
                source_ids=("mercury-spb",),
            ),
        ),
        tips=(
            "Drag a shaky head slowly across deep points, 10–40 ft down.",
            "They school: once you catch one, stay put and keep casting there.",
        ),
        source_ids=("tpwd-spb", "mercury-spb", "tpwd-bass-id", "odwc-fish-id"),
    ),
    SpeciesGuide(
        common_name="White Bass",
        scientific_name="Morone chrysops",
        role="sport",
        difficulty="beginner",
        summary=(
            "Called sand bass in Texas. Schools chase shad in open water, and each spring "
            "they run up rivers and creeks to spawn: the easiest time to catch a lot of them."
        ),
        diet="Gizzard and threadfin shad above all; also insects and crustaceans near the surface.",
        diet_type="carnivore",
        identification=(
            "Faint stripes, often broken; only one reaches the tail.",
            "A deep body with an arched back: the body is deeper than 1/3 of its length.",
            "One tooth patch near the middle of the back of the tongue. Striped bass and hybrid striped bass have two.",
        ),
        where_and_when=(
            "Spring run: they leave the reservoir and swim up rivers and creeks to spawn over "
            "gravel or rock in moving water.",
            "The run starts around 50°F water and peaks at 55–60°F. Texas runs include the "
            "Sabine above Toledo Bend, the Neches above Lake Palestine and the San Gabriel "
            "above Granger Lake.",
            "The rest of the year: open water and main-lake humps. Diving gulls mark schools "
            "feeding on shad, especially early, late, or on cloudy days.",
            "Most active at dawn and dusk. At night, try lighted docks.",
        ),
        live_baits=("2–4 in minnows or shad", "Worms", "Crickets"),
        lures=(
            "2–3 in curly-tail grubs on a jighead",
            "Inline spinners",
            "Slabs and jigging spoons",
            "Small crankbaits",
            "Topwater lures when schools are breaking the surface",
        ),
        setups=(
            TackleSetup(
                name="Grub or spinner",
                use_when="The spring run, and schools near the surface.",
                method="lure",
                rod="Medium-light to medium spinning rod; a longer rod casts farther",
                reel="Spinning reel",
                line="6–12 lb",
                terminal="2–3 in curly-tail grub on a 1/16–1/4 oz jighead, or an inline spinner.",
                source_ids=("odwc-whitebass", "mdc-bass"),
            ),
            TackleSetup(
                name="Slab jigging",
                use_when="Schools deep in open water, found with a fish finder.",
                method="lure",
                rod="Medium spinning rod",
                reel="Spinning reel",
                line="6–12 lb",
                terminal="½ oz slab or jigging spoon, dropped to the bottom and jigged.",
                source_ids=("odwc-whitebass", "tpwd-tawakoni"),
            ),
            TackleSetup(
                name="Live minnow",
                use_when="Slow days, and bottom fishing at night.",
                method="bait",
                rod="Medium-light spinning rod",
                reel="Spinning reel",
                line="6–12 lb",
                terminal="A live 2–4 in minnow or shad, on the bottom or under a float.",
                source_ids=("odwc-whitebass", "tpwd-wtb"),
            ),
        ),
        tips=(
            "Keep a steady retrieve close to the bottom.",
        ),
        legal_notes=BAIT_RULES,
        source_ids=(
            "tpwd-wtb",
            "tpwd-tawakoni",
            "odwc-whitebass",
            "coastal-sandbass",
            "mdc-bass",
            "tpwd-bass-id",
            "odwc-fish-id",
        ),
    ),
    SpeciesGuide(
        common_name="Striped Bass",
        scientific_name="Morone saxatilis",
        role="sport",
        difficulty="advanced",
        summary=(
            "Big, hard-fighting fish that roam open water in schools chasing shad. Usually "
            "fished from a boat. Lake Texoma, on the Texas–Oklahoma border, is known for them."
        ),
        diet="Shad, minnows and insects.",
        diet_type="carnivore",
        identification=(
            "Strong, dark, unbroken stripes, several of them reaching the tail.",
            "A slender body with a flat back: the body is less than 1/3 as deep as it is long.",
            "Two distinct tooth patches near the middle of the back of the tongue.",
        ),
        where_and_when=(
            "Schools in open water and avoids the shoreline.",
            "On Lake Texoma the best months are May–June and October–December.",
            "Topwater action is best in the first two hours of daylight; the fish go deeper as "
            "the sun rises. Diving, squawking gulls mean a school is feeding.",
            "In winter they hold near underwater structure.",
        ),
        live_baits=("Live threadfin or gizzard shad",),
        lures=(
            "6 in pencil poppers (topwater)",
            "1–2 oz slabs in chartreuse, chrome or white",
            "Swimbaits",
            "Bucktail jigs",
            "Jigging spoons",
        ),
        setups=(
            TackleSetup(
                name="Topwater and slabs",
                use_when="Schools busting shad at the surface, or deep schools on the fish finder.",
                method="lure",
                rod="Rod rated for 1–2 oz lures",
                reel="Spinning or baitcasting reel",
                line="20 lb",
                terminal="6 in pencil popper, or a 1–2 oz slab.",
                source_ids=("tpwmag-texoma-2014",),
            ),
            TackleSetup(
                name="Live shad drift",
                use_when="Drifting slowly over schools.",
                method="bait",
                rod="Medium to medium-heavy rod",
                reel="Spinning, spincast or baitcasting reel",
                line="8–14 lb",
                terminal="Size 1 to 3/0 circle hook and a ½–3 oz sinker, drifted at about 0.5–1 mph.",
                source_ids=("buckley-striper", "odwc-striper"),
            ),
            TackleSetup(
                name="All-round",
                use_when="A lighter setup that also covers hybrids and white bass.",
                method="either",
                rod="Medium to medium-heavy rod",
                reel="Spinning, spincast or baitcasting reel",
                line="8–14 lb",
                terminal="Slab, jighead with grub, or live shad.",
                source_ids=("odwc-striper",),
            ),
        ),
        tips=(
            "Drop a slab to the bottom, then reel it up as fast as you can.",
            "With circle hooks, don't jerk. Keep reeling and let the fish load the rod.",
        ),
        legal_notes=BAIT_RULES,
        source_ids=(
            "odwc-striper-fg",
            "odwc-striper",
            "tpwmag-texoma-2014",
            "tpwmag-texoma-2020",
            "tpwd-tawakoni",
            "buckley-striper",
            "tpwd-bass-id",
            "odwc-fish-id",
        ),
    ),
    SpeciesGuide(
        common_name="Hybrid Striped Bass",
        scientific_name="Morone saxatilis × Morone chrysops",
        role="sport",
        difficulty="intermediate",
        summary=(
            "A cross between striped bass and white bass that TPWD has stocked since 1972. "
            "Like both parents, it schools up and chases shad."
        ),
        diet="Threadfin and gizzard shad; also minnows, crustaceans and insects.",
        diet_type="carnivore",
        identification=(
            "Distinct stripes, usually broken, several of them reaching the tail. A striped bass's stripes are unbroken; a white bass's are faint.",
            "A deep body with a slightly arched back: the body is deeper than 1/3 of its length, unlike the slender striped bass.",
            "Two tooth patches on the back of the tongue, sometimes close together. A white bass has one.",
        ),
        where_and_when=(
            "Open-water schools, most active at dawn and dusk.",
            "Early morning: topwater near the banks. Midday: follow birds working the water.",
            "Best in May, during the shad spawn, and in fall. Try windblown points, riprap "
            "and dams, and main-lake humps and points.",
        ),
        live_baits=("2–4 in live shad or fathead minnows",),
        lures=(
            "½ oz lipless crankbaits",
            "Grubs on 1/8–½ oz jigheads",
            "¼–1 oz slabs",
            "Blade baits",
            "White or chartreuse marabou jigs in low light",
        ),
        setups=(
            TackleSetup(
                name="All-round casting",
                use_when="Casting to schools and points.",
                method="lure",
                rod="Medium to medium-heavy rod",
                reel="Spinning, spincast or baitcasting reel",
                line="8–14 lb",
                terminal="½ oz lipless crankbait, or a grub on a 1/8–½ oz jighead.",
                source_ids=("odwc-striper",),
            ),
            TackleSetup(
                name="Vertical slab",
                use_when="Nothing showing on the surface; fish holding near the bottom.",
                method="lure",
                rod="Medium to medium-heavy rod",
                reel="Spinning or baitcasting reel",
                line="8–14 lb",
                terminal="¼–1 oz slab jigged near the bottom.",
                source_ids=("odwc-striper", "tpwd-tawakoni"),
            ),
            TackleSetup(
                name="Live shad",
                use_when="Slow bites, or anchored over a school.",
                method="bait",
                rod="Medium to medium-heavy rod",
                reel="Spinning or baitcasting reel",
                line="8–14 lb",
                terminal="A live 2–4 in shad or fathead minnow.",
                source_ids=("odwc-striper", "tpwd-tawakoni"),
            ),
        ),
        tips=(
            "Once you find a feeding school they'll bite almost anything. Keep casting to it.",
            "If nothing's on the surface, jig slabs near the bottom.",
        ),
        legal_notes=BAIT_RULES,
        source_ids=(
            "tamu-hsb",
            "odwc-hybrid-fg",
            "odwc-striper",
            "tpwmag-hybrid-2014",
            "tpwd-tawakoni",
            "tpwd-bass-id",
            "odwc-fish-id",
        ),
    ),
    SpeciesGuide(
        common_name="Channel Catfish",
        scientific_name="Ictalurus punctatus",
        role="sport",
        difficulty="beginner",
        summary=(
            "The classic first fish: found all over Texas, eats almost anything, and TPWD "
            "stocks them in city ponds through its Neighborhood Fishin' program."
        ),
        diet="Almost anything: insects, snails and clams, crayfish, fish and some plants.",
        diet_type="omnivore",
        identification=(
            "Dark spots on the body, though large adults may lose them.",
            "The outer edge of the anal fin is rounded, with 24 to 29 rays. A blue catfish's is straight.",
        ),
        where_and_when=(
            "Found statewide. Spawns in late spring or early summer at about 75°F water.",
            "Moves into the shallows at night from late spring to early fall. By day, look in "
            "deeper holes and around sunken timber out of the current.",
            "Neighborhood Fishin' ponds are stocked every 2–4 weeks from late April to early "
            "November, except August.",
        ),
        live_baits=(
            "Nightcrawlers",
            "Chicken liver",
            "Shrimp (stays on the hook well)",
            "Stinkbait",
            "Cut hot dogs or cheese",
        ),
        lures=("A plastic worm dipped in catfish dip bait",),
        setups=(
            TackleSetup(
                name="Pond slip-sinker rig",
                use_when="City ponds and small lakes; the easiest place to start.",
                method="bait",
                rod="Spincast or spinning combo",
                reel="Spincast or spinning reel",
                line="8 lb or heavier",
                terminal=(
                    "#4 or #6 baitholder hook on an 18 in leader, with a ¼–½ oz egg sinker "
                    "and a swivel above it."
                ),
                source_ids=("utah-cat", "mn-ccf"),
            ),
            TackleSetup(
                name="Lake bottom rig",
                use_when="Bigger lakes and bigger fish.",
                method="bait",
                rod="7 ft or slightly longer",
                reel="Baitcasting reel preferred; spincast also works",
                line="15–20 lb",
                terminal=(
                    "1 oz egg sinker and a barrel swivel, about 2 ft of heavy leader, and a "
                    "4/0–6/0 circle or bait hook."
                ),
                source_ids=("mn-ccf",),
            ),
        ),
        tips=(
            "Use only enough weight to keep the bait on the bottom, then reel the line tight.",
            "A small treble hook holds soft baits like liver or cheese better.",
            "No bite in 15 minutes? Move to a new spot.",
            "In a creek or river, fresh cut shad's natural oil trail is hard to beat. In "
            "warm, murky or slow-moving water, a strong-smelling prepared stink bait "
            "carries just as well and is easier to keep on the hook.",
        ),
        source_ids=(
            "tpwd-ccf",
            "tpwd-nf",
            "tmf-cat",
            "mn-ccf",
            "mdc-cat",
            "utah-cat",
            "agfc-hooks",
            "tpwd-cat-id",
            "odwc-fish-id",
        ),
    ),
    SpeciesGuide(
        common_name="Blue Catfish",
        scientific_name="Ictalurus furcatus",
        role="sport",
        difficulty="intermediate",
        summary=(
            "The biggest catfish in Texas: the state record is 121.5 lb. It eats fish, so "
            "fresh cut shad is the bait to use, and it needs heavy tackle."
        ),
        diet="Fish once they're a few inches long, plus large invertebrates.",
        diet_type="carnivore",
        identification=(
            "No dark spots on the body.",
            "The outer edge of the anal fin is straight, with 30 to 36 rays. A channel catfish's is rounded.",
        ),
        where_and_when=(
            "Main river channels, tributaries and big reservoirs. Moves upstream in summer "
            "for cooler water and downstream in winter for warmer water.",
            "Winter is prime time in Texas. On sunny days, try shallow flats the sun has "
            "warmed. Or find schools of shad on a fish finder and fish at their depth.",
            "In summer: drop-offs, woody cover and areas near the main channel.",
        ),
        live_baits=(
            "Fresh cut shad (fresh beats frozen)",
            "Cut skipjack herring",
            "Live shad",
        ),
        setups=(
            TackleSetup(
                name="Big-fish rig",
                use_when="Anchored on channel edges and drop-offs.",
                method="bait",
                rod="7–10 ft medium-heavy to heavy rod",
                reel="Heavy-duty baitcasting or spinning reel",
                line="30–50 lb mono",
                terminal="6/0–8/0 circle hook with a 3–8 oz slip sinker.",
                source_ids=("mdc-bigcat",),
            ),
            TackleSetup(
                name="Winter drift",
                use_when="Drifting flats and shad schools in winter.",
                method="bait",
                rod="Same heavy rod as the big-fish rig",
                reel="Same as the big-fish rig",
                line="Same as the big-fish rig",
                terminal="8/0–10/0 circle hook with the lightest weight that still touches bottom.",
                source_ids=("tpwmag-bluecat-2020",),
            ),
        ),
        tips=(
            "Blues of 20–50 lb are common in some waters, so heavy gear isn't overkill.",
        ),
        legal_notes=BAIT_RULES,
        source_ids=(
            "tpwd-blc",
            "tpwmag-bluecat-2020",
            "mdc-bigcat",
            "mdc-cat",
            "tpwd-cedarcreek",
            "tpwd-cat-id",
            "odwc-fish-id",
        ),
    ),
    SpeciesGuide(
        common_name="White Crappie",
        scientific_name="Pomoxis annularis",
        role="sport",
        difficulty="intermediate",
        summary=(
            "A schooling panfish that holds around brush piles, sunken trees, docks and "
            "bridge pilings. Good to eat. A minnow under a bobber is the classic way to catch it."
        ),
        diet="Small fish (minnows and shad), insects and crayfish.",
        diet_type="carnivore",
        identification=(
            "Distinct vertical bars on the sides.",
            "5 to 6 spines in the dorsal fin; a black crappie has 7 or 8.",
            "Silvery, from white on the belly to green or dark green on the back.",
        ),
        where_and_when=(
            "Around sunken trees, brush piles, docks and bridge pilings. Handles muddier "
            "water than black crappie.",
            "Spawns in spring at 65–70°F in the shallow ends of coves, then moves 15 ft or deeper.",
            "Summer: suspended 10–20 ft deep near timber and creek channels. Winter: deep "
            "structure, especially along south-facing banks.",
            "Where you catch one, a school is usually close.",
        ),
        live_baits=("1½–2½ in minnows (the preferred bait)",),
        lures=(
            "Small soft-plastic jigs",
            "Beetle-spins",
            "Small jigging spoons",
            "Small poppers at dawn or dusk",
        ),
        setups=_CRAPPIE_SETUPS,
        tips=(
            "Crappie have soft mouths. Set the hook with a steady lift, not a hard jerk.",
            "Hold the jig still right next to the cover instead of jerking it.",
            "In fall, let the jig sink 2–3 seconds, then reel slowly.",
        ),
        source_ids=(
            "tpwd-wcp",
            "tpwd-crappie-spots",
            "odwc-wcp",
            "mdc-crappie",
            "mn-crappie",
            "va-crappie",
            "agfc-hooks",
            "odwc-fish-id",
        ),
    ),
    SpeciesGuide(
        common_name="Black Crappie",
        scientific_name="Pomoxis nigromaculatus",
        role="sport",
        difficulty="intermediate",
        summary=(
            "Like white crappie but prefers clearer water, and is most common in East and "
            "Northeast Texas. Fish it the same way."
        ),
        diet="Fewer fish and more insects and crustaceans than white crappie.",
        diet_type="carnivore",
        identification=(
            "Irregular black blotches with no clear pattern, instead of vertical bars.",
            "7 or 8 spines in the dorsal fin; a white crappie has 5 to 6.",
            "Deeper-bodied than a white crappie.",
        ),
        where_and_when=(
            "Most common in the clear waters of East and Northeast Texas.",
            "Spawns at about 60°F.",
            "Around standing timber and brush; moves deeper than 15 ft after spring.",
        ),
        live_baits=("1½–2½ in minnows",),
        lures=("Small soft-plastic jigs", "Beetle-spins", "Small jigging spoons"),
        # The crappie sources don't split tackle by species.
        setups=_CRAPPIE_SETUPS,
        tips=(
            "Crappie have soft mouths. Set the hook with a steady lift, not a hard jerk.",
            "Hold the jig still right next to the cover instead of jerking it.",
        ),
        source_ids=(
            "tpwd-bcp",
            "odwc-bcp",
            "mdc-crappie",
            "mn-crappie",
            "va-crappie",
            "agfc-hooks",
            "odwc-fish-id",
        ),
    ),
    SpeciesGuide(
        common_name="Bluegill",
        scientific_name="Lepomis macrochirus",
        role="sport",
        difficulty="beginner",
        summary=(
            "Fairly easy to catch, curious and not picky, and found in almost every Texas "
            "pond and lake, which makes it a great first fish."
        ),
        diet="Mostly aquatic insects and their larvae; midge larvae can be half its diet.",
        diet_type="omnivore",
        where_and_when=(
            "In fresh water all over Texas.",
            "Spawns from about 70°F, peaking in May–June and sometimes lasting into fall. "
            "Nests are 1–2 ft deep, often over gravel, and many are built close together; "
            "spawning fish use water 2–6 ft deep.",
            "Late summer: weed edges and brush piles more than 10 ft deep. Winter: 12–20 ft "
            "deep near cover.",
        ),
        live_baits=(
            "A small piece of worm or nightcrawler, just enough to cover the hook",
            "Crickets",
            "Grasshoppers",
            "Mealworms",
        ),
        lures=(
            "Tiny jigs, 1/32 oz and smaller (black works well)",
            "Tiny spinners",
            "Small black flies",
            "Small poppers",
        ),
        setups=(
            TackleSetup(
                name="Cane pole",
                use_when="Kids and first-timers: no casting or reeling.",
                method="bait",
                rod="Cane pole",
                reel="None: just flip the line out",
                line="2–6 lb",
                terminal="#6–#10 hook, a small split shot and a small bobber.",
                source_ids=("mdc-beginners", "mdc-bluegill"),
            ),
            TackleSetup(
                name="Spincast with a bobber",
                use_when="The standard beginner setup.",
                method="bait",
                rod="5–6½ ft rod",
                reel="Closed-face spincast reel (the easiest for beginners)",
                line="2–6 lb",
                terminal="#6–#10 hook, split shot above it, and a bobber 1–3 ft above the bait.",
                source_ids=("mdc-beginners", "mdc-bluegill"),
            ),
            TackleSetup(
                name="Ultralight lures",
                use_when="When you want to cast lures instead of bait.",
                method="lure",
                rod="Ultralight spinning rod",
                reel="Small spinning reel",
                line="2–6 lb",
                terminal="Jig of 1/32 oz or smaller, a tiny spinner, or a small fly.",
                source_ids=("mdc-bluegill",),
            ),
        ),
        tips=(
            "Use the smallest bobber that floats your bait. You'll see more bites.",
            "If you're fishing on the bottom, watch your line closely: bites are light.",
            "A small soft-plastic grub on a 1/16 oz tungsten jig under a slip bobber "
            "catches just as many bluegill as live bait, without rebaiting the hook "
            "every fish.",
        ),
        source_ids=("tpwd-bgl", "tmf-bluegill", "mdc-bluegill", "mdc-beginners"),
    ),
    SpeciesGuide(
        common_name="Gizzard Shad",
        scientific_name="Dorosoma cepedianum",
        role="forage",
        difficulty=None,
        summary=(
            "A bait fish, not a sport fish: it rarely bites a hook. Anglers catch it with a "
            "cast net to use as bait for catfish, stripers and hybrids."
        ),
        diet="A filter feeder: it strains tiny plants and animals from the water.",
        diet_type="filter_feeder",
        where_and_when=(
            "Around marinas and dock lights in the early morning, and in feeder creeks.",
        ),
        identification=(
            "Usually 9–14 in long.",
            "The upper jaw sticks out well past the lower jaw (threadfin shad's doesn't).",
        ),
        how_to_get=(
            "A cast net. TPWD allows cast nets up to 14 ft across, for nongame fish and "
            "other aquatic life such as crabs, crayfish and shrimp (not game fish).",
            "A smaller mesh (about 3/8 in) keeps shad from getting stuck in the net in shallow "
            "water; heavier nets sink faster in deep winter water.",
            "Keep them alive in an aerated bait tank.",
        ),
        bait_for=(
            "Blue catfish, as cut bait",
            "Striped bass and hybrid striped bass, live",
        ),
        tips=("Hook cut pieces shallow so the point of the hook stays exposed.",),
        legal_notes=BAIT_RULES,
        source_ids=(
            "tpwd-gsh",
            "tpwd-regs-devices",
            "tpwd-regs-general",
            "tpwd-cedarcreek",
            "tpwd-tawakoni",
            "catfishedge-shad",
            "tacklevillage-shad",
        ),
    ),
    SpeciesGuide(
        common_name="Threadfin Shad",
        scientific_name="Dorosoma petenense",
        role="forage",
        difficulty=None,
        summary=(
            "A small bait fish that almost never bites a hook. It's what striped bass, hybrids "
            "and white bass are chasing, so it makes excellent live bait. Catch it with a cast net."
        ),
        diet="A filter feeder.",
        diet_type="filter_feeder",
        where_and_when=(
            "Usually in the top 5 ft of water.",
            "Dies off when the water drops below 45°F.",
        ),
        identification=(
            "Rarely more than 6 in long.",
            "The upper jaw does not stick out past the lower jaw.",
            "A clearly yellow tail; anglers call them \"yellowtails.\"",
        ),
        how_to_get=(
            "A cast net, up to 14 ft across per TPWD. Cast nets are legal for nongame fish "
            "and other aquatic life, not game fish.",
            "Look around marinas and dock lights early in the morning.",
            "Keep them alive in an aerated bait tank.",
        ),
        bait_for=(
            "Striped bass and hybrid striped bass, live",
            "Catfish, whole or cut",
        ),
        tips=(
            "To fish a whole threadfin for catfish, hook it through the top of the head, turn "
            "the hook, and hook it again near the tail.",
        ),
        legal_notes=BAIT_RULES,
        source_ids=(
            "tpwd-tfs",
            "al-tfs",
            "tpwd-regs-devices",
            "tpwd-regs-general",
            "tpwd-tawakoni",
            "catfishedge-shad",
            "tacklevillage-shad",
        ),
    ),
)

# --------------------------------------------------------------------------
# Habitat, habits, why the baits work, and eating (docs/adr/0024)
# --------------------------------------------------------------------------
# Added to the twelve original guides after the fact, so they're kept here
# rather than spliced into each literal above. Mostly from TPWD's own species
# pages; every source named in `sources` was opened and read, and is added to
# that guide's source list so the page shows it.

_DETAILS: dict[str, dict[str, tuple[str, ...]]] = {
    "largemouth-bass": dict(
        habitat=(
            "Seeks cover: logs, rock ledges, vegetation and man-made structures.",
            "Prefers clear, quiet water but tolerates a wide range of habitats.",
            "Native to many Texas rivers and lakes. The Florida largemouth, a subspecies, has been "
            "stocked into many Texas lakes.",
        ),
        habits=(
            "Young bass school; adults are usually solitary. Several adults may share a small area "
            "without interacting.",
            "An ambush hunter: it hides among plants, roots or limbs and strikes prey that comes past.",
            "Becomes a predator at about 2 in long; larger bass eat smaller bass.",
            "The male builds the nest in 2–8 ft of water, on any bottom but soft mud, and guards the "
            "eggs. The fry hatch in 5–10 days and stay in a group near the nest under his watch.",
            "Grows to 4–6 in in its first year, 8–12 in by two and about 16 in by three. Average "
            "lifespan is 16 years.",
        ),
        why_these_baits=(
            "Adults eat almost nothing but fish and crayfish, so the baits that work look like one: "
            "live shiners, soft-plastic crayfish, crankbaits and swimbaits.",
            "It ambushes from cover, so a bait has to pass close to the log, weed edge or dock it's "
            "hiding in.",
            "Lures work best when they resemble fish, crayfish, worms, insects or frogs (Missouri "
            "Dept. of Conservation).",
        ),
        eating=(
            "Fillet it: cut behind the gill cover down to the backbone, run the knife along the "
            "backbone to the tail, then skin the fillet and cut out the ribs.",
        ),
        sources=("mdc-bait-lures", "ks-cleaning"),
    ),
    "spotted-bass": dict(
        habitat=(
            "Likes more current than largemouth bass, and tolerates warmer, murkier, slower water "
            "than smallmouth bass.",
            "Native to East Texas from the Guadalupe River to the Red River, but not the Edwards "
            "Plateau.",
        ),
        habits=(
            "Diet changes with size: zooplankton when young, then insects, then fish and crayfish.",
            "Spawns over rock or gravel at 57–74°F. Females lay 1,150 to 47,000 eggs, and the male "
            "guards them, and the young for up to four weeks after they hatch.",
            "Much smaller than a largemouth: the largest known in Texas is just over 5.5 lb. Still "
            "an excellent fighter for its size.",
        ),
        why_these_baits=(
            "Adults eat fish and crayfish, which is why small soft plastics in natural colors "
            "(green pumpkin, watermelon) dragged along the bottom work.",
        ),
        sources=(),
    ),
    "white-bass": dict(
        habitat=(
            "Native in Texas only to the Red River drainage.",
            "Spawns in running water over gravel or rock.",
        ),
        habits=(
            "Travels in schools and feeds near the surface.",
            "Males run upstream to the spawning areas as much as a month before the females.",
            "Builds no nest: several males gather around a female near the surface or in midwater. "
            "The eggs sink, stick to rocks and hatch in 2–3 days.",
            "Grows fast, 8–9 in in its first year, and rarely lives past four.",
        ),
        why_these_baits=(
            "Gizzard and threadfin shad are its preferred prey, so the best lures are shad-shaped "
            "and shiny: slabs, spoons, inline spinners and white grubs.",
            "Schools feed at the surface, so once a school is found, spoons or spinners worked near "
            "the top catch fish one after another.",
            "Bottom fishing with live bait at night also works.",
        ),
        eating=("Superb table fare (TPWD).",),
        sources=(),
    ),
    "striped-bass": dict(
        habitat=(
            "A saltwater fish by origin, stocked into many Texas rivers and reservoirs, where it "
            "does well without salt water.",
            "Needs cool, well-oxygenated water and can't tolerate poor water quality. From fall "
            "through spring it spreads through the reservoir; in summer it gathers in cool, deep "
            "water near the thermocline.",
        ),
        habits=(
            "Lives in open water in schools that keep moving.",
            "Runs up flowing tributaries to spawn in spring. Its spawning needs are specific, so few "
            "reservoirs have self-sustaining populations; most are kept up by stocking.",
            "Grows fast, often 24 in by its fourth year, and is believed to live up to 30 years.",
        ),
        why_these_baits=(
            "Gizzard and threadfin shad are its main prey, and it's big enough to eat gizzard shad "
            "too large for most other fish. That's why live shad and big shad-colored slabs, "
            "swimbaits and pencil poppers are the standard baits.",
        ),
        eating=("Prized for its flavorful flesh (Missouri Dept. of Conservation).",),
        sources=("mdc-striper-fg",),
    ),
    "hybrid-striped-bass": dict(
        habitat=(
            "A hatchery-made cross of striped bass and white bass, stocked into reservoirs. It is "
            "sterile, so every population depends on stocking.",
            "An open-water fish that doesn't stay near weeds, stumps or other structure.",
            "Gathers by the fastest current: below dams while water is being released, at springs, "
            "and at creek mouths after heavy rain.",
        ),
        habits=(
            "Roams in schools like \"mini wolf packs\", slashing into balls of baitfish. Diving birds "
            "join in.",
            "Early in the day it is in shallow water near the bank; later it moves deeper with the "
            "baitfish.",
            "In spring it runs up tributaries with the white bass, though it can't reproduce.",
            "Typically 7–10 lb, seldom 20.",
        ),
        why_these_baits=(
            "Gizzard and threadfin shad are a major food, so shad-like lures and live shad work. "
            "Once a school is feeding it bites almost anything.",
            "It hits hard and can break light line or wreck lures, so use heavier tackle than for "
            "white bass.",
        ),
        eating=("Considered excellent eating (Missouri Dept. of Conservation).",),
        sources=("mdc-hybrid-fg",),
    ),
    "channel-catfish": dict(
        habitat=(
            "Most abundant in large streams with low or moderate current; found throughout Texas.",
        ),
        habits=(
            "Spawns in late spring or early summer once the water reaches 75°F. The male picks a "
            "dark, hidden nest site, such as a hole in a drift pile, a log, an undercut bank or rocks, "
            "and guards the eggs and fry.",
            "Eggs hatch in about a week; the fry stay in the nest about another week.",
            "Matures in 3–6 years in Texas. Fish over 36 lb have been landed in Texas waters.",
            "Like other catfish, more active in low light and overnight, but catchable any time.",
        ),
        why_these_baits=(
            "A catfish finds food mostly by taste and touch, not sight, so strong-smelling baits work: "
            "stink bait, punch bait, chicken liver, cut bait.",
            "Channel catfish are much more likely than flathead or blue catfish to take baits that "
            "aren't live or natural, which is why prepared baits and hot dogs catch them.",
            "Adults eat almost anything (insects, snails, crayfish, fish and some plants), so worms "
            "and shrimp work too.",
        ),
        eating=(
            "Prized for its flavor. Catfish are skinned rather than scaled: see the catfish "
            "cleaning steps in the handbook.",
        ),
        sources=("odwc-catfish", "utah-clean-cat"),
    ),
    "blue-catfish": dict(
        habitat=(
            "Mainly large rivers: main channels, tributaries and the reservoirs built on major river "
            "systems. In Texas, absent from the northwest, including the Panhandle.",
        ),
        habits=(
            "Moves upstream in summer to find cooler water and downstream in winter for warmer water.",
            "Starts eating fish at about 4 in long. Typically 20–40 lb; Texas's largest freshwater "
            "sport fish. The Texas rod-and-reel record is 121.5 lb.",
            "Early spring, from March through May, is often best for big blues, and some of the "
            "largest are caught in midwinter.",
        ),
        why_these_baits=(
            "Shad is its preferred food, so fresh cut shad (or skipjack herring) on a circle hook is "
            "the standard bait.",
        ),
        eating=("An excellent food fish (TPWD). Skin it like other catfish.",),
        sources=("odwc-catfish",),
    ),
    "white-crappie": dict(
        habitat=(
            "Native to the eastern two-thirds of Texas and now statewide, except the upper Rio "
            "Grande and Pecos drainages.",
            "Gathers around submerged trees, boat docks and other structure.",
        ),
        habits=(
            "Adults form schools, sometimes large ones; young fingerlings school in the middle of "
            "lakes.",
            "Builds nests in large beds, spawning at 65–70°F (as low as 56°F has been seen). Fry "
            "hatch in 3–5 days.",
            "Grows to 3–5 in in its first year and 7–8 in in its second. Fish over 4.5 lb have been "
            "landed in Texas.",
            "Can overpopulate and stay small (\"stunt\") in small lakes.",
        ),
        why_these_baits=(
            "Adults eat small fish and insects, so a small live minnow is the preferred bait; small "
            "jigs imitate the same minnows.",
        ),
        eating=(
            "Scale it and cook it whole, or fillet it with the panfish method in the handbook.",
        ),
        sources=("ks-cleaning",),
    ),
    "black-crappie": dict(
        habitat=(
            "Most abundant in the clear, acidic waters of East Texas. Native to central Texas, "
            "except the Edwards Plateau.",
        ),
        habits=(
            "Builds nests and spawns in spring, generally at about 60°F.",
            "Stockier than a white crappie, which grows faster in length. Fish over 3.5 lb have "
            "been caught in Texas public waters.",
        ),
        why_these_baits=(
            "Eats fewer fish and more insects and crustaceans than white crappie, so small jigs and "
            "insect-sized baits work alongside minnows.",
        ),
        eating=(
            "Scale it and cook it whole, or fillet it with the panfish method in the handbook.",
        ),
        sources=("ks-cleaning",),
    ),
    "bluegill": dict(
        identification=(
            "A dark spot at the base (rear) of the soft dorsal fin, and vertical bars on the sides.",
            "A small mouth.",
            "A flexible black ear flap, and deep blue on the underside of the gill cover.",
            "Usually 10 spines in the spiny dorsal fin and 3 in the anal fin.",
            "Dark olive back; sides lavender, brown, copper or orange; belly reddish-orange or "
            "yellow. Breeding males are brighter.",
        ),
        habitat=(
            "Found throughout Texas: three subspecies live here.",
            "Vegetation and sunken trees in shallow backwaters of rivers, lakes and ponds.",
        ),
        habits=(
            "Builds nests 1–2 ft deep, preferring gravel; 50 or more nests may cluster in one "
            "small spawning bed. The males guard them.",
            "Its long spawning season lets it overpopulate where few predators or anglers thin it out.",
            "Texas public waters have produced bluegill approaching 2 lb.",
        ),
        why_these_baits=(
            "Young bluegill eat plankton; adults eat aquatic insects and larvae, so small baits win: "
            "a piece of worm, a cricket, a mealworm, a tiny jig.",
            "A lively cricket is hard for a hungry bluegill to resist, especially big bluegill in "
            "summer and late fall.",
            "Its small mouth is why the hook and bait must be small: TPWD suggests hooks size 6–14 "
            "for sunfish.",
        ),
        eating=(
            "Scale it and cook it whole, or fillet it with the panfish method in the handbook.",
        ),
        sources=("tpwd-sunfish-id", "tmf-live-bait", "ks-cleaning"),
    ),
    "gizzard-shad": dict(
        habitat=(
            "Most abundant in large rivers and reservoirs; found in all major Texas streams and "
            "reservoirs. Avoids steep, fast streams.",
        ),
        habits=(
            "Usually in large schools. Called \"skipjack\" for leaping out of the water or skipping "
            "along the surface on its side.",
            "Spawns in late spring in shallow, protected water; the sticky eggs hatch in about "
            "4 days.",
            "Commonly 9–14 in; some exceed 20 in.",
        ),
        why_these_baits=(
            "It filters food from the water with long, close-set gill rakers, which is why it "
            "almost never bites a hook and is caught with a cast net instead.",
            "It's food for most game fish, which is why it makes good bait, often as cut bait.",
        ),
        eating=("Generally considered worthless as food (TPWD).",),
        sources=(),
    ),
    "threadfin-shad": dict(
        habitat=(
            "Usually in the top 5 ft of water, more often where there's a noticeable current. "
            "Common in East Texas streams and stocked statewide as forage in many reservoirs.",
        ),
        habits=(
            "Spawns from spring, at about 70°F, into summer.",
            "Very sensitive to cold: die-offs happen below 45°F.",
        ),
        why_these_baits=(
            "Rarely bites a hook, so it's netted. It's what stripers, hybrids and white bass are "
            "chasing, which makes it top live bait for them.",
        ),
        sources=(),
    ),
}


def _with_details(guide: SpeciesGuide) -> SpeciesGuide:
    extra = _DETAILS.get(guide.slug)
    if not extra:
        return guide
    sources = tuple(extra.get("sources", ()))
    fields = {k: v for k, v in extra.items() if k != "sources"}
    if "identification" in fields and guide.identification:
        raise ValueError(f"{guide.slug}: identification is already set in the guide")
    return replace(
        guide,
        **fields,
        source_ids=guide.source_ids + tuple(s for s in sources if s not in guide.source_ids),
    )


# --------------------------------------------------------------------------
# Six more fish a Texas beginner is likely to catch (docs/adr/0024)
# --------------------------------------------------------------------------

_NEW_GUIDES: tuple[SpeciesGuide, ...] = (
    SpeciesGuide(
        common_name="Flathead Catfish",
        scientific_name="Pylodictis olivaris",
        role="sport",
        difficulty="advanced",
        summary=(
            "Texas's second-largest sport fish after the blue catfish, and the one catfish that "
            "wants live fish. Fish a live sunfish next to heavy wood cover, at dusk or after dark."
        ),
        diet=(
            "Live fish. Young fish eat worms, insects and crayfish; from about 10 in long the diet "
            "is entirely fish, including shad, carp, sunfish, bass and other catfish."
        ),
        diet_type="carnivore",
        identification=(
            "A broad, flat head with the lower jaw sticking out past the upper jaw. Channel and "
            "blue catfish have the upper jaw longer.",
            "Tail only slightly notched, almost square, not deeply forked like a channel or blue "
            "catfish's.",
            "Pale yellow to light brown, heavily mottled with black or brown; cream or pale yellow "
            "belly. Young fish can be nearly black.",
            "Other names: yellow cat, Opelousas cat, mud cat, shovelhead.",
        ),
        habitat=(
            "Deep pools of streams, rivers, canals, lakes and reservoirs with murky water and slow "
            "current.",
            "Stays near heavy cover: log jams, brush piles, hollow logs, undercut banks, bluffs and "
            "large rocks.",
        ),
        habits=(
            "Usually alone. Adults move into shallow water at night to feed.",
            "Spawns from late May through August at 75–80°F. The male picks a hollow log, a cave or "
            "a hole under a bank, and guards the eggs aggressively.",
            "Typically lives 12–14 years. Can exceed 100 lb; 50 lb fish aren't unusual in Texas "
            "where mature populations exist.",
        ),
        where_and_when=(
            "Woody cover in coves and backwaters, deep holes near cover, and below reservoir dams.",
            "Most active at low light and overnight; larger fish feed more at night. Work cover "
            "near sunrise and sunset.",
            "It feeds little while spawning but heavily before and after.",
        ),
        live_baits=(
            "Live sunfish, such as bluegill (the go-to bait)",
            "Live shad",
            "Large live minnows, goldfish or bullheads",
        ),
        why_these_baits=(
            "Unlike most catfish, it eats only live fish, so it consistently takes only live bait.",
            "Bigger bait tends to catch bigger fish, because small fish can't take it.",
        ),
        setups=(
            TackleSetup(
                name="Live sunfish in cover",
                use_when="Casting a live bait into woody cover and waiting for a take.",
                method="bait",
                rod="Medium to extra-heavy rod",
                reel="Spinning, spincasting or baitcasting reel",
                line="10–80 lb test, with a 30–80 lb leader",
                terminal=(
                    "A sturdy 6/0–10/0 circle hook through the lips, or between the dorsal fin and "
                    "the tail, of a live bluegill. A ½–1 oz weight on the main line above a barrel "
                    "swivel. Don't sweep-set a circle hook: reel down on the fish."
                ),
                source_ids=("odwc-catfish",),
            ),
            TackleSetup(
                name="Big-river tight line",
                use_when="Deep pools, cut banks and log jams in a large river.",
                method="bait",
                rod="7–10 ft medium-heavy or heavy rod",
                reel="Heavy-duty baitcasting or spinning reel",
                line="30–50 lb monofilament, with about 18 in of 50 lb leader below the swivel",
                terminal=(
                    "A 6/0–8/0 circle hook with a live sunfish or large minnow hooked through the "
                    "back below the dorsal fin, or through both lips. A 3–8 oz slip sinker above a "
                    "two-way swivel, just heavy enough to hold the bottom."
                ),
                source_ids=("mdc-bigcat",),
            ),
        ),
        tips=(
            "Keep live bait cool: an insulated cooler with a frozen jug of ice.",
            "No bite in 30 minutes? Move. Approach cover quietly.",
            "Below dams, the current can be dangerous.",
        ),
        eating=("The belly meat is especially good eating (Oklahoma Dept. of Wildlife Conservation).",),
        source_ids=("tpwd-flc", "odwc-catfish", "mdc-bigcat", "mdc-flathead", "tpwd-cat-id"),
    ),
    SpeciesGuide(
        common_name="Guadalupe Bass",
        scientific_name="Micropterus treculii",
        role="sport",
        difficulty="intermediate",
        summary=(
            "The official state fish of Texas, found only in Texas. A small, hard-fighting bass of "
            "Hill Country streams; cast to every rock, root and eddy along the current."
        ),
        diet=(
            "Fish, crayfish and insect larvae. The very young and older adults eat more invertebrates "
            "than largemouth bass do; in hot weather the biggest feed on grasshoppers."
        ),
        diet_type="carnivore",
        identification=(
            "Generally green, with a black, diamond-shaped pattern along the sides and rows of spots "
            "forming stripes on the belly.",
            "With the mouth closed, the jaw doesn't reach past the eye, as it does on a largemouth.",
            "No vertical bars, unlike a smallmouth bass; the markings reach lower on the body than a "
            "spotted bass's.",
            "A red-rimmed eye.",
        ),
        habitat=(
            "Flowing water: streams of the northern and eastern Edwards Plateau, including the "
            "headwaters of the San Antonio and Guadalupe rivers, the Colorado above Austin, and parts "
            "of the Brazos drainage. Largemouth bass, by contrast, live in quiet water.",
            "In lakes without current, such as Lake Travis, it sticks to rock: rocky banks, bluff "
            "walls, ledges and points.",
        ),
        habits=(
            "Matures at one year old. Spawns from as early as March through May and June, on gravel "
            "nests in shallow water, often in faster flow than largemouth use.",
            "Doesn't grow large: fish over 3.5 lb have been landed, and most are under a foot long.",
            "Its biggest threat is interbreeding with introduced smallmouth bass.",
            "Ambushes from shoreline structure. On hot, sunny days it goes deeper.",
        ),
        where_and_when=(
            "Swirling pools below current, calm backwaters off the main flow, and every run, riffle, "
            "rock, root wad and fallen tree along a shady bank.",
            "The bite peaks from late April into May. For surface fishing, March–June and "
            "September–October are best.",
            "Hill Country streams are fishable all year: their main springs run about 70°F.",
        ),
        lures=(
            "Ned rig (a short soft-plastic stick on a small jighead) bounced along the bottom",
            "Small jigs and soft-plastic crawfish",
            "Drop-shot finesse worms",
            "Small paddle-tail swimbaits that look like threadfin shad",
            "Crawfish-colored crankbaits bumped along rocky banks",
            "Poppers and other topwaters near downed trees and lily pads",
        ),
        why_these_baits=(
            "It feeds heavily on crawfish, so crawfish-colored plastics and crankbaits are the "
            "starting point.",
            "It's aggressive and needs no delicate presentation; a fast, \"mean\" lure draws "
            "explosive strikes.",
            "Grasshoppers and other insects falling from the bank are a summer staple, which is why "
            "hopper-style flies and poppers work.",
        ),
        setups=(
            TackleSetup(
                name="Finesse drop shot or Ned rig",
                use_when="Rocky ledges and bluff walls, or the bottom of a river pool.",
                method="lure",
                rod="Spinning rod",
                reel="Spinning reel",
                line="Light line for finesse baits (no pound test given by the sources)",
                terminal=(
                    "Drop shot: a 1/0 hook with a green pumpkin straight-tail worm above a ¼ oz "
                    "weight, fished slowly. Or a Ned rig: a short stickbait on a small jighead."
                ),
                source_ids=("torwicks-gdb", "texasmonthly-gdb"),
            ),
            TackleSetup(
                name="Fly rod on a Hill Country stream",
                use_when="Wading or paddling a river, casting to the bank.",
                method="lure",
                rod="7–8½ ft, 5- or 6-weight, medium-fast",
                reel="Fly reel with a floating bass-taper line (or a short 5 ft sinking tip)",
                line="1X–3X leader with fluorocarbon tippet, 7–9 ft",
                terminal=(
                    "Snag-resistant flies, sizes 4–10, worked slowly: Clousers, Woolly Buggers, "
                    "crayfish patterns, poppers, and grasshopper or cricket patterns in sizes 4–8."
                ),
                source_ids=("flyfisherman-gdb",),
            ),
        ),
        tips=(
            "Make short, accurate casts tight to the bank: that's where it waits.",
            "Strikes are explosive. Don't hesitate to set the hook.",
            "Many anglers practice catch and release with Guadalupe bass.",
        ),
        source_ids=("tpwd-gdb", "tamu-gdb", "flyfisherman-gdb", "texasmonthly-gdb", "torwicks-gdb", "tpwd-bass-id"),
    ),
    SpeciesGuide(
        common_name="Redear Sunfish",
        scientific_name="Lepomis microlophus",
        role="sport",
        difficulty="beginner",
        summary=(
            "The \"shellcracker\": a big sunfish that eats snails on the bottom. Fish a worm on or "
            "near the bottom, a little deeper than the bluegill beds."
        ),
        diet=(
            "Snails are a major food, which is where the name shellcracker comes from; also insect "
            "larvae and small crustaceans."
        ),
        diet_type="carnivore",
        identification=(
            "A red edge on the ear (gill) flap of males, orange on females; the flap is never long.",
            "Dark olive back, yellow to green sides, nearly white belly; a small mouth.",
            "Long, pointed pectoral fins.",
            "Other names: shellcracker, Georgia bream, cherry gill, sun perch.",
        ),
        habitat=(
            "Near the bottom in warm, clear, quiet water with little current and plenty of aquatic "
            "vegetation.",
            "Native to the eastern two-thirds of Texas and widely stocked elsewhere.",
        ),
        habits=(
            "Spawns in late spring and early summer, in deeper water than most sunfish, in beds of "
            "saucer-shaped nests set so close they nearly touch.",
            "Rarely rises to the surface to feed.",
            "Grows to about 12 in and 2 lb; few live past six summers.",
        ),
        where_and_when=(
            "Look past the bluegill beds along a bank, in slightly deeper water. Catching bluegill "
            "instead? Move a little deeper.",
            "Backs of bays with gravel bottoms and vegetation, and around logs and brush.",
            "Spawning starts when the water reaches the 70s°F; that's when they're concentrated and "
            "easiest to catch. Once you catch one, keep fishing the spot.",
        ),
        live_baits=("Redworms or other earthworms", "Wax worms", "Mealworms", "Crickets"),
        lures=("Small black or brown jigs that look like a snail or insect", "Soft-plastic \"bluegill bugs\" tipped with a wax worm"),
        why_these_baits=(
            "It feeds on the bottom on snails and larvae, so baits fished on or near the bottom "
            "work, and topwater baits rarely do.",
        ),
        setups=(
            TackleSetup(
                name="Worm under a bobber, near the bottom",
                use_when="Just beyond the bluegill beds in spring and early summer.",
                method="bait",
                rod="Ultralight spinning rod",
                reel="Ultralight spinning reel",
                line="4–6 lb monofilament",
                terminal="A redworm, wax worm or cricket set under a bobber so it rides close to or on the bottom.",
                source_ids=("kyfw-redear",),
            ),
            TackleSetup(
                name="Drop shot along the bottom",
                use_when="Searching deeper water slowly until you find the fish.",
                method="either",
                rod="Ultralight spinning rod",
                reel="Ultralight spinning reel",
                line="4–6 lb monofilament",
                terminal="A hook tied a few inches above a 3/16 oz weight, baited with a worm or a small jig, moved slowly along the bottom.",
                source_ids=("kyfw-redear",),
            ),
        ),
        eating=("Scale it and cook it whole, or fillet it with the panfish method in the handbook.",),
        source_ids=("tpwd-rsf", "tamu-rsf", "kyfw-redear", "tpwd-sunfish-id", "ks-cleaning"),
    ),
    SpeciesGuide(
        common_name="Rainbow Trout",
        scientific_name="Oncorhynchus mykiss",
        role="sport",
        difficulty="beginner",
        summary=(
            "A cold-water fish TPWD stocks into community lakes every winter. It bites almost as "
            "soon as it's stocked, on light tackle and small baits."
        ),
        diet="Insects, crustaceans, mollusks and fish: a carnivore, but not only a fish-eater.",
        diet_type="carnivore",
        identification=(
            "A salmon-like body with a slightly forked tail covered in dark spots.",
            "Dark olive back, silvery white below, heavily speckled, with a pink to red stripe along "
            "each side.",
        ),
        habitat=(
            "Needs water below about 70°F. Texas summers are too warm for it to breed or, usually, "
            "survive, so most Texas trout are stocked for winter fishing.",
            "Exceptions: the Guadalupe River below Canyon Lake, which often stays cool enough "
            "year-round, and a small wild population in McKittrick Canyon in the Guadalupe "
            "Mountains.",
        ),
        habits=(
            "Stays active in winter, when bass and crappie slow down.",
            "Often nibbles rather than taking a bait in one bite.",
            "The Texas record is 8.24 lb, from the Canyon Reservoir tailrace.",
        ),
        where_and_when=(
            "TPWD stocks several hundred thousand into community fishing lakes each winter; for "
            "2025–26 it planned 335,048 fish from Nov. 26 to March 6, in Neighborhood Fishin' lakes "
            "and dozens of city and county park ponds.",
            "Check TPWD's trout stocking schedule before going: dates and places change.",
            "Arrive early on stocking day; trout bite almost immediately after they're released.",
            "In a Texas state park you can fish without a license from the bank, a dock or a pier.",
        ),
        live_baits=(
            "Dough baits such as PowerBait, molded to cover the hook",
            "Corn",
            "Small pieces of worm",
            "Salmon eggs",
        ),
        lures=(
            "Small inline spinners, 1/16–1/8 oz (olive, brown, black or white)",
            "Small spoons in gold or silver",
            "Small marabou jigs",
            "Flies: small nymphs and bead-head Woolly Buggers",
        ),
        why_these_baits=(
            "Its diet is insects and crustaceans, so small lures and flies that look like them work.",
            "Scented dough baits sit on the bottom where a cruising trout finds them; it often "
            "nibbles, so wait for steady pressure before setting the hook.",
        ),
        setups=(
            TackleSetup(
                name="Dough bait on the bottom",
                use_when="Stocked ponds and lakes; still or slow water.",
                method="bait",
                rod="6–7 ft medium-light rod",
                reel="Spinning reel",
                line="6–8 lb monofilament",
                terminal=(
                    "A size 6, 8 or 10 snelled bait-holder hook covered with PowerBait, a snap "
                    "swivel, and a ¼ oz sinker in still water (½ oz in current)."
                ),
                source_ids=("odwc-trout",),
            ),
            TackleSetup(
                name="Small spinner",
                use_when="Casting and slowly retrieving along the bank.",
                method="lure",
                rod="6–7 ft medium-light rod",
                reel="Spinning reel",
                line="6–8 lb monofilament",
                terminal="A 1/16–1/8 oz inline spinner or small spoon, retrieved slowly.",
                source_ids=("odwc-trout",),
            ),
            TackleSetup(
                name="Ultralight with a light leader",
                use_when="Clear water, or wary fish.",
                method="either",
                rod="6–6½ ft rod",
                reel="Ultralight spinning reel with 4 lb line",
                line="4 lb main line; a 2 ft leader of 2 lb line on a snap swivel",
                terminal=(
                    "Treble hooks size 16–18 for cheese and dough baits, or single hooks size 10–16 "
                    "for salmon eggs; a BB-size split shot 12–24 in above the hook."
                ),
                source_ids=("mdc-trout",),
            ),
        ),
        tips=(
            "Set the hook with a medium pull, not a hard jerk.",
            "Land trout with a net: they can break the line when lifted out of the water.",
        ),
        eating=("Bring ice and get the fish on it soon after catching (TPWD).",),
        source_ids=("tpwd-rbt", "tpwd-trout-2025", "odwc-trout", "mdc-trout", "tpwmag-trout-2005", "tamu-baits"),
    ),
    SpeciesGuide(
        common_name="Freshwater Drum",
        scientific_name="Aplodinotus grunniens",
        role="sport",
        difficulty="beginner",
        summary=(
            "A silvery bottom feeder that makes a grunting sound, common in rivers and big lakes "
            "statewide. Worms on the bottom catch more drum than anything else."
        ),
        diet=(
            "Fish, crayfish and immature insects. It roots through the bottom and moves rocks to "
            "find prey, and heavy throat teeth let it crush some mollusks."
        ),
        diet_type="carnivore",
        identification=(
            "Deep-bodied and silvery, with a long dorsal fin split into two sections.",
            "No spot on the tail, unlike its saltwater relative, the red drum.",
            "Grunts: a sound you can hear or feel when you hold one.",
            "Other names: gaspergou, gou, drum fish.",
        ),
        habitat=(
            "Found throughout Texas except the Panhandle, in a wide range of waters. Spends most of "
            "its time on or near the bottom.",
            "Often in deeper water with current: current breaks, eddies, drop-offs, below dams and "
            "around structure.",
        ),
        habits=(
            "Spawns in open water in April or May in Texas; the eggs float until they hatch.",
            "Travels in schools: after one, keep fishing that area.",
            "Usually 1–4 lb; the Texas rod-and-reel record is over 30 lb.",
        ),
        where_and_when=(
            "Rocky rivers and large reservoirs, especially below dams. Good for bank anglers.",
        ),
        live_baits=("Worms and nightcrawlers", "Crawdad tails", "Pieces of cooked shrimp", "Minnows"),
        lures=("Small grubs and jigs fished near the bottom", "Spoons", "Small swimbaits"),
        why_these_baits=(
            "It feeds on the bottom on crayfish, insects and small fish, and isn't picky, so natural "
            "baits on the bottom work best; drum \"aggressively inhale bait.\"",
            "It has a small mouth, so use a small hook.",
        ),
        setups=(
            TackleSetup(
                name="Sliding sinker on the bottom",
                use_when="Current breaks, eddies and drop-offs; from the bank or anchored above a spot.",
                method="bait",
                rod="Any rod; a basic spincasting outfit handles most drum",
                reel="Spincasting, spinning or baitcasting reel",
                line="15–20 lb monofilament, or better, 20–30 lb braid (its thin diameter drags less in current)",
                terminal=(
                    "A ½ oz or heavier egg sinker sliding on the main line above a barrel swivel, "
                    "then about 12 in of mono leader and a size 2 or 4 bait-holder hook, or a light "
                    "wire size 1 circle hook (just tighten the line, don't jerk)."
                ),
                source_ids=("agfc-drum",),
            ),
            TackleSetup(
                name="Jig near the bottom",
                use_when="Covering water below dams and along rocky drops.",
                method="lure",
                rod="Any rod; a basic spincasting outfit handles most drum",
                reel="Spincasting, spinning or baitcasting reel",
                line="15–20 lb monofilament or 20–30 lb braid",
                terminal="A small grub, swimbait or jig, or a spoon, worked slowly near the bottom.",
                source_ids=("agfc-drum", "tmf-drum"),
            ),
        ),
        eating=(
            "Good eating when caught from cool water. Ice it as soon as possible, fillet it like a "
            "bass or crappie (it has no small bones in the fillet), and trim the dark red meat just "
            "under the skin.",
            "Fried in a seasoned cornmeal coating at 350°F for about six minutes, or cubed and "
            "boiled 5–7 minutes in crab-boil seasoning (\"poor man's lobster\").",
        ),
        source_ids=("tpwd-fwd", "agfc-drum", "tmf-drum"),
    ),
    SpeciesGuide(
        common_name="Common Carp",
        scientific_name="Cyprinus carpio",
        role="sport",
        difficulty="intermediate",
        summary=(
            "A big, hard-fighting fish found in nearly every Texas water. It rarely takes a lure: "
            "fish corn or dough on the bottom over a spot you've baited."
        ),
        diet="An omnivore: it eats a broad mix of plants and animals.",
        diet_type="omnivore",
        identification=(
            "Heavy-bodied, with barbels (whiskers) on both sides of the upper jaw.",
            "Brassy green or yellow to golden brown or silvery, with a yellowish-white belly.",
            "A dorsal fin of 17–21 rays, and a heavy toothed spine at the front of the dorsal and "
            "anal fins.",
            "Other names: German carp, European carp.",
        ),
        habitat=(
            "Ponds, lakes, streams and rivers; tolerates a wide range of conditions. Not native: "
            "it comes from Europe and Asia and is now everywhere in Texas.",
        ),
        habits=(
            "Grows fast and lives long, over 47 years. Commonly 12–25 in and up to 8–10 lb; the "
            "Texas rod-and-reel record is 43.13 lb.",
            "Can spawn several times a season, from March to September.",
            "Fights hard and makes long runs.",
        ),
        where_and_when=(
            "Almost any pond, lake or river. Carp find a baited (chummed) area fairly quickly.",
        ),
        live_baits=(
            "Canned or frozen sweet corn",
            "Boiled field corn",
            "Dough balls and oatmeal-based pack baits",
            "Bread",
        ),
        why_these_baits=(
            "It's an omnivore and usually won't strike a lure, so baits like corn and dough fished "
            "on the bottom work best.",
            "Scattering a few handfuls of corn draws carp to your spot and keeps them there.",
        ),
        setups=(
            TackleSetup(
                name="Hair rig over chum",
                use_when="Bottom fishing a spot baited with corn.",
                method="bait",
                rod="Medium action, at least 6 ft (8½–12 ft is better for big fish)",
                reel="Spinning or spincast reel with a good drag and 100+ yd of line",
                line="10–15 lb mono or braid; a slightly lighter mono or fluorocarbon leader",
                terminal=(
                    "A size 4–8 hook with a short \"hair\" loop off the bend; the bait is threaded on "
                    "the hair so the hook point stays bare. Egg sinker and barrel swivel above the "
                    "leader."
                ),
                source_ids=("nydec-carp",),
            ),
            TackleSetup(
                name="Simple bottom rig",
                use_when="Your first carp, with standard tackle.",
                method="bait",
                rod="Medium action, at least 6 ft",
                reel="Spinning or spincast reel with a good drag",
                line="10–15 lb mono",
                terminal="An egg sinker, a barrel swivel, a short leader and a size 4–8 bait hook covered with corn or dough.",
                source_ids=("nydec-carp",),
            ),
        ),
        tips=(
            "Chum with a few handfuls of corn, and add more every half hour to an hour.",
            "Leave the bail open (or the button pushed) with the rod in a holder, so a carp can run "
            "with the bait.",
            "Set the drag properly and take your time: carp make long runs. Land it with a net.",
            "A hair rig also makes release easier, because the fish isn't hooked deeply.",
        ),
        eating=("Flavor depends on the water it came from (TPWD).",),
        source_ids=("tpwd-crp", "nydec-carp", "mdc-bait-lures"),
    ),
)

GUIDES: tuple[SpeciesGuide, ...] = tuple(_with_details(g) for g in _BASE_GUIDES) + _NEW_GUIDES

_BY_SLUG = {g.slug: g for g in GUIDES}
_BY_NAME = {g.common_name.lower(): g for g in GUIDES}


def get_guide(slug_or_name: str) -> SpeciesGuide | None:
    key = slug_or_name.strip()
    return _BY_SLUG.get(slugify(key)) or _BY_NAME.get(key.lower())


def sources_for(ids: tuple[str, ...]) -> list[Source]:
    return [SOURCES[i] for i in ids]
