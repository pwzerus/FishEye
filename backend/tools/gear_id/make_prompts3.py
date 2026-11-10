"""prompts3.json: prompts2 plus a description of what each item looks like.

    python -I make_prompts3.py <work dir>

Descriptions say what tells an item from its neighbours (where the reel
sits, what the lure's lip or blade looks like), the way a shop assistant
would. Compared with prompts2 on the val photos only.
"""
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
LOOKS = {
    "combo-spincast": ["a spincast reel with a closed cone-shaped cover on top of the rod and a thumb push button",
                       "a beginner spincast rod and reel combo with a closed-face reel"],
    "rod-spinning": ["a spinning rod with large line guides on the underside and a spinning reel hanging below the handle",
                     "a fishing rod with a cork or foam handle and a spinning reel underneath"],
    "reel-spinning": ["a spinning reel with an open fixed spool, a wire bail arm and a crank handle on the side",
                      "an open-face spinning reel hanging below a rod"],
    "rod-baitcasting": ["a baitcasting rod with small guides on top and a trigger grip under the reel seat",
                        "a casting rod with a baitcasting reel mounted on top"],
    "reel-baitcasting": ["a baitcasting reel, a low oval reel sitting on top of the rod with a revolving spool and a thumb bar",
                         "a round conventional reel with a revolving spool and a star drag"],
    "rod-fly": ["a fly reel, a narrow round reel with a wide spool of thick fly line",
                "a long thin fly rod with a single-action fly reel at the butt"],
    "rod-ice": ["a very short ice fishing rod about two feet long with a small reel",
                "a tiny ice fishing jigging rod next to a hole in the ice"],
    "pole-cane": ["a long bamboo cane pole with the line tied to its tip and no reel",
                  "a long telescopic fishing pole without a reel"],
    "line-mono": ["a spool of clear or green monofilament fishing line", "a coil of transparent nylon fishing line"],
    "line-braid": ["a spool of braided fishing line made of woven coloured fibres",
                   "bright green or yellow braided fishing line on a spool"],
    "hook-j": ["a single J-shaped fishing hook with an eye, a barb and a pointed tip", "a pack of small bait hooks"],
    "hook-circle": ["a circle hook whose point curves back toward the shank, making an almost round shape",
                    "circle hooks used for catfish and saltwater bait fishing"],
    "hook-treble": ["a treble hook with three hooks sharing one shank and one eye", "treble hooks with three barbed points"],
    "sinker-split-shot": ["small round lead split shot weights with a slit to pinch onto the line",
                          "tiny round fishing weights in a container"],
    "sinker-egg": ["egg-shaped lead sinkers with a hole through the middle", "bullet-shaped worm weights for fishing"],
    "sinker-bank": ["a pyramid-shaped or bank sinker with a wire loop on top", "a heavy teardrop-shaped bell sinker"],
    "bobber": ["a round red and white plastic fishing bobber with a spring clip", "a round fishing float sitting on the water"],
    "float-slip": ["a long slender fishing float, a slip bobber or pencil float",
                   "a thin stick-shaped float with a brightly coloured tip"],
    "swivel": ["small metal barrel swivels and snap swivels used to join fishing line", "a box of tiny brass fishing swivels"],
    "leader-wire": ["a steel wire leader with a swivel on one end and a snap on the other",
                    "a coated wire fishing leader for toothy fish"],
    "jig-head": ["a jig head, a hook with a round lead head moulded behind the eye, often painted",
                 "a lead-headed jig hook with a soft plastic body threaded on"],
    "lure-soft-worm": ["a long soft plastic worm lure with a ribbed body", "a rubbery plastic fishing worm in a bright colour"],
    "lure-grub": ["a soft plastic grub with a curly flapping tail", "a small curly-tailed soft plastic lure"],
    "lure-crankbait": ["a crankbait, a short fat hard plastic fish-shaped lure with a plastic diving lip and two treble hooks",
                       "a chubby wooden or plastic diving lure with a bill"],
    "lure-lipless": ["a lipless crankbait, a flat-sided vibrating hard lure without a lip and with the line tie on its back",
                     "a rattling lipless crankbait shaped like a shad"],
    "lure-jerkbait": ["a jerkbait, a long slim minnow-shaped hard lure with a small lip and several treble hooks",
                      "a long thin minnow plug lure"],
    "lure-spinnerbait": ["a spinnerbait, a safety-pin shaped wire lure with spinning metal blades on one arm and a skirted jig head on the other",
                         "a spinnerbait with a rubber skirt and willow leaf blades"],
    "lure-inline-spinner": ["an inline spinner, a straight wire lure with a rotating metal blade, a beaded body and a treble hook",
                            "a small spinner lure with a spinning blade in front of its body"],
    "lure-spoon": ["a spoon lure, a curved oval piece of shiny metal with a treble hook at one end",
                   "a metal fishing spoon with a painted or polished finish"],
    "lure-popper": ["a popper, a topwater lure with a cupped concave face that floats on the surface",
                    "a floating topwater plug lure"],
    "lure-swimbait": ["a soft plastic swimbait shaped like a small fish with a paddle tail", "a realistic fish-shaped swimbait lure"],
    "fly-dry": ["an artificial fly tied from feathers, fur and thread on a small hook", "a colourful fishing fly or streamer"],
    "bait-nightcrawler": ["live earthworms or nightcrawlers in dark soil", "a fishing worm on a hook"],
    "bait-minnow": ["live minnows, small silver baitfish swimming in a bucket", "a small minnow used as live bait"],
    "bait-crayfish": ["a crayfish with claws, a small freshwater lobster", "a live crawfish used for bait"],
    "bait-waxworm": ["pale white wax worms or mealworm larvae", "small grubs and maggots used as fishing bait"],
    "bait-cricket": ["a live cricket or grasshopper insect", "crickets used for bait"],
    "bait-leech": ["a dark slimy leech used as fishing bait", "live leeches in water"],
    "bait-liver": ["raw red chicken livers used as catfish bait", "a container of chicken liver bait"],
    "bait-shrimp": ["raw shrimp used as fishing bait", "a whole or peeled shrimp on a hook"],
    "bait-corn": ["yellow sweet corn kernels used as fishing bait", "canned corn on a hook"],
    "bait-cut": ["cut bait, chunks or strips of fresh fish such as shad", "a dead baitfish cut into pieces"],
    "bait-roe": ["orange salmon eggs or fish roe used as bait", "a spawn sac of fish eggs in mesh"],
    "tool-pliers": ["needle-nose fishing pliers with long thin jaws", "a pair of aluminium fishing pliers"],
    "tool-tackle-box": ["a tackle box with compartments full of lures and hooks", "a plastic tackle box or tackle tray"],
    "tool-net": ["a fishing landing net with a handle and a hoop", "a rubber mesh landing net"],
    "tool-stringer": ["a fish stringer, a cord or chain with clips to hold caught fish", "a cooler or ice chest"],
    "tool-bucket": ["a minnow bucket or bait bucket with an inner liner", "a bucket for keeping live bait"],
    "tool-lifejacket": ["a life jacket or personal flotation device", "an orange life vest"],
    "tool-measure": ["a fish measuring board with an inch ruler", "a fish lying on a measuring ruler"],
    "tool-sunglasses": ["a pair of polarised fishing sunglasses", "sunglasses with tinted lenses"],
    "tool-ice-auger": ["an ice auger, a long spiral drill for cutting holes in ice", "a hand or power ice auger on a frozen lake"],
}
p2 = json.loads((work / "prompts2.json").read_text("utf-8"))
assert set(LOOKS) == {k for k in p2 if not k.startswith(("x-", "f-"))}, set(LOOKS) ^ set(p2)
p3 = {k: (v + [f"a photo of {d}." for d in LOOKS[k]] * 3 if k in LOOKS else v) for k, v in p2.items()}
(work / "prompts3.json").write_text(json.dumps(p3, indent=1), encoding="utf-8")
print(len(p3), "classes,", sum(len(v) for v in p3.values()), "sentences (descriptions weighed as much as the names)")
