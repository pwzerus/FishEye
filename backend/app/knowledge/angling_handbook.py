"""The angler's handbook: what applies to every fish, not one species.

Baits and why they work, lures, tackle, knots, caring for and cleaning a
catch, telling look-alike fish apart, and when fish bite. Same rules as the
species guides (species_guides.py, docs/adr/0011): reviewed text, every
topic names the pages it came from, and no number that isn't in one of
them. Each topic becomes one retrievable passage (services/rag/chunking.py)
and one card on the fish guide page, under its own anchor, so an answer can
cite exactly the card it used (docs/adr/0024).

Regulations stay out, as in the guides, except where a rule changes how a
beginner handles the fish in front of them (not wasting it, when it may be
filleted, eating advisories); those are paraphrased closely and link the agency
that sets them. A topic that states one state's rule is tagged with that state
(`region`), so it is shown only there (docs/adr/0027).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.species_guides import SOURCES


@dataclass(frozen=True)
class HandbookTopic:
    id: str  # anchor and passage section, e.g. "bait-nightcrawlers"
    category: str  # one of CATEGORIES
    title: str
    body: tuple[str, ...]  # sentences, read in order
    source_ids: tuple[str, ...]
    # A state code when the topic states that state's rules; shown only there
    # (knowledge/jurisdictions.py, docs/adr/0027). "all" otherwise.
    region: str = "all"


# Order is the page's order.
CATEGORIES: dict[str, str] = {
    "baits": "Live and natural bait",
    "lures": "Lures",
    "tackle": "Rods, reels, line and terminal tackle",
    "knots": "Knots",
    "care": "Releasing, keeping and cleaning fish",
    "identify": "Telling fish apart",
    "timing": "When fish bite",
    # Added with docs/adr/0026.
    "technique": "Casting, playing and landing a fish",
    "conditions": "Weather, water and where fish hold",
    "safety": "Staying safe on the water",
    "rules": "License, and rules that follow you home",
}

TOPICS: tuple[HandbookTopic, ...] = (
    # ------------------------------------------------------------------ baits
    HandbookTopic(
        id="bait-worms",
        category="baits",
        title="Worms and nightcrawlers",
        body=(
            "The best all-around bait: nearly every freshwater game fish eats worms.",
            "Large worms and nightcrawlers suit bass and catfish; a small worm or a piece of one "
            "suits bluegill, sunfish, crappie and trout. Redworms are a favorite for redear "
            "sunfish, and worms catch more freshwater drum than any other bait.",
            "Why use them: cheap, easy to find (dig them, or look under boards and rocks after "
            "rain) and easy to keep alive; kept cool they last up to a month.",
            "How to hook: run the hook through the worm, slide it up the shank and thread it "
            "through three to five more times. On a small hook use pieces, with the point pushed "
            "into the end so the bait doesn't slide off. On a large hook leave the tail free to "
            "wiggle.",
        ),
        source_ids=("mdc-bait-lures", "tmf-live-bait", "tamu-baits", "tamu-hook-bait", "kyfw-redear", "agfc-drum"),
    ),
    HandbookTopic(
        id="bait-minnows",
        category="baits",
        title="Minnows and shiners",
        body=(
            "Live baitfish for predators. Size picks the fish: small minnows for crappie, medium ones "
            "for bass and larger trout, large shiners for big bass.",
            "Why use them: crappie and bass eat small fish, and a live minnow moves like the real "
            "thing because it is.",
            "How to hook: for casting or trolling, through both lips, point up, so it swims "
            "naturally. Under a float, through the back without touching the spine, which would "
            "paralyze it. Fished free with no weight, through the tail.",
            "Keep them in a minnow bucket in the water they came from and use them soon. Never "
            "dump unused bait into a lake: it can bring in unwanted animals.",
            "Check your state's bait rules before you buy them: some states restrict live fish as "
            "bait, and California does not allow fish as bait in most of its inland waters.",
        ),
        source_ids=("tmf-live-bait", "tamu-hook-bait", "tamu-baits", "mdc-bait-lures", "tpwd-wcp", "tpwd-lmb", "cdfw-regs-2026"),
    ),
    HandbookTopic(
        id="bait-insects",
        category="baits",
        title="Crickets, grasshoppers and other insects",
        body=(
            "Panfish, sunfish and trout eat insects: crickets, grasshoppers, beetles, ants, "
            "caterpillars.",
            "Why use them: a lively cricket is hard for a hungry bluegill to resist, especially big "
            "bluegill in summer and late fall. Grasshoppers falling from the bank are a summer "
            "staple for river bass.",
            "How to hook a cricket: push the point slowly into the area just behind the head, not "
            "deep (Take Me Fishing). Or thread the hook through the rear of the body: a hook "
            "through the front kills an insect quickly (Texas A&M AgriLife).",
        ),
        source_ids=("tamu-baits", "tmf-live-bait", "tamu-hook-bait", "flyfisherman-gdb"),
    ),
    HandbookTopic(
        id="bait-grubs",
        category="baits",
        title="Mealworms, wax worms and grubs",
        body=(
            "Small larvae sold at bait shops, used for panfish, sunfish and trout. Wax worms are "
            "also used to tip small jigs for redear sunfish.",
            "Why use them: small enough for a sunfish's small mouth, and easy to buy.",
            "How to hook: thread the hook lengthwise through the body, or through the side. Use "
            "several to hide the hook.",
        ),
        source_ids=("tamu-baits", "tamu-hook-bait", "kyfw-redear"),
    ),
    HandbookTopic(
        id="bait-crayfish",
        category="baits",
        title="Crayfish (crawfish)",
        body=(
            "A main food of bass and catfish, and of freshwater drum, which root along the bottom "
            "for them.",
            "Why use them: fish already eat them; hooked well, a crayfish keeps moving naturally.",
            "How to hook: shallowly through the back or the meaty part of the tail, away from vital "
            "organs, or about ½ in from the end of the tail. A cut-off tail can also hide the hook.",
            "Catch them in rocky spots with a fine-mesh net, or a trap baited with chicken liver; "
            "keep them in damp rags or moss.",
        ),
        source_ids=("tamu-baits", "tmf-live-bait", "tamu-hook-bait", "tpwd-fwd"),
    ),
    HandbookTopic(
        id="bait-shad-cut",
        category="baits",
        title="Shad and cut bait",
        body=(
            "Gizzard and threadfin shad, live or cut into pieces, are the top bait for blue catfish, "
            "stripers and hybrids, because shad is their main food. Use it fresh when you can.",
            "How to hook: cut chunks with the skin on and run the hook through the skin, which holds "
            "it on. Hook the chunk shallowly so the point stays exposed.",
            "Shad are nongame fish and legal bait; game fish are not (see Texas bait rules).",
        ),
        source_ids=("tpwd-gsh", "odwc-catfish", "mdc-striper-fg", "mdc-hybrid-fg", "mdc-bigcat", "tamu-hook-bait", "catfishedge-shad", "tpwd-regs-general"),
    ),
    HandbookTopic(
        id="bait-liver-soft",
        category="baits",
        title="Chicken liver, hot dogs, cheese and other soft baits",
        body=(
            "Food-store baits for channel catfish: chicken liver, hot dogs, cheese.",
            "Why they work: a catfish finds food mostly by taste and smell, not sight, and channel "
            "catfish take non-living baits far more readily than flathead or blue catfish.",
            "Drawback: soft baits tear off the hook. Let liver or clams firm up briefly in the sun, "
            "run the hook through several times, or use a small treble hook, which holds soft "
            "baits better.",
        ),
        source_ids=("tpwd-ccf", "odwc-catfish", "tamu-hook-bait", "mdc-bigcat"),
    ),
    HandbookTopic(
        id="bait-stink",
        category="baits",
        title="Stink bait, punch bait and dip bait",
        body=(
            "Prepared catfish baits. Stink bait is a fermented mix of things like cheese, chicken "
            "liver, blood and flour; dip bait is smeared onto a ribbed plastic worm.",
            "Why they work: channel catfish find food mostly by taste and smell, and take prepared "
            "baits more readily than other catfish.",
            "Fish them on the bottom or a few feet under a bobber.",
        ),
        source_ids=("mdc-bait-lures", "odwc-catfish", "mdc-bigcat"),
    ),
    HandbookTopic(
        id="bait-dough-corn",
        category="baits",
        title="Dough baits, PowerBait and corn",
        body=(
            "Dough baits catch carp, catfish, trout and panfish. Carp also take canned or frozen "
            "corn, boiled field corn and bread; stocked trout take dough baits such as PowerBait.",
            "Why they work: scent. Carp rarely hit lures, so a bait they find by smell on the bottom "
            "is the way to catch them.",
            "How to use: mold the dough so it completely hides the hook. Homemade dough is flour or "
            "cornmeal mixed with hot water and a flavor such as garlic or anise; kept in the fridge.",
        ),
        source_ids=("tamu-baits", "tamu-hook-bait", "nydec-carp", "odwc-trout", "mdc-bait-lures"),
    ),
    HandbookTopic(
        id="bait-shrimp",
        category="baits",
        title="Shrimp",
        body=(
            "Used for catfish and freshwater drum.",
            "Pulling off a shell section or two releases scent that draws fish.",
            "How to hook: lightly through the body or the meaty tail; for tail pieces, thread the "
            "hook into the meat to hide it.",
        ),
        source_ids=("tamu-hook-bait", "tpwd-ccf", "agfc-drum"),
    ),
    # ------------------------------------------------------------------ lures
    HandbookTopic(
        id="lure-soft-plastics",
        category="lures",
        title="Soft plastics and jigs",
        body=(
            "A jig is a weighted head on a hook; a soft-plastic worm, grub or crawfish slides over "
            "it to look like prey.",
            "How to fish it: cast, let it sink, then lift the rod tip slowly and let it fall again. "
            "Changing the plastic's color or shape changes how it moves.",
            "Which fish: plastic worms for bass; small jigs for crappie and bluegill.",
        ),
        source_ids=("tmf-lures", "mdc-bait-lures"),
    ),
    HandbookTopic(
        id="lure-crankbaits",
        category="lures",
        title="Crankbaits and plugs",
        body=(
            "Hard plastic lures shaped and painted like baitfish. A plastic lip makes most of them "
            "dive; some float and are worked on top.",
            "How to fish them: sharp twitch-and-stop retrieves work well. Bumping a crankbait off "
            "rocks triggers strikes from bass.",
            "Which fish: bass, small crappie, sometimes catfish.",
            "The most straightforward lures for a beginner.",
        ),
        source_ids=("tmf-lures", "mdc-bait-lures", "torwicks-gdb"),
    ),
    HandbookTopic(
        id="lure-spinnerbaits",
        category="lures",
        title="Spinnerbaits and inline spinners",
        body=(
            "A spinnerbait has a bright skirt over the hook and a metal blade that spins, flashes "
            "and vibrates; it's a bass lure. Small inline spinners suit trout, crappie and small "
            "bluegill.",
            "How to fish them: a steady, even retrieve.",
            "Why they work: color, flash and vibration draw the fish in.",
        ),
        source_ids=("tmf-lures", "mdc-bait-lures", "odwc-trout"),
    ),
    HandbookTopic(
        id="lure-spoons",
        category="lures",
        title="Spoons and slabs",
        body=(
            "Curved metal lures that wobble like an injured baitfish, reflect light and vibrate.",
            "How to fish them: cast and retrieve steadily through the depth the fish are at.",
            "Which fish: once a white bass school is found, anglers often fish spoons near the "
            "surface; small spoons catch stocked trout.",
        ),
        source_ids=("tmf-lures", "tpwd-wtb", "odwc-trout"),
    ),
    HandbookTopic(
        id="lure-topwater",
        category="lures",
        title="Topwater lures",
        body=(
            "Floating lures that make noise and movement on the surface: poppers, pencil poppers, "
            "buzzbaits.",
            "When: early morning and toward dark for bass; topwaters near the bank for hybrids "
            "early in the day.",
            "Why: they draw aggressive fish, and an inactive bass may strike one out of annoyance.",
        ),
        source_ids=("tmf-lures", "mn-lmb", "fwc-bass", "tpwmag-hybrid-2014"),
    ),
    # ------------------------------------------------------------------ tackle
    HandbookTopic(
        id="tackle-reels",
        category="tackle",
        title="Reels: spincast, spinning, baitcasting and fly",
        body=(
            "Spincast: the line sits on an enclosed spool. Easy to learn and forgiving; a good "
            "starter reel for beginners and kids.",
            "Spinning: the most versatile; one medium outfit handles a wide range of lures and "
            "weights, and it suits light line and finesse baits.",
            "Baitcasting: works best with heavier lures and line. Gives more control, but needs a "
            "practiced thumb and brake adjustments when lures change.",
            "Fly reel: you strip line off by hand and the rod casts the line's weight, not the "
            "lure's.",
        ),
        source_ids=("tmf-reels",),
    ),
    HandbookTopic(
        id="tackle-rods",
        category="tackle",
        title="Rod power and action",
        body=(
            "Power is how much force it takes to bend the rod: ultralight, light, medium-light, "
            "medium, medium-heavy, heavy, extra heavy. Ultralight suits light lures and small trout "
            "and panfish; heavy suits big fish and heavy baits.",
            "The rod's label gives its lure weight range: roughly up to ⅜ oz for ultralight, ¼–¾ oz "
            "for medium, ⅜–1 oz for heavy.",
            "Action is where it bends: fast rods bend mostly in the top third and snap back quickly, "
            "for accuracy and hard hooksets; slow rods bend down toward the handle and absorb "
            "shock.",
        ),
        source_ids=("meateater-rods",),
    ),
    HandbookTopic(
        id="tackle-line",
        category="tackle",
        title="Fishing line: monofilament, fluorocarbon and braid",
        body=(
            "Monofilament: the cheapest and the standard. Stretchy, which can weaken a long-distance "
            "hookset, and holds up to rock and wood. Cheap mono keeps coils from the spool "
            "(\"memory\").",
            "Fluorocarbon: nearly invisible underwater, strong and abrasion resistant, so popular in "
            "clear water and as a leader. Stiffer and more expensive.",
            "Braid: much thinner than mono for its strength, no stretch, so bites and hooksets are "
            "felt at once. Less abrasion resistant, and needs a mono or fluorocarbon leader. Its "
            "thin diameter drags less in current.",
        ),
        source_ids=("fs-line", "agfc-drum"),
    ),
    HandbookTopic(
        id="tackle-hooks",
        category="tackle",
        title="Hooks: sizes, J hooks and circle hooks",
        body=(
            "Plain numbers get smaller as they get bigger: a No. 12 is far smaller than a No. 2. "
            "\"Aught\" sizes go the other way: a 12/0 is far bigger than a 2/0.",
            "Typical sizes: bluegill No. 4–8, crappie No. 2–6, bass No. 2 to 4/0, catfish No. 1 to "
            "6/0 by fish size. When in doubt, go smaller so the fish can take it.",
            "Thin wire for small fish and light hooksets (crappie, bluegill, trout); heavier wire "
            "for catfish and big fish, which can straighten a thin hook.",
            "The J hook (Aberdeen, round bend) is the most widely used.",
        ),
        source_ids=("agfc-hooks", "tpwd-sunfish-id"),
    ),
    HandbookTopic(
        id="tackle-circle-hooks",
        category="tackle",
        title="How to use a circle hook",
        body=(
            "A circle hook sets itself: once the fish has the bait in its mouth, a steady, slow "
            "pull turns the hook into the corner of the jaw.",
            "Don't jerk or sweep the rod. Reel down on the fish.",
            "It takes practice to trust one. Big-river catfish anglers mostly use 6/0–8/0 circle "
            "hooks.",
        ),
        source_ids=("agfc-hooks", "odwc-catfish", "mdc-bigcat"),
    ),
    HandbookTopic(
        id="tackle-split-shot",
        category="tackle",
        title="Split shot",
        body=(
            "Split shot are small weights, some as small as a BB, with a groove cut in the middle. "
            "Slide the line into the groove and pinch it shut.",
            "Often a single split shot is all the weight a bait needs to sink. It's easy to add, "
            "move or take off.",
        ),
        source_ids=("tmf-weights",),
    ),
    HandbookTopic(
        id="tackle-sinkers",
        category="tackle",
        title="Sinkers: egg, bullet, cone and pyramid",
        body=(
            "Sinkers range from as small as a BB to a few ounces. Most are lead; tungsten is nearly "
            "indestructible but costs more.",
            "Egg (inline) sinkers: the line runs through them. In a bottom rig the sinker slides "
            "on the main line above a barrel swivel, with the leader and hook below.",
            "Cone sinkers rig a worm Carolina-style; a bullet sinker goes ahead of a Texas-rigged "
            "worm. Pyramid sinkers are heavy weights for surf fishing.",
            "Use only enough weight to hold the bottom.",
        ),
        source_ids=("tmf-weights", "agfc-drum", "mn-lmb", "mdc-bigcat"),
    ),
    HandbookTopic(
        id="tackle-bobbers",
        category="tackle",
        title="Bobbers (floats)",
        body=(
            "A bobber holds the bait at a set depth and shows the bite.",
            "A slip bobber slides up and down the line and suits a lot of situations. Slender floats "
            "are more sensitive.",
            "Use the smallest bobber that floats your bait: you'll see more bites.",
        ),
        source_ids=("tmf-weights", "tmf-bluegill"),
    ),
    HandbookTopic(
        id="tackle-leaders",
        category="tackle",
        title="Leaders and swivels",
        body=(
            "A leader is a short length of line between the main line and the hook.",
            "Braid needs a mono or fluorocarbon leader. A leader a little weaker than the main line "
            "breaks first when snagged, so you lose only the hook.",
            "A barrel swivel joins the main line to the leader and stops a sliding sinker.",
        ),
        source_ids=("fs-line", "mdc-bigcat", "nydec-carp", "agfc-drum"),
    ),
    # ------------------------------------------------------------------ knots
    HandbookTopic(
        id="knot-improved-clinch",
        category="knots",
        title="Improved clinch knot",
        body=(
            "The go-to knot for tying a hook or lure to monofilament.",
            "Pass 5–6 in of line through the hook eye and wrap the tag end around the main line 5–6 "
            "times. Bring the tag end back through the small loop by the eye, then through the big "
            "loop you just made.",
            "Wet the knot, pull it snug and trim the tag end.",
        ),
        source_ids=("zebco-knots",),
    ),
    HandbookTopic(
        id="knot-palomar",
        category="knots",
        title="Palomar knot",
        body=(
            "A strong knot for braid and mono, and many anglers find it easier than the clinch.",
            "Double 4–6 in of line into a loop and push the loop through the hook eye. Tie a loose "
            "overhand knot with the doubled line, then pass the hook through the loop.",
            "Wet it, pull both ends tight and trim.",
        ),
        source_ids=("zebco-knots",),
    ),
    HandbookTopic(
        id="knot-arbor",
        category="knots",
        title="Arbor knot (line to reel)",
        body=(
            "Ties new line onto the reel spool.",
            "Wrap the line around the spool, tie an overhand knot with the tag end around the main "
            "line, then a second overhand knot at the tip of the tag end as a stopper. Pull the "
            "main line to slide the knot tight against the spool.",
        ),
        source_ids=("zebco-knots",),
    ),
    # ------------------------------------------------------------------ care
    HandbookTopic(
        id="care-release",
        category="care",
        title="Catch and release: handling a fish you'll let go",
        body=(
            "To release a fish unharmed, land it quickly: a fish played to exhaustion can be "
            "harmed. Set the hook quickly too, so it doesn't swallow the bait.",
            "Wet your hands (or use a wet rag or glove) and don't rub off the slime, which protects "
            "it from infection. Keep it out of the water no longer than you can hold your breath.",
            "Hold a small fish (under 5 lb) by the lower jaw; support a big one horizontally with "
            "two hands. Keep fingers out of the eyes and gills.",
            "Back the hook out with pliers, hemostats or a hook remover, ideally with the fish in "
            "the water. Don't jerk the line to break it off.",
            "Revive a tired fish facing into the current, supporting its middle and tail until it "
            "swims away.",
            "From deep water, bring it up slowly so it can adjust to the pressure change.",
        ),
        source_ids=("tpwd-cr",),
    ),
    HandbookTopic(
        id="care-keeping",
        category="care",
        title="Keeping your catch fresh",
        body=(
            "Ice is the key to good-tasting fish, especially in summer. Get it into a cooler with "
            "plenty of ice soon after it's caught.",
            "A slush of ice and water chills fish 4–5 times faster than ice alone. A fisheries "
            "handling guide recommends about 2 lb of ice per pound of fish, packed around the fish "
            "and into the belly cavity once it's gutted.",
            "Gutting removes a source of bacteria and lets the fish chill faster.",
            "A fish on a stringer counts as kept. It's illegal to leave edible fish or bait fish "
            "from public waters to die without intending to eat them or use them as bait.",
        ),
        source_ids=("utah-clean-cat", "lsu-handling", "tpwd-regs-general"),
    ),
    HandbookTopic(
        id="care-dispatch-bleed",
        category="care",
        title="Killing a fish quickly and bleeding it",
        body=(
            "For a fish you'll keep, a quick kill avoids bruising the meat: a sharp blow to the head "
            "stuns it, and a spike pushed into the skull just above the eyes kills it and slows "
            "spoilage.",
            "Then bleed it while the heart still pumps: cut through the gills (or rip them with "
            "pliers), or cut the artery at the tail. Leave it in water for about 5–10 minutes, until "
            "the blood stops, then put it on ice.",
            "Why bleed: better-looking, better-tasting meat that chills faster. It's optional.",
        ),
        source_ids=("lsu-handling", "utah-clean-cat"),
    ),
    HandbookTopic(
        id="clean-scaling",
        category="care",
        title="Scaling panfish to cook whole",
        body=(
            "For crappie and bluegill: scrape the scales off both sides (a spoon or scaling tool "
            "works), then dip the fish in clean water to rinse off loose scales and slime.",
            "Leaving the skin on helps the fish hold together, fry crisper and taste better.",
        ),
        source_ids=("ks-cleaning",),
    ),
    HandbookTopic(
        id="clean-fillet",
        category="care",
        title="Filleting bass and other larger fish",
        body=(
            "Lay the fish on its side. Cut just behind the gill cover from the top of the back to "
            "the belly, down to the backbone.",
            "Turn the knife flat and run it along the backbone toward the tail, cutting through the "
            "ribs, and lift the fillet off before you reach the tail.",
            "Skin it: hold the knife flat against the board and slice between skin and meat. Then "
            "cut the rib bones out of the fillet. Repeat on the other side.",
            "Freshwater drum fillet the same way and have no small bones in the fillet; trim the "
            "dark red meat just under the skin.",
        ),
        source_ids=("ks-cleaning", "agfc-drum"),
    ),
    HandbookTopic(
        id="clean-fillet-panfish",
        category="care",
        title="Filleting crappie and bluegill",
        body=(
            "Put a small fillet knife in at the back of the neck and run it along the top of the "
            "ribs toward the belly, coming out at the front of the anal fin, then cut back to the "
            "tail.",
            "Cut down just behind the gill cover and slice the fillet off the ribs; separate it "
            "from the belly. Repeat on the other side.",
            "Cutting along the outside of the ribs saves a little more of the belly meat.",
        ),
        source_ids=("ks-cleaning",),
    ),
    HandbookTopic(
        id="clean-catfish",
        category="care",
        title="Cleaning a catfish (skinning)",
        body=(
            "Catfish are skinned, not scaled. Watch the barbed spines in the side and back fins: "
            "they lock in place. Break the side fins off with pliers and grip the fish with a glove "
            "or rag.",
            "Score the skin around the head and along the back, clamp the head, and pull the skin "
            "toward the tail with catfish skinning pliers.",
            "Fillet along the spine from tail to head and work the fillet off the ribs, or gut it "
            "and cut off the head and tail to cook it whole.",
            "Trim the dark lateral line, fat and connective tissue from the fillet: contaminants "
            "tend to collect there. Soaking fillets in milk or buttermilk for 30 minutes to an hour "
            "takes away a fishy taste.",
        ),
        source_ids=("utah-clean-cat", "ks-cleaning"),
    ),
    HandbookTopic(
        id="care-filleting-rule",
        category="care",
        title="When you may fillet a fish (Texas)",
        body=(
            "A fish that has a length limit may not have its head or tail removed, and may not be "
            "filleted, until you finally land your catch, so its length and species can be checked. "
            "Read TPWD's general fishing rules for the details.",
            "Fish you catch and release right away don't count as in your possession; fish on a "
            "stringer, in a cooler, livewell or bucket do, and must meet length and bag limits.",
        ),
        source_ids=("tpwd-regs-general",),
        region="TX",
    ),
    HandbookTopic(
        id="care-possession-ga",
        category="care",
        title="Keeping fish within the limit (Georgia)",
        body=(
            "In Georgia daily and possession limits are per person, and no one may hold more than "
            "the limit for any species, so each angler should keep their fish on a separate stringer "
            "or in a separate creel.",
            "Lengths are total length, and any fish shorter than the minimum for its species must "
            "go back. Limits differ on some lakes and on waters shared with South Carolina: check "
            "the regulations guide for the water you are on.",
        ),
        source_ids=("garegs-general",),
        region="GA",
    ),
    HandbookTopic(
        id="care-keeping-ca",
        category="care",
        title="Measuring and keeping fish (California)",
        body=(
            "In California a fish's length is its total length: the longest straight line from the "
            "tip of the head to the end of the longest lobe of the tail. Limits are set water by "
            "water; CDFW's interactive regulations map shows the ones for the water you are on.",
            "Salmon and steelhead must be kept so their species and size can be told until you get "
            "home or prepare them to eat, and trout may not be kept alive in a container on a boat.",
        ),
        source_ids=("cdfw-regs-2026",),
        region="CA",
    ),
    HandbookTopic(
        id="care-eating-safely",
        category="care",
        title="Eating your catch safely",
        body=(
            "Cook fish to an internal temperature of 145°F, or until the flesh is no longer "
            "translucent and flakes easily with a fork.",
            "Is fish from this lake safe to eat? State health and wildlife agencies test fish for "
            "contaminants (in Texas, the Department of State Health Services). A "
            "consumption ban means you may not keep fish from that area (catch and release is still "
            "legal); an advisory recommends limiting how much you eat, often by species and size.",
            "Advisories are strictest for pregnant or nursing women, women who may become pregnant, "
            "and children under 12. Check your state's current list before eating fish from a lake.",
            "A carp's flavor depends on the water it came from; freshwater drum are best from cool "
            "water.",
        ),
        source_ids=("foodsafety-temps", "tpwd-consumption", "tpwd-crp", "agfc-drum"),
    ),
    # ------------------------------------------------------------------ identify
    HandbookTopic(
        id="id-catfish",
        category="identify",
        title="Which catfish is it? Channel, blue or flathead",
        body=(
            "All three have whiskers (barbels) and smooth, scaleless skin.",
            "Look at the tail first. Deeply forked: channel or blue catfish. Almost square, only "
            "slightly notched: flathead.",
            "Look at the jaw. Flathead: broad flat head, lower jaw sticking out past the upper. "
            "Channel and blue: upper jaw longer.",
            "Channel vs blue: a channel catfish usually has dark spots and a rounded anal fin with "
            "24–29 rays; a blue catfish has no spots (outside the Rio Grande) and a straight-edged "
            "anal fin with 30 or more rays.",
            "Color: flathead is yellow to brown and mottled; blue is slate blue on the back.",
        ),
        source_ids=("tpwd-ccf", "tpwd-blc", "tpwd-flc", "tpwd-cat-id"),
    ),
    HandbookTopic(
        id="id-black-bass",
        category="identify",
        title="Which bass is it? Largemouth, spotted or Guadalupe",
        body=(
            "Close the fish's mouth and look at the jaw. Reaches well past the back of the eye: "
            "largemouth. Ends at the back of the eye or before it: spotted or Guadalupe bass.",
            "Largemouth: one dark stripe of blotches along each side; most have no tooth patch on "
            "the tongue.",
            "Spotted: a more broken side stripe, rows of dark spots on a whitish belly, and a tooth "
            "patch on the tongue.",
            "Guadalupe: green with a black diamond pattern along the sides, the markings reaching "
            "lower on the body than a spotted bass's; lives in flowing Hill Country streams.",
            "Smallmouth bass have vertical bars, which Guadalupe bass lack.",
        ),
        source_ids=("tpwd-bass-id", "tpwd-lmb", "tpwd-spb", "tpwd-gdb", "tamu-gdb"),
    ),
    HandbookTopic(
        id="id-temperate-bass",
        category="identify",
        title="White bass, striped bass or hybrid?",
        body=(
            "Stripes. Striped bass: strong, dark, unbroken stripes, several reaching the tail. "
            "Hybrid: distinct but usually broken stripes. White bass: faint stripes, only one "
            "reaching the tail.",
            "Body shape. Striped bass are slender (body depth less than a third of the length); "
            "white bass and hybrids are deeper-bodied.",
            "Tongue. White bass: one tooth patch. Striped bass: two distinct parallel patches. "
            "Hybrid: two patches close together, or a single one.",
            "Size. A white bass rarely gets big; a hybrid can exceed 5 lb.",
        ),
        source_ids=("tpwd-wtb", "mdc-striper-fg", "mdc-hybrid-fg", "tpwd-bass-id"),
    ),
    HandbookTopic(
        id="id-panfish",
        category="identify",
        title="Crappie, bluegill, redear or another sunfish?",
        body=(
            "Crappie: silvery and deep-bodied. White crappie have vertical bars and 5–6 dorsal "
            "spines; black crappie have irregular black blotches and 7–8 spines.",
            "Bluegill: a black spot at the back of the dorsal fin, vertical bars, a small mouth and "
            "a flexible black ear flap.",
            "Redear sunfish: a red (male) or orange (female) edge on a short ear flap, and long "
            "pointed pectoral fins.",
            "Green sunfish: a large mouth and turquoise spots. Warmouth: a large mouth and dark "
            "lines radiating from the eye. Longear: a long black ear flap edged in white.",
        ),
        source_ids=("tpwd-wcp", "tpwd-bcp", "tpwd-bgl", "tpwd-rsf", "tpwd-sunfish-id"),
    ),
    HandbookTopic(
        id="id-shad",
        category="identify",
        title="Gizzard shad or threadfin shad?",
        body=(
            "Upper jaw sticks out well past the lower: gizzard shad. It doesn't: threadfin shad.",
            "Threadfin shad have yellowish fins and rarely pass 6 in; gizzard shad are commonly "
            "9–14 in.",
            "The anal fin has 29–35 rays on a gizzard shad and 20–25 on a threadfin.",
        ),
        source_ids=("tpwd-gsh", "tpwd-tfs"),
    ),
    HandbookTopic(
        id="id-others",
        category="identify",
        title="Carp, drum or trout?",
        body=(
            "Common carp: heavy body, brassy to golden, whiskers on the upper jaw and a long dorsal "
            "fin with a toothed spine.",
            "Freshwater drum: silvery, deep-bodied, a long dorsal fin split in two, and it grunts. "
            "Its saltwater relative, the red drum, has a spot on the tail.",
            "Rainbow trout: slim, speckled all over, a pink to red stripe along the side and a "
            "spotted tail; in Texas mostly in stocked winter lakes.",
        ),
        source_ids=("tpwd-crp", "tpwd-fwd", "tpwd-rbt"),
    ),
    # ------------------------------------------------------------------ timing
    HandbookTopic(
        id="timing-day",
        category="timing",
        title="Best time of day",
        body=(
            "Low light is prime time for many fish. Catfish are most active at dawn, dusk and "
            "overnight, and big flatheads feed mostly at night.",
            "Bass take topwater lures best early in the morning and toward dark.",
            "White bass and hybrids are most active at dawn and dusk; hybrids are near the bank "
            "early and move deeper as the day goes on.",
            "Guadalupe bass go deeper on hot, sunny days.",
        ),
        source_ids=("odwc-catfish", "mdc-flathead", "mn-lmb", "odwc-whitebass", "tamu-hsb", "tpwmag-hybrid-2014", "torwicks-gdb"),
    ),
    HandbookTopic(
        id="timing-season",
        category="timing",
        title="Best time of year",
        body=(
            "Spring spawning gathers fish in the shallows: largemouth at about 60°F, crappie at "
            "60–70°F, bluegill from about 70°F, redear when the water reaches the 70s, channel "
            "catfish at 75°F.",
            "White bass run up rivers to spawn in early spring.",
            "Winter is prime for blue catfish in Texas, and the season for stocked rainbow trout, "
            "which stay active when bass and crappie slow down.",
            "Flathead catfish feed little while spawning but heavily before and after it.",
        ),
        source_ids=("tpwd-lmb", "tpwd-wcp", "tpwd-bgl", "kyfw-redear", "tpwd-ccf", "odwc-whitebass", "tpwmag-bluecat-2020", "odwc-trout", "mdc-flathead"),
    ),

    # ------------------------------------------------------------- technique
    HandbookTopic(
        id="cast-spinning",
        category="technique",
        title="Casting a spinning or spincast reel",
        body=(
            "Let the bait or lure hang 10 to 18 inches below the rod tip, and hold the rod at "
            "about waist level with the reel underneath.",
            "Hook the line with your forefinger and open the bail, keeping hold of the line. On a "
            "spincast reel, press and hold the button instead.",
            "Sweep the rod tip back over your dominant shoulder, then bring it forward quickly "
            "toward the target. As the rod comes forward past your shoulder, let go of the line "
            "(or release the button) and the weight of the lure pulls line off the reel.",
            "Close the bail by hand, then reel. A spincast reel's enclosed housing is what keeps "
            "it from tangling, which is why it suits a beginner.",
        ),
        source_ids=("tmf-cast", "tmf-reels"),
    ),
    HandbookTopic(
        id="cast-baitcast",
        category="technique",
        title="Casting a baitcaster without a backlash",
        body=(
            "Let the lure hang 8 to 10 inches below the rod tip. Hold the rod at waist level with "
            "the reel on top and your thumb resting on the spool.",
            "Press the button to go into free spool, keeping your thumb against the spool so it "
            "can't unwind.",
            "Pull the rod back over your dominant shoulder and bring it forward swiftly, aiming "
            "the tip at the target. Lift your thumb off the spool as the rod comes forward.",
            "Put your thumb back on the spool as the lure hits the water: the spool keeps "
            "spinning after the lure stops, and that is what makes a backlash. Then reel once or "
            "twice to engage the anti-reverse.",
            "Baitcasting is an acquired skill. It is worth learning for heavy lures and heavy "
            "line, and it is not the reel to learn to cast on.",
        ),
        source_ids=("tmf-cast", "tmf-reels"),
    ),
    HandbookTopic(
        id="technique-drag",
        category="technique",
        title="Setting the drag",
        body=(
            "The drag is a stack of friction plates in the reel. When a fish pulls harder than the "
            "friction, the spool turns backwards and gives line instead of letting it break.",
            "Set it before the first cast: adjusting it while a fish is on is difficult. The knob "
            "is on the front of a spinning reel, on top of a spincast reel, and shaped like a star "
            "beside the handle on a baitcaster. Right tightens, left loosens.",
            "By hand: pull line straight up above the reel. If it slips out too easily, tighten; "
            "if it won't move, loosen. With a spring scale, set the drag to start giving line at "
            "roughly a third to a half of the line's rated strength \u2014 about 7 to 10 lb on 20 lb "
            "line.",
            "Too tight and a big fish breaks the line; too loose and the fight drags on. Of the "
            "two, too loose is the safer mistake.",
            "With braid, pull against pliers or a pencil rather than bare hands: it cuts fingers.",
        ),
        source_ids=("tmf-drag",),
    ),
    HandbookTopic(
        id="technique-measure",
        category="technique",
        title="Measuring a fish",
        body=(
            "Lay the fish on its side with its jaw closed, and measure a straight line from the "
            "tip of the snout to the extreme tip of the tail fin.",
            "Squeeze a soft tail fin together, or turn a hard tail, to get the longest overall "
            "measurement.",
            "Length limits are set on that measurement and they vary by water body, so check "
            "your state agency's rules for the lake you are on before you keep a fish (in Texas, "
            "TPWD's).",
        ),
        source_ids=("tpwd-measure", "tpwd-cr"),
    ),
    HandbookTopic(
        id="technique-shore",
        category="technique",
        title="Fishing from the bank",
        body=(
            "You do not need a boat. Walk the shoreline and pick a spot away from roads, ramps and "
            "crowds: noise and fishing pressure near an entrance mean fewer bites.",
            "On a lake or pond, cast parallel to the shoreline rather than straight out into the "
            "middle \u2014 fish hold along the bank, often within a foot or two of it.",
            "Fish what you can reach: docks, laydowns, vegetation, rock piles, and any drop-off "
            "where the bank falls into deeper water. Under a pier, fish right against the pilings.",
            "On a river, look for slower water \u2014 eddies and the slack behind rocks and log jams "
            "\u2014 because most game fish avoid heavy current. Where a bridge or pilings rub the "
            "line, use a heavier leader.",
        ),
        source_ids=("tmf-shore", "nydec-where", "indnr-when"),
    ),
    HandbookTopic(
        id="start-first-trip",
        category="technique",
        title="Your first trip in Texas",
        body=(
            "Three things to sort out first: somewhere to go, a license if you need one, and the "
            "rules for that water.",
            "TPWD runs free fishing events and intro classes, lists where to fish across the "
            "state, and publishes fishing and stocking reports that say what is biting where.",
            "The Outdoor Annual app holds the regulations, works offline, and can carry a digital "
            "copy of your license.",
            "A rod and reel, a few hooks, split shot and bobbers, and a tub of worms is a complete "
            "beginner's kit. Some state parks lend tackle.",
        ),
        source_ids=("tpwd-beginners",),
        region="TX",
    ),
    HandbookTopic(
        id="start-first-trip-ga",
        category="technique",
        title="Your first trip in Georgia",
        body=(
            "Three things to sort out first: somewhere to go, a license if you need one, and the "
            "rules for that water.",
            "Georgia WRD has an interactive map of places to fish, including Public Fishing Areas, "
            "Wildlife Management Areas and state parks, and publishes fishing forecasts for the "
            "state's lakes and rivers. Check its closures page before you drive to a ramp.",
            "Fish-n-Learn programs are for children 8 to 15 with an adult, and free fishing days "
            "are listed on WRD's site.",
            "You can borrow a rod, reel and tackle box for the day from the office at participating "
            "state parks. The regulations guide is free online, and in print at WRD offices and "
            "license sellers.",
        ),
        source_ids=("gawrd-angler", "gawrd-parkfishing"),
        region="GA",
    ),
    HandbookTopic(
        id="start-first-trip-ca",
        category="technique",
        title="Your first trip in California",
        body=(
            "Three things to sort out first: somewhere to go, a license if you need one, and the "
            "rules for that water.",
            "CDFW's Fishing in the City program runs short introductory clinics on safety, knots, "
            "rigging, casting and the rules, lends equipment to beginners, and stocks many urban "
            "lakes with rainbow trout and catfish before its clinics.",
            "Anglers 15 and younger need no license, and nobody needs one on Free Fishing Days.",
            "Before you buy minnows, read the bait rules: most inland waters don't allow fish as "
            "bait, so worms, insects and lures are the usual start.",
        ),
        source_ids=("cdfw-fitc", "cdfw-license", "cdfw-regs-2026"),
        region="CA",
    ),
    # ------------------------------------------------------------ conditions
    HandbookTopic(
        id="cond-cover",
        category="conditions",
        title="Cover: weeds, wood and docks",
        body=(
            "Cover gives fish shelter, shade and protection, and draws the baitfish and insects "
            "they eat. It is where to cast first.",
            "Weed beds and lily pads hold insects and baitfish; fish their edges and the openings "
            "in them, which also keeps your line out of the salad. The best weed beds run into "
            "deeper water.",
            "Downed trees, stumps, branches and rock piles all work the same way.",
            "Docks are productive at any time of day because of the shade. The biggest fish often "
            "sit far underneath, so do not fish only the outside edge.",
            "Overhanging trees and brushy banks drop insects into the water, and big fish hold "
            "right under them \u2014 sometimes a foot from shore, wherever there is a foot of water.",
        ),
        source_ids=("nydec-where", "indnr-when"),
    ),
    HandbookTopic(
        id="cond-points",
        category="conditions",
        title="Points, drop-offs and inlets",
        body=(
            "A point that slopes gradually into deeper water is a route fish use between deep "
            "water and the shallows. Fish the tip and the corners. A point that drops off sharply, "
            "or has no deep water near it, is worth less.",
            "A drop-off \u2014 where the bottom falls away \u2014 lets fish move between depths without "
            "crossing open water, which is why they follow it.",
            "Where a creek or stream runs into the lake it brings food, and fish gather there. "
            "Inlets are at their best when fish stage before moving upstream to spawn.",
        ),
        source_ids=("nydec-where",),
    ),
    HandbookTopic(
        id="cond-clarity",
        category="conditions",
        title="Water clarity and lure colour",
        body=(
            "How far you can see into the water decides what the fish can see, and so what to "
            "throw.",
            "Clear water (two feet of visibility or more): natural, prey-coloured or flashy "
            "lures \u2014 spoons, spinners, jerkbaits, lipless crankbaits, willow-blade spinnerbaits, "
            "soft plastics.",
            "Stained water (a few inches of visibility): bright colours, such as chartreuse soft "
            "plastics, bright lipless crankbaits, and gold or copper blades.",
            "Muddy water (an inch or two): dark colours and vibration \u2014 bladed swim jigs, "
            "rattling crankbaits, Colorado-blade spinnerbaits, soft plastic stickbaits.",
        ),
        source_ids=("indnr-when",),
    ),
    HandbookTopic(
        id="cond-wind",
        category="conditions",
        title="Wind",
        body=(
            "Fish the windblown shoreline. Wind pushes warm surface water and the food in it "
            "against the bank, and the fish follow.",
            "If the wind makes casting hard, use a heavier lure, and watch for snags.",
            "An easterly wind usually means a high-pressure system has moved in, which is the "
            "old saying \"wind from the east, fish bite least\" \u2014 and there is something to it.",
        ),
        source_ids=("indnr-when", "kyfw-weather"),
    ),
    HandbookTopic(
        id="cond-fronts",
        category="conditions",
        title="Fronts and pressure",
        body=(
            "Weather matters more than most beginners expect, and barometric pressure is the part "
            "that matters most.",
            "Fish feed hard ahead of a storm, as a low-pressure system moves in.",
            "After it passes, a bright high-pressure \"bluebird\" day is the hardest fishing of "
            "all: fish hold tight to cover, go lethargic and sit on the bottom, especially in "
            "clear lakes in late winter and early spring.",
            "In those seasons the best days come on the third or fourth day of stable weather, "
            "whatever the temperature. Plan a trip for the day before a front, or three to four "
            "days after one.",
        ),
        source_ids=("kyfw-weather", "indnr-when"),
    ),
    HandbookTopic(
        id="cond-light",
        category="conditions",
        title="Cloud, rain and sun",
        body=(
            "Cloud and rain cut the light getting into the water, which lets predators ambush "
            "prey, and fish roam further to find food. Rain also washes insects in.",
            "On a bright, sunny day fish deeper, in shade, or later in the day once the shallows "
            "have warmed.",
            "A bright spring day is good on a shallow, stained lake, where the shallows warm fast "
            "and draw fish in, and poor on a deep, clear one, where the fish are more "
            "light-sensitive and the water warms slowly.",
            "In cold water, slow down: small lures, light line, a slow retrieve near the bottom.",
        ),
        source_ids=("indnr-when", "kyfw-weather"),
    ),
    # ---------------------------------------------------------------- safety
    HandbookTopic(
        id="safe-lifejacket",
        category="safety",
        title="Life jackets",
        body=(
            "Who must wear one, and when, is set by each state; the law for your state is on its "
            "own card.",
            "Of the people who died in recreational boating accidents in 2019, drowning was the "
            "reported cause for 79 percent, and 86 percent of those who drowned were not wearing "
            "a life jacket.",
            "Check the fit: do it up, raise your arms over your head and have someone pull up on "
            "the shoulders. If it rides up over your chin or face it is too big. A child's jacket "
            "does not work for an adult, and do not buy one for a child to grow into.",
        ),
        source_ids=("tpwd-lifejacket",),
    ),
    HandbookTopic(
        id="safe-lifejacket-tx",
        category="safety",
        title="Life jacket law (Texas)",
        body=(
            "In Texas every child under 13 must wear a US Coast Guard-approved life jacket on a "
            "boat under 26 feet while it is under way, which includes drifting but not at anchor. "
            "Adults must have one aboard that fits and is easy to reach.",
        ),
        source_ids=("tpwd-lifejacket",),
        region="TX",
    ),
    HandbookTopic(
        id="safe-lifejacket-ga",
        category="safety",
        title="Life jacket law (Georgia)",
        body=(
            "In Georgia every child under 13 must wear a life jacket while the boat is under way, "
            "unless the child is inside a fully enclosed cabin.",
            "Every boat must carry a wearable life jacket for each person aboard, and boats from "
            "16 feet up to 26 feet also need a throwable one.",
            "Anyone on a personal watercraft must wear a life jacket at all times.",
        ),
        source_ids=("garegs-boating", "gawrd-equipment"),
        region="GA",
    ),
    HandbookTopic(
        id="safe-lifejacket-ca",
        category="safety",
        title="Life jacket law (California)",
        body=(
            "In California every child under 13 must wear a US Coast Guard-approved life jacket "
            "while the boat is under way \u2014 on motorboats, sailboats, and human-powered boats "
            "such as kayaks and canoes. On a motorboat or sailboat a child inside an enclosed cabin "
            "is exempt, and on a sailboat so is a child in a harness tethered to the boat.",
            "Every boat must carry a life jacket that fits each person aboard, within easy reach. "
            "Sailboats 16 feet and longer also need a throwable one.",
        ),
        source_ids=("cadbw-safety",),
        region="CA",
    ),
    HandbookTopic(
        id="safe-handling",
        category="safety",
        title="Handling a fish without getting hurt",
        body=(
            "Catfish have stiff, barbed spines in the dorsal and both pectoral fins, and they are "
            "the usual reason someone goes home early. Hold a catfish from behind, with your hand "
            "over its back and behind those fins, or use pliers and a grip.",
            "Use long-nosed pliers or a hook-out to take hooks from any fish, rather than fingers.",
            "A fish that is going back wants wet hands and as little time out of the water as "
            "possible; a fish you are keeping goes on ice straight away.",
        ),
        source_ids=("utah-clean-cat", "tpwd-cr", "lsu-handling"),
    ),
    # ----------------------------------------------------------------- rules
    HandbookTopic(
        id="rule-license",
        category="rules",
        title="Do I need a fishing license? (Texas)",
        body=(
            "In Texas, residents and non-residents need a fishing license to fish public water, "
            "and a resident taking fish, mussels, clams or crayfish needs a freshwater or "
            "saltwater endorsement with it.",
            "No license is needed for anyone under 17, resident or not; for Texas residents born "
            "before 1 January 1931; and for certain people with intellectual disabilities under "
            "the conditions TPWD sets out.",
            "You can also fish without one in Texas state parks.",
            "A Lake Texoma license covers both the Texas and Oklahoma water of that lake and "
            "nothing else. License terms and fees change: TPWD's license page is the authority.",
        ),
        source_ids=("tpwd-license", "tpwd-beginners"),
        region="TX",
    ),
    HandbookTopic(
        id="rule-clean-drain-dry",
        category="rules",
        title="Clean, drain and dry (Texas)",
        body=(
            "Zebra mussels and other invasive species travel between Texas lakes on boats, "
            "trailers and in water, so the law asks three things of anyone leaving the water.",
            "Clean: remove all plants, animals and mud from the boat and trailer, and wash them "
            "thoroughly.",
            "Drain: drain all water before leaving the area \u2014 livewells, bilge, ballast and "
            "engine cooling water. Pull the plug.",
            "Dry: let everything dry completely before launching somewhere else, ideally for a "
            "week or more.",
            "A boat kept on infested water, or with mussels attached, needs TPWD's advice and "
            "often professional hot-water cleaning before it is moved to another lake.",
        ),
        source_ids=("tpwd-cdd",),
        region="TX",
    ),
    HandbookTopic(
        id="rule-license-ga",
        category="rules",
        title="Do I need a fishing license? (Georgia)",
        body=(
            "In Georgia, anglers 16 and older need a current Georgia fishing license with them, in "
            "fresh or salt water. Anyone helping an angler, for example by netting a fish, must be "
            "licensed too.",
            "Nobody 15 or younger needs a fishing or trout license; Georgia residents that age can "
            "buy an optional youth license that includes trout privileges.",
            "No license is needed to fish a private pond, or for a resident and their immediate "
            "family fishing on their own land. A pond owned by a government is not private.",
            "From 16, fishing designated trout waters or keeping mountain trout also needs a trout "
            "license; in a state park's impounded waters you need one only to keep trout. Saltwater "
            "anglers 16 and older also need a free Saltwater Information Program (SIP) permit.",
            "On the lakes and rivers Georgia shares with Alabama and South Carolina, such as West "
            "Point, Walter F. George, Hartwell and Clarks Hill, either state's license is valid. "
            "License terms and fees change: Georgia WRD's license page is the authority.",
        ),
        source_ids=("gawrd-license", "garegs-license", "garegs-bordering"),
        region="GA",
    ),
    HandbookTopic(
        id="rule-clean-drain-dry-ga",
        category="rules",
        title="Clean, drain and dry (Georgia)",
        body=(
            "Georgia WRD asks everyone leaving the water to stop the spread of aquatic nuisance "
            "species, such as zebra mussel larvae too small to see.",
            "Clean: inspect the boat, trailer and gear, remove plants and mud, and wash everything "
            "with a high-pressure hose or hot water of at least 120\u00b0F.",
            "Drain: drain all water from inside the boat \u2014 bilge, motor and livewell \u2014 "
            "and pull the plug, away from the ramp.",
            "Dry: let everything air-dry, preferably for at least five days, or towel it dry before "
            "going to another lake. Never move bait from one waterway to another.",
        ),
        source_ids=("gawrd-cdd", "garegs-general"),
        region="GA",
    ),
    HandbookTopic(
        id="rule-license-ca",
        category="rules",
        title="Do I need a fishing license? (California)",
        body=(
            "In California anyone 16 or older needs a sport fishing license, kept in their "
            "immediate possession while fishing. Under 16, no license is needed.",
            "Report cards are needed by anyone, whatever their age, fishing for steelhead or "
            "sturgeon (and salmon in the Klamath, Trinity and Smith rivers), even on Free Fishing "
            "Days.",
            "Fishing with two rods in inland waters needs a Second Rod validation on the license; "
            "anglers under 16 may use two rods without one.",
            "No license is needed to fish from a public pier in ocean waters, and none on CDFW's "
            "Free Fishing Days. License terms and fees change: CDFW's license page is the authority.",
        ),
        source_ids=("cdfw-license", "cdfw-regs-2026", "cdfw-fitc"),
        region="CA",
    ),
    HandbookTopic(
        id="rule-clean-drain-dry-ca",
        category="rules",
        title="Clean, drain and dry, and mussel inspections (California)",
        body=(
            "Quagga, zebra and now golden mussels threaten California's lakes, and many reservoirs "
            "inspect boats at the ramp: a boat that isn't clean, drained and dry can be quarantined "
            "or turned away.",
            "Clean: remove all plants, animals and mud from the boat, motor and trailer, put them in "
            "the trash, and rinse away from storm drains and waterways.",
            "Drain: drain the motor, ballast, livewell and buckets on land before leaving.",
            "Dry: leave compartments open and let the boat dry for at least five days in warm, dry "
            "weather, up to 30 days in cool, damp weather.",
            "By law, a motorized boat used in fresh water must display a current Mussel Fee sticker "
            "next to its registration. Report a suspected mussel to CDFW with a close-up photo and "
            "the location.",
        ),
        source_ids=("cadbw-mussels", "cdfw-mussels"),
        region="CA",
    ),
    HandbookTopic(
        id="rule-line-disposal",
        category="rules",
        title="Old fishing line",
        body=(
            "Discarded line tangles birds and other animals and does not break down in a "
            "landfill. It never belongs on the bank or in the water.",
            "Monofilament and fluorocarbon can be recycled, in colour or clear, at a collection "
            "bin \u2014 at tackle shops, ramps, piers and access points \u2014 but not in household "
            "recycling. Take the hooks and lures off first, and leave out line with weed or "
            "growth on it. Keep a coffee can in the tackle box until you have enough to drop off.",
            "Braided and fused line cannot be recycled: cut it into pieces shorter than a foot "
            "and put it in a covered bin so animals cannot reach it.",
        ),
        source_ids=("tmf-line-recycle",),
    ),
    # ------------------------------------------------------- care (cooking)
    HandbookTopic(
        id="cook-methods",
        category="care",
        title="Cooking a fish you caught",
        body=(
            "The ten-minute rule covers most methods: ten minutes of cooking per inch of "
            "thickness, turning once. A piece under half an inch thick needs less and no turning. "
            "It does not apply to deep frying or the microwave.",
            "Bake at 400\u00b0F with a little liquid \u2014 broth or lemon juice \u2014 about five minutes a "
            "side for an inch-thick piece. Broil four to five inches from the heat. Grill with a "
            "baste, turning halfway. Saut\u00e9 over medium heat in a non-stick pan.",
            "It is done when the flesh is opaque and flakes easily with a fork, and the inside "
            "has reached 145\u00b0F. Colour alone does not tell you.",
            "Catfish is mild and sweet, close to any other white fish, and takes whatever "
            "seasoning you like \u2014 lemon and butter, cajun, paprika and oregano.",
        ),
        source_ids=("tamu-catfish-cook", "umn-fish"),
    ),
    HandbookTopic(
        id="cook-storage",
        category="care",
        title="Keeping and thawing fish at home",
        body=(
            "Raw fish keeps one to two days in the refrigerator. Cooked fish should be cooled "
            "below 41\u00b0F within two hours, and reheated to 165\u00b0F.",
            "Thaw in the refrigerator, which is the best way, allowing up to 24 hours per pound; "
            "open vacuum packaging before thawing. Cold running water in a sealed bag is the fast "
            "way. Never thaw on the counter, in standing water or in hot water.",
        ),
        source_ids=("umn-fish", "uaf-freezing", "tamu-catfish-cook"),
    ),
    HandbookTopic(
        id="cook-freezing",
        category="care",
        title="Freezing your catch",
        body=(
            "Freezing keeps quality, it does not add any: a fish that was poorly handled on the "
            "water will be a poor fish out of the freezer. Gut and chill it quickly, and do not "
            "freeze fish with soft flesh or blood clots in it.",
            "Cut it down to fillets or steaks first: small packages freeze faster.",
            "Vacuum packaging is best. Failing that, double-wrap in plastic, or use heavy freezer "
            "bags with the air pressed out \u2014 do not add water. A glaze of ice works but has to be "
            "renewed every few months. Label each package with the fish and the date.",
            "Freeze fast, on the coldest setting, without packing the freezer full: it should be "
            "frozen solid within 24 hours.",
            "Fatty fish such as trout keep in excellent condition about three months, lean fish "
            "roughly twice that. Raw fish is safe for three to eight months. Freezer burn is "
            "moisture escaping through imperfect wrapping; rancid fat and ice-crystal damage come "
            "from long storage and a freezer that keeps changing temperature.",
        ),
        source_ids=("uaf-freezing", "umn-fish"),
    ),
)

_BY_ID = {t.id: t for t in TOPICS}


def get_topic(topic_id: str) -> HandbookTopic | None:
    return _BY_ID.get(topic_id)


def _check() -> None:
    ids = [t.id for t in TOPICS]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate handbook topic ids")
    for t in TOPICS:
        if t.category not in CATEGORIES:
            raise ValueError(f"{t.id}: unknown category {t.category!r}")
        missing = [i for i in t.source_ids if i not in SOURCES]
        if missing:
            raise ValueError(f"{t.id}: unknown sources {missing}")


_check()
