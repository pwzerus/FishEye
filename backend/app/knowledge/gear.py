"""What to buy: the gear a beginner meets in the guides, with a real photo.

The guides and handbook say "a No. 6 hook under a bobber" or "a split shot
a foot above the hook"; someone who has never been in a tackle shop needs to
see what those look like before they can buy them. Each item here is one
thing on the shelf: what it is for, which fish it suits, the handbook topic
that explains it in full, and whether it belongs in a first kit.

Text is ours, written from the handbook topics it links (which carry the
agency sources). No brands and no prices: those go stale and FishEye sells
nothing.

Photos are Wikimedia Commons files picked by eye on 2026-11-06 (one per
item, a clear picture of the thing itself), public domain, CC0 or CC BY
only, so they are safe in a commercial product with their credit
(docs/data-sources.md, "Gear photos"). They are hot-linked from Wikimedia
with the credit beside them, like the fish photos (ADR 0015); nothing is
copied into the repo. An item without a good open photo has none: the text
still says what to look for.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Display order of the categories, with their headings.
CATEGORIES: dict[str, str] = {
    "rods-reels": "Rods and reels",
    "line": "Line",
    "terminal": "Hooks, weights and floats",
    "lures": "Lures",
    "bait": "Live and natural bait",
    "tools": "Tools and safety",
}


@dataclass(frozen=True)
class GearPhoto:
    file: str  # "File:Spinning reel.jpg"
    url: str  # a 960 px (or smaller, whole) thumbnail on upload.wikimedia.org
    width: int
    height: int
    author: str
    licence: str  # "CC BY 4.0", "Public domain"
    licence_url: str | None
    page: str  # the file's page on Commons


@dataclass(frozen=True)
class GearItem:
    id: str
    name: str
    category: str
    what: str  # what it is and what it's for, one or two sentences
    tip: str  # how to choose or use it, one sentence
    topic: str | None  # the handbook topic that explains it (angling_handbook.py)
    fish: tuple[str, ...] = ()  # guide slugs it's a good choice for
    first_kit: bool = False  # on the "first trip" shopping list
    photo: GearPhoto | None = field(default=None, compare=False)


_PAN = ("bluegill", "redear-sunfish", "white-crappie", "black-crappie", "yellow-perch")
_BASS = ("largemouth-bass", "smallmouth-bass", "spotted-bass", "guadalupe-bass")
_CAT = ("channel-catfish", "blue-catfish", "flathead-catfish", "brown-bullhead")
_TROUT = ("rainbow-trout", "brown-trout", "brook-trout", "cutthroat-trout")

ITEMS: tuple[GearItem, ...] = (
    # ------------------------------------------------------------ rods and reels
    GearItem(
        "combo-spincast", "Spincast rod and reel (push-button)", "rods-reels",
        "A short rod with a closed reel: press the button, cast, let go. The line can't tangle "
        "into a bird's nest, so it's the easiest outfit to start with, and the usual kids' rod.",
        "Sold as a ready-spooled combo; one with 6 to 10 lb line covers panfish, small bass and "
        "stocked trout.",
        "tackle-reels", _PAN + ("rainbow-trout", "channel-catfish"), first_kit=True,
    ),
    GearItem(
        "rod-spinning", "Spinning rod", "rods-reels",
        "The all-round rod: the reel hangs under it and the guides are large near the handle. "
        "A 6 to 7 ft medium-light or medium rod handles most lake fishing.",
        "Read the label: it gives the line and lure weight the rod is made for.",
        "tackle-rods", _PAN + _BASS + _TROUT + ("walleye",), first_kit=True,
    ),
    GearItem(
        "reel-spinning", "Spinning reel", "rods-reels",
        "An open-faced reel with a bail that flips over to release line. Versatile and good with "
        "light line and small lures; the next step up from spincast.",
        "A 2500 or 3000 size suits a medium-light rod; spool it with 6 to 10 lb mono.",
        "tackle-reels", _PAN + _BASS + _TROUT + ("walleye",), first_kit=True,
    ),
    GearItem(
        "rod-baitcasting", "Baitcasting rod", "rods-reels",
        "A rod with the reel on top and a trigger under the handle, made for heavier lures and "
        "line: bass with big baits, pike, catfish.",
        "Learn on a spinning rod first; a baitcaster needs a practised thumb.",
        "tackle-rods", _BASS + _CAT + ("northern-pike", "striped-bass"),
    ),
    GearItem(
        "reel-baitcasting", "Baitcasting reel", "rods-reels",
        "A reel whose spool turns as you cast. Accurate and strong, but it backlashes if the "
        "spool outruns the line, so it has brakes to set for each lure.",
        "Set the brake high to start and lower it as your thumb learns.",
        "cast-baitcast", _BASS + _CAT + ("northern-pike", "striped-bass"),
    ),
    GearItem(
        "rod-fly", "Fly rod and reel", "rods-reels",
        "A long, light rod that casts the weight of a thick fly line, not of the lure, so it can "
        "throw flies that weigh nothing. Classic for trout, fun for bluegill.",
        "A 9 ft 5-weight is the usual first trout fly rod.",
        "method-fly", _TROUT + ("bluegill",),
    ),
    GearItem(
        "rod-ice", "Ice fishing rod", "rods-reels",
        "A short rod, about 2 to 3 ft, for jigging straight down through a hole in the ice.",
        "Only go on ice that's thick enough; see the ice safety topic first.",
        "method-ice", ("yellow-perch", "bluegill", "black-crappie", "walleye", "northern-pike"),
    ),
    GearItem(
        "pole-cane", "Cane pole", "rods-reels",
        "A long pole with line tied to the tip and no reel: the cheapest way to fish a bobber "
        "and worm along the bank for bluegill and crappie.",
        "Tie line about as long as the pole.",
        "tackle-bobbers", _PAN,
    ),
    # --------------------------------------------------------------------- line
    GearItem(
        "line-mono", "Monofilament line", "line",
        "Single-strand nylon line: cheap, a little stretchy, easy to tie. The standard line for "
        "a first reel.",
        "6 to 8 lb for panfish and trout, 10 to 14 lb for bass and catfish.",
        "tackle-line", _PAN + _TROUT + _BASS + ("channel-catfish",), first_kit=True,
    ),
    GearItem(
        "line-braid", "Braided line", "line",
        "Woven line, much thinner than mono for its strength and with no stretch, so you feel "
        "every bite. Needs a mono or fluorocarbon leader.",
        "Use a palomar knot; braid slips in some knots meant for mono.",
        "tackle-line", _BASS + ("northern-pike", "blue-catfish"),
    ),
    # ----------------------------------------------------------------- terminal
    GearItem(
        "hook-j", "Bait hooks (J hooks)", "terminal",
        "The plain hook shaped like a J. Sizes run backwards: a No. 8 is small, a No. 1 bigger; "
        "past 1/0 the number grows with the hook.",
        "No. 6 to 8 for bluegill, No. 2 to 4 for crappie and trout, 1/0 and up for catfish.",
        "tackle-hooks", _PAN + _TROUT + _CAT, first_kit=True,
    ),
    GearItem(
        "hook-circle", "Circle hooks", "terminal",
        "A hook whose point turns back toward the shank. It catches the corner of the jaw as the "
        "fish swims off, so it's rarely swallowed: good for fish you'll release.",
        "Don't jerk to set it: just reel steadily.",
        "tackle-circle-hooks", _CAT + ("striped-bass",),
    ),
    GearItem(
        "hook-treble", "Treble hooks", "terminal",
        "Three hooks in one, found on crankbaits and spoons and used for dough and stink baits "
        "for catfish and carp.",
        "Some waters ban them or limit how many; check the rules.",
        "bait-stink", _CAT + ("common-carp",),
    ),
    GearItem(
        "sinker-split-shot", "Split shot", "terminal",
        "Small round weights with a slot: pinch one onto the line to sink a bait. Often all the "
        "weight a bobber rig needs.",
        "Pinch it about a foot above the hook; use pliers, not your teeth.",
        "tackle-split-shot", _PAN + _TROUT, first_kit=True,
    ),
    GearItem(
        "sinker-egg", "Egg and bullet sinkers", "terminal",
        "Weights with a hole through them. The line slides through, so a fish can take the bait "
        "without feeling the weight: the basis of a bottom rig for catfish.",
        "Stop it with a swivel and tie 1 to 2 ft of leader below.",
        "tackle-sinkers", _CAT + ("common-carp", "freshwater-drum"),
    ),
    GearItem(
        "sinker-bank", "Bank and pyramid sinkers", "terminal",
        "Heavier weights that tie on the end of a line to hold the bottom in current or wind.",
        "Use only enough weight to hold bottom.",
        "rig-bottom", _CAT + ("freshwater-drum",),
    ),
    GearItem(
        "bobber", "Bobbers (round floats)", "terminal",
        "Clip-on floats that hold the bait off the bottom and dip when a fish bites. The simplest "
        "way to see a bite.",
        "The smallest bobber that floats your bait shows the most bites.",
        "tackle-bobbers", _PAN + ("rainbow-trout",), first_kit=True,
    ),
    GearItem(
        "float-slip", "Slip bobbers and floats", "terminal",
        "Slender floats that slide on the line and stop at a bobber stop, so you can fish any "
        "depth and still cast easily.",
        "Set the stop so the bait hangs just above the weeds or the fish.",
        "rig-slip-bobber", _PAN + ("walleye",),
    ),
    GearItem(
        "swivel", "Swivels and snap swivels", "terminal",
        "Small metal links that stop line twist and join the main line to a leader. A snap swivel "
        "lets you change lures without retying.",
        "A snap can weaken a crankbait's action; tie straight to lures when you can.",
        "tackle-leaders", _CAT + _TROUT,
    ),
    GearItem(
        "leader-wire", "Wire leaders", "terminal",
        "A short length of wire between line and lure, so the teeth of pike and muskie can't cut "
        "the line.",
        "Only for toothy fish; other fish see it and bite less.",
        "tackle-leaders", ("northern-pike",),
    ),
    GearItem(
        "jig-head", "Jig heads", "terminal",
        "A hook with a lead head moulded on, for threading soft plastics. Small ones catch "
        "crappie and perch; bigger ones bass and walleye.",
        "1/32 to 1/16 oz for crappie, 1/8 to 1/4 oz for walleye and bass.",
        "rig-jigs", _PAN + _BASS + ("walleye",),
    ),
    # -------------------------------------------------------------------- lures
    GearItem(
        "lure-soft-worm", "Soft plastic worms", "lures",
        "Rubbery worms, rigged weedless (Texas rig) or wacky. The bass lure most anglers start "
        "with.",
        "Green pumpkin or black in a 4 to 7 in size covers most lakes.",
        "lure-soft-plastics", _BASS,
    ),
    GearItem(
        "lure-grub", "Curly-tail grubs", "lures",
        "A small soft body with a tail that flutters as it moves. On a jig head, one of the best "
        "lures for crappie, perch, white bass and walleye.",
        "Swim it slowly just above the bottom.",
        "rig-jigs", _PAN + ("white-bass", "walleye", "smallmouth-bass"),
    ),
    GearItem(
        "lure-crankbait", "Crankbaits", "lures",
        "Hard plastic or wooden baitfish with a lip that makes them dive and wobble when reeled. "
        "The lip's size sets how deep it runs.",
        "Pick one that dives a little deeper than the water, so it bumps bottom.",
        "lure-crankbaits", _BASS + ("walleye", "white-bass"),
    ),
    GearItem(
        "lure-lipless", "Lipless crankbaits", "lures",
        "Flat-sided, rattling baits with no lip; they sink and can be fished at any depth.",
        "Reel it fast over grass, then let it fall.",
        "lure-crankbaits", _BASS + ("white-bass", "striped-bass"),
    ),
    GearItem(
        "lure-jerkbait", "Jerkbaits and minnow plugs", "lures",
        "Long, thin hard baits shaped like a minnow: twitch and pause them, and they dart like an "
        "injured fish.",
        "Works best in clear, cool water.",
        "lure-crankbaits", _BASS + _TROUT + ("walleye", "northern-pike"),
    ),
    GearItem(
        "lure-spinnerbait", "Spinnerbaits", "lures",
        "A wire frame with spinning blades above a skirted hook. Comes through weeds and wood "
        "well, and flashes in murky water.",
        "Slow-roll it past cover; white or chartreuse in stained water.",
        "lure-spinnerbaits", _BASS + ("northern-pike",),
    ),
    GearItem(
        "lure-inline-spinner", "Inline spinners", "lures",
        "A small blade spinning around a wire shaft. Simple to use, and catches trout, panfish "
        "and bass everywhere.",
        "Reel just fast enough to keep the blade turning.",
        "lure-spinnerbaits", _TROUT + _PAN + _BASS,
    ),
    GearItem(
        "lure-spoon", "Spoons", "lures",
        "A curved piece of metal that wobbles and flashes. Casts far; good for trout, pike and "
        "white bass, and jigged through the ice.",
        "Let it sink, then reel with pauses so it flutters.",
        "lure-spoons", _TROUT + ("northern-pike", "white-bass", "walleye", "kokanee-salmon"),
    ),
    GearItem(
        "lure-popper", "Poppers and topwater lures", "lures",
        "Floating lures fished on the surface: a cupped face spits water when twitched. The "
        "strike is the most exciting in fishing.",
        "Early morning and evening, over calm water near cover.",
        "lure-topwater", _BASS + ("bluegill",),
    ),
    GearItem(
        "lure-swimbait", "Swimbaits", "lures",
        "Soft or jointed baits that look and swim like a real fish, often with a paddle tail.",
        "Reel slow and steady; the tail does the work.",
        "lure-soft-plastics", _BASS + ("striped-bass", "walleye"),
    ),
    GearItem(
        "fly-dry", "Flies", "lures",
        "Hooks dressed with feather and fur to look like insects: dry flies float, nymphs and "
        "streamers sink.",
        "Ask a local shop which flies the trout are taking that month.",
        "method-fly", _TROUT + ("bluegill",),
    ),
    # --------------------------------------------------------------------- bait
    GearItem(
        "bait-nightcrawler", "Nightcrawlers and worms", "bait",
        "Big earthworms, sold in tubs in bait shops and many gas stations. Nearly every "
        "freshwater fish eats them: the surest first bait.",
        "A piece on a small hook for bluegill; a whole one for bass, catfish and trout.",
        "bait-worms", _PAN + _TROUT + _CAT + ("largemouth-bass", "walleye"), first_kit=True,
    ),
    GearItem(
        "bait-minnow", "Live minnows", "bait",
        "Small baitfish (fatheads, shiners) sold by the dozen. Crappie, bass, walleye and pike "
        "eat them.",
        "Hook through the lips or under the back fin; keep them cool and aerated. Some states "
        "limit which minnows you may use or move.",
        "bait-minnows", ("white-crappie", "black-crappie", "walleye", "northern-pike") + _BASS,
    ),
    GearItem(
        "bait-crayfish", "Crayfish", "bait",
        "Small freshwater lobsters that bass, catfish and drum love. Catch them under rocks or buy "
        "them where legal.",
        "Hook through the tail; check your state's rules before moving them.",
        "bait-crayfish", ("smallmouth-bass", "largemouth-bass", "channel-catfish", "freshwater-drum"),
    ),
    GearItem(
        "bait-waxworm", "Wax worms and mealworms", "bait",
        "Small soft grubs sold in cups, the classic ice fishing bait for panfish.",
        "One or two on a small hook or tipped on a tiny jig.",
        "bait-grubs", _PAN + ("rainbow-trout",),
    ),
    GearItem(
        "bait-cricket", "Crickets and grasshoppers", "bait",
        "Live insects that bluegill and trout take near the surface in summer.",
        "Use a light hook through the collar and little or no weight.",
        "bait-insects", _PAN + _TROUT,
    ),
    GearItem(
        "bait-leech", "Leeches", "bait",
        "Ribbon leeches, a favourite walleye and smallmouth bait in the north.",
        "Hook through the sucker end so it swims.",
        "bait-worms", ("walleye", "smallmouth-bass", "yellow-perch"),
    ),
    GearItem(
        "bait-liver", "Chicken liver", "bait",
        "Soft, smelly and cheap from the grocery store: a top channel catfish bait.",
        "Toughen it in the sun or freezer, or tie it on with thread, so it stays on the hook.",
        "bait-liver-soft", ("channel-catfish", "blue-catfish", "brown-bullhead"),
    ),
    GearItem(
        "bait-shrimp", "Shrimp", "bait",
        "Raw grocery shrimp works for catfish, carp and drum in fresh water.",
        "Peeled pieces stay on the hook better.",
        "bait-shrimp", ("channel-catfish", "freshwater-drum", "common-carp"),
    ),
    GearItem(
        "bait-corn", "Sweet corn", "bait",
        "Canned corn catches carp and stocked trout where it's allowed.",
        "Some trout waters ban corn; check before using it.",
        "bait-dough-corn", ("common-carp", "rainbow-trout"),
    ),
    GearItem(
        "bait-cut", "Cut bait (shad and other baitfish)", "bait",
        "Chunks of oily fish such as shad or skipjack. The best bait for big blue catfish.",
        "Use it fresh; cut it into chunks about the size of a matchbox.",
        "bait-shad-cut", ("blue-catfish", "channel-catfish", "flathead-catfish", "striped-bass"),
    ),
    GearItem(
        "bait-roe", "Salmon eggs and spawn sacks", "bait",
        "Real or imitation fish eggs, a classic stream bait for trout and steelhead.",
        "A single egg on a small hook, or a spawn sack drifted along the bottom.",
        "method-steelhead", _TROUT,
    ),
    # -------------------------------------------------------------------- tools
    GearItem(
        "tool-pliers", "Needle-nose pliers", "tools",
        "For taking hooks out quickly and safely, pinching split shot and cutting line.",
        "Keep them on your belt, not in the bottom of the bag.",
        "start-what-to-buy", (), first_kit=True,
    ),
    GearItem(
        "tool-tackle-box", "Tackle box", "tools",
        "A box with small compartments that keeps hooks, weights and lures sorted and dry.",
        "A small clear box is plenty for a first kit.",
        "start-what-to-buy", (), first_kit=True,
    ),
    GearItem(
        "tool-net", "Landing net", "tools",
        "Lifts a fish out of the water without the line breaking. A rubber net is gentler on fish "
        "you release.",
        "Lead the fish head-first into the net; don't chase it.",
        "care-release", _BASS + _TROUT + _CAT,
    ),
    GearItem(
        "tool-stringer", "Stringer or cooler", "tools",
        "Keeps fish you plan to eat alive in the water or cold on ice.",
        "Fish to eat go on ice as soon as possible.",
        "care-keeping", (),
    ),
    GearItem(
        "tool-bucket", "Bait bucket", "tools",
        "Keeps live minnows alive; an aerator helps on hot days.",
        "Never dump leftover bait into the water.",
        "bait-minnows", (),
    ),
    GearItem(
        "tool-lifejacket", "Life jacket", "tools",
        "A US Coast Guard-approved life jacket that fits. Required on boats and the single most "
        "important piece of safety gear.",
        "Wear it, don't just carry it; check the label for fit and weight.",
        "safe-lifejacket", (), first_kit=True,
    ),
    GearItem(
        "tool-measure", "Measuring board or tape", "tools",
        "To check a fish against a size limit before you keep it.",
        "Measure from the tip of the closed mouth to the tip of the pinched tail.",
        "technique-measure", (),
    ),
    GearItem(
        "tool-sunglasses", "Polarised sunglasses", "tools",
        "Cut the glare off the water so you can see weeds, fish and drop-offs, and protect your "
        "eyes from hooks.",
        "Grey or brown lenses suit most days.",
        "cond-clarity", (),
    ),
    GearItem(
        "tool-ice-auger", "Ice auger", "tools",
        "A large hand or powered drill that bores a hole through the ice.",
        "Check ice thickness as you go.",
        "safe-ice", ("yellow-perch", "walleye", "bluegill"),
    ),
)

ITEM_BY_ID: dict[str, GearItem] = {i.id: i for i in ITEMS}


def items() -> list[GearItem]:
    """Every item, in category order, each with its photo when one is pinned."""
    from app.knowledge.gear_photos import PHOTOS

    order = {c: n for n, c in enumerate(CATEGORIES)}
    out = [
        GearItem(**{**i.__dict__, "photo": PHOTOS.get(i.id)})
        for i in ITEMS
    ]
    return sorted(out, key=lambda i: order[i.category])


def for_topic(topic: str) -> list[GearItem]:
    return [i for i in items() if i.topic == topic]


def for_fish(slug: str) -> list[GearItem]:
    return [i for i in items() if slug in i.fish]
