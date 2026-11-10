"""prompts2.json: several names per item, each in several sentences.

    python -I make_prompts2.py <work dir>

Compared with prompts.json on the val photos only (train_eval.py --text).
The x-* and f-* classes are copied from prompts.json unchanged.
"""
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
NAMES = {
    "combo-spincast": ["a spincast reel", "a closed-face spincast reel with a push button", "a spincast rod and reel combo"],
    "rod-spinning": ["a spinning rod", "a spinning rod and reel", "a fishing rod with a spinning reel under it"],
    "reel-spinning": ["a spinning reel", "an open-face spinning reel"],
    "rod-baitcasting": ["a baitcasting rod", "a casting rod with a baitcaster on top", "a bass fishing casting rod"],
    "reel-baitcasting": ["a baitcasting reel", "a baitcaster", "a low-profile baitcasting reel", "a round conventional fishing reel"],
    "rod-fly": ["a fly rod", "a fly fishing reel", "a fly rod and fly reel"],
    "rod-ice": ["an ice fishing rod", "a short ice fishing jigging rod"],
    "pole-cane": ["a cane pole", "a bamboo fishing pole", "a long fishing pole with no reel"],
    "line-mono": ["monofilament fishing line", "a spool of clear fishing line"],
    "line-braid": ["braided fishing line", "a spool of braided fishing line"],
    "hook-j": ["a fishing hook", "J fishing hooks", "bait hooks"],
    "hook-circle": ["a circle hook", "circle fishing hooks with the point turned in"],
    "hook-treble": ["a treble hook", "treble fishing hooks with three points"],
    "sinker-split-shot": ["split shot sinkers", "small round split shot weights"],
    "sinker-egg": ["egg sinkers", "bullet weights for fishing", "lead fishing sinkers"],
    "sinker-bank": ["a bank sinker", "a pyramid sinker", "a bell sinker"],
    "bobber": ["a fishing bobber", "a red and white round bobber", "a round fishing float"],
    "float-slip": ["a slip bobber", "a slender fishing float", "a pencil float"],
    "swivel": ["fishing swivels", "a barrel swivel", "snap swivels"],
    "leader-wire": ["a wire fishing leader", "a steel leader with a snap"],
    "jig-head": ["a jig head", "a lead jig head hook", "a jig with a soft plastic body"],
    "lure-soft-worm": ["a soft plastic worm lure", "a plastic worm for bass fishing"],
    "lure-grub": ["a curly tail grub lure", "a soft plastic grub"],
    "lure-crankbait": ["a crankbait", "a crankbait lure with a diving lip", "a hard plastic diving lure"],
    "lure-lipless": ["a lipless crankbait", "a rattle bait lure"],
    "lure-jerkbait": ["a jerkbait", "a minnow plug lure", "a long slim minnow lure"],
    "lure-spinnerbait": ["a spinnerbait", "a spinnerbait lure with a wire arm, blades and a skirt"],
    "lure-inline-spinner": ["an inline spinner lure", "a spinner lure with a rotating blade"],
    "lure-spoon": ["a spoon lure", "a metal spoon fishing lure"],
    "lure-popper": ["a popper lure", "a topwater fishing lure"],
    "lure-swimbait": ["a swimbait", "a soft plastic paddle tail swimbait"],
    "fly-dry": ["a fishing fly", "an artificial fly for fly fishing", "a streamer fly"],
    "bait-nightcrawler": ["earthworms", "nightcrawlers", "fishing worms in dirt"],
    "bait-minnow": ["live minnows", "small bait fish"],
    "bait-crayfish": ["a crayfish", "a crawfish"],
    "bait-waxworm": ["wax worms", "mealworms", "maggots used as fishing bait"],
    "bait-cricket": ["a cricket", "a grasshopper"],
    "bait-leech": ["a leech", "leeches used as fishing bait"],
    "bait-liver": ["raw chicken livers"],
    "bait-shrimp": ["shrimp", "raw shrimp used as bait"],
    "bait-corn": ["sweet corn kernels", "canned corn"],
    "bait-cut": ["cut bait", "chunks of fish used as bait", "a dead baitfish"],
    "bait-roe": ["salmon eggs", "fish roe", "a spawn sac"],
    "tool-pliers": ["needle-nose pliers", "fishing pliers"],
    "tool-tackle-box": ["a tackle box", "a tackle box with lures in compartments"],
    "tool-net": ["a landing net", "a fishing net with a handle"],
    "tool-stringer": ["a fish stringer", "a cooler"],
    "tool-bucket": ["a bait bucket", "a minnow bucket"],
    "tool-lifejacket": ["a life jacket", "a life vest"],
    "tool-measure": ["a fish measuring board", "a measuring tape"],
    "tool-sunglasses": ["polarized sunglasses", "sunglasses"],
    "tool-ice-auger": ["an ice auger", "a hand ice drill"],
}
TEMPLATES = ["a photo of {}.", "a close-up photo of {}.", "{}, fishing gear.", "a photo of {} in a store.",
             "a photo of {} on a table."]
old = json.loads((work / "prompts.json").read_text("utf-8"))
assert set(NAMES) == {k for k in old if not k.startswith(("x-", "f-"))}, set(NAMES) ^ set(old)
new = {k: [t.format(n) for n in names for t in TEMPLATES] for k, names in NAMES.items()}
new.update({k: v for k, v in old.items() if k.startswith(("x-", "f-"))})
(work / "prompts2.json").write_text(json.dumps(new, indent=1), encoding="utf-8")
print(len(new), "classes,", sum(len(v) for v in new.values()), "sentences")
