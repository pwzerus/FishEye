"""Gear groups for training and scoring, and what each source label allows.

A photo's label is the set of classes that would be a right answer: an Open
Images "Fishing lure" photo allows every lure; a hand-checked photo of a
spinning reel allows only reel-spinning. Not-gear photos allow the x-*
classes (prompts.json).

The groups are as coarse as the photo labels are: what is learnt from
photos is the group, and which item inside it is left to the text vectors
(train_eval.py). Each source label allows exactly its group(s), never a
group that many labels share: a group allowed by most photos is where a
partial-label fit puts everything (small hooks and swivels, once).
"""
GROUPS = {
    "rod": ["rod-spinning", "rod-baitcasting", "rod-fly", "rod-ice", "pole-cane", "combo-spincast"],
    "reel": ["reel-spinning", "reel-baitcasting", "combo-spincast", "rod-fly"],
    "line": ["line-mono", "line-braid"],
    "hook": ["hook-j", "hook-circle", "hook-treble"],
    "sinker": ["sinker-split-shot", "sinker-egg", "sinker-bank"],
    "float": ["bobber", "float-slip"],
    "terminal": ["swivel", "leader-wire"],
    "lure": ["jig-head", "lure-soft-worm", "lure-grub", "lure-swimbait", "lure-crankbait", "lure-lipless",
             "lure-jerkbait", "lure-popper", "lure-spinnerbait", "lure-inline-spinner", "lure-spoon"],
    "fly": ["fly-dry"],
    "bait": ["bait-nightcrawler", "bait-minnow", "bait-crayfish", "bait-waxworm", "bait-cricket", "bait-leech",
             "bait-liver", "bait-shrimp", "bait-corn", "bait-cut", "bait-roe"],
    "tackle-box": ["tool-tackle-box"],
    "tools": ["tool-pliers", "tool-net", "tool-stringer", "tool-bucket", "tool-lifejacket", "tool-measure",
              "tool-sunglasses", "tool-ice-auger"],
}
# Kinds of lure, for reading results (the fine score already counts them).
LURE_KINDS = {
    "soft-lure": ["lure-soft-worm", "lure-grub", "lure-swimbait"],
    "hard-lure": ["lure-crankbait", "lure-lipless", "lure-jerkbait", "lure-popper"],
    "metal-lure": ["lure-spinnerbait", "lure-inline-spinner", "lure-spoon"],
}
LURES = GROUPS["lure"]
ALL_GEAR = sorted({c for g in GROUPS.values() for c in g})
NOT_GEAR = ["x-fish", "x-water", "x-boat", "x-people", "x-animal", "x-food", "x-city", "x-nature", "x-objects"]

# Open Images label (oi_meta.py names) -> classes it allows.
OI_ALLOWS = {
    "rod": GROUPS["rod"],
    "reel": GROUPS["reel"],
    "lure": LURES,
    "spoon": ["lure-spoon"],
    "surface-lure": ["lure-popper"],
    "spinnerbait": ["lure-spinnerbait", "lure-inline-spinner"],
    "hook": GROUPS["hook"],
    "float": GROUPS["float"],
    "sinker": GROUPS["sinker"],
    "bait": GROUPS["bait"],
    "tackle-box": ["tool-tackle-box"],
    "tackle": ALL_GEAR,  # some gear, which not said: teaches "gear", weighed down in training
    "fly-fishing": ["rod-fly", "fly-dry"],
}
# Commons category kind (commons_cats.py) -> classes it allows, before checking.
COMMONS_ALLOWS = {
    "lure": LURES + ["fly-dry"], "reel": GROUPS["reel"], "rod": GROUPS["rod"], "float": GROUPS["float"],
    "hook": GROUPS["hook"], "line": GROUPS["line"], "sinker": GROUPS["sinker"],
    "bait": GROUPS["bait"], "ice": ["rod-ice", "tool-ice-auger"], "swivel": ["swivel"],
}


def group_of(cls: str) -> set[str]:
    """Every group a class is in (combo-spincast is a rod and a reel)."""
    if cls.startswith("x-"):
        return {"not-gear"}
    return {g for g, members in GROUPS.items() if cls in members}
