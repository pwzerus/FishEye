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
from dataclasses import dataclass, field

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

GUIDES: tuple[SpeciesGuide, ...] = (
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

_BY_SLUG = {g.slug: g for g in GUIDES}
_BY_NAME = {g.common_name.lower(): g for g in GUIDES}


def get_guide(slug_or_name: str) -> SpeciesGuide | None:
    key = slug_or_name.strip()
    return _BY_SLUG.get(slugify(key)) or _BY_NAME.get(key.lower())


def sources_for(ids: tuple[str, ...]) -> list[Source]:
    return [SOURCES[i] for i in ids]
