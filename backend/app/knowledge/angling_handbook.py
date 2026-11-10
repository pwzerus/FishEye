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

from app.knowledge.jurisdictions import JURISDICTIONS, limits_source_id
from app.knowledge.species_guides import SOURCES
from app.knowledge.state_licenses import STATE_LICENSES, license_body


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
    "rigs": "Rigs and jigs",
    "knots": "Knots",
    "care": "Releasing, keeping and cleaning fish",
    "identify": "Telling fish apart",
    "timing": "When fish bite",
    # Added with docs/adr/0026.
    "technique": "Casting, playing and landing a fish",
    # Added 2026-11-01.
    "methods": "Ways to fish",
    "conditions": "Weather, water and where fish hold",
    "safety": "Staying safe on the water",
    "rules": "Licenses and fishing rules",
    # Added 2026-11-08, from the questions beginners actually ask.
    "trouble": "When it isn't working",
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
            "deep. Or thread the hook through the rear of the body: a hook through the front "
            "kills an insect quickly.",
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
            "When to throw one: early morning and toward dark for bass; topwaters near the bank for "
            "hybrids early in the day.",
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
        title="Rod power, action and length",
        body=(
            "Power is how much force it takes to bend the rod: ultralight, light, medium-light, "
            "medium, medium-heavy, heavy, extra heavy. Ultralight suits light lures and small trout "
            "and panfish; heavy suits big fish and heavy baits.",
            "The rod's label gives its lure weight range: roughly up to ⅜ oz for ultralight, ¼–¾ oz "
            "for medium, ⅜–1 oz for heavy.",
            "Action is where it bends: fast rods bend mostly in the top third and snap back quickly, "
            "for accuracy and hard hooksets; slow rods bend down toward the handle and absorb "
            "shock.",
            "Length: for a first rod, a medium-light rod from 5½ to 6½ ft suits most people, with a "
            "reel for 4 to 12 lb line. Children manage a shorter rod more easily.",
            "The rod's length, action and the line it suits are printed just above the handle.",
        ),
        source_ids=("meateater-rods", "mdc-gear", "mdc-beginners", "nydec-guide", "odwc-fits"),
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
        title="Improved clinch knot: how to tie a fishing knot",
        body=(
            "The go-to fishing knot for tying a hook or lure to monofilament line.",
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
            "One of the easiest and strongest knots, for braid and mono: even a child can tie it, and "
            "many anglers find it easier than the clinch. Not a good choice for crankbaits or lures "
            "with lots of hooks.",
            "Double 4–6 in of line into a loop and push the loop through the hook eye. Tie a loose "
            "overhand knot with the doubled line, then pass the hook through the loop.",
            "Wet it, pull both ends tight and trim.",
        ),
        source_ids=("zebco-knots", "pfbc-knots"),
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
        title="Keeping your catch fresh on ice",
        body=(
            "Ice is the key to good-tasting fish, especially on a hot summer day. Get it into a "
            "cooler with plenty of ice soon after it's caught.",
            "A slush of ice and water chills fish 4–5 times faster than ice alone. A fisheries "
            "handling guide recommends about 2 lb of ice per pound of fish, packed around the fish "
            "and into the belly cavity once it's gutted.",
            "Gutting removes a source of bacteria and lets the fish chill faster.",
            "A fish on a stringer counts as kept. It's illegal to leave edible fish or bait fish "
            "from public waters to die without intending to eat them or use them as bait.",
            "A stringer or a wire basket keeps fish alive in cool water. Run the stringer through "
            "the lower lip, not the gills, where fish die faster. In warm water they die quickly, "
            "so use ice.",
        ),
        source_ids=("utah-clean-cat", "lsu-handling", "tpwd-regs-general", "nydec-guide"),
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
        title="Eating your catch safely: cooking temperature and advisories",
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
            "overnight, and big flatheads feed mostly at night. Cloud and rain cut the light too "
            "(see Cloud, rain and sun).",
            "Bass take topwater lures best early in the morning and toward dark.",
            "White bass and hybrids are most active at dawn and dusk; hybrids are near the bank "
            "early and move deeper as the day goes on.",
            "Guadalupe bass go deeper on hot, sunny days.",
        ),
        source_ids=("odwc-catfish", "mdc-flathead", "mn-lmb", "odwc-whitebass", "tamu-hsb", "tpwmag-hybrid-2014", "torwicks-gdb", "indnr-when"),
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
            "two, too loose is the safer mistake. If your line breaks when a fish makes a run, the "
            "drag is too tight: loosen it.",
            "With braid, pull against pliers or a pencil rather than bare hands: it cuts fingers.",
        ),
        source_ids=("tmf-drag", "nydec-guide"),
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
        id="start-what-to-buy",
        category="technique",
        title="What to buy to start fishing: the gear a beginner needs",
        body=(
            "A beginner's first fishing gear is small: a spincast or spinning rod and reel already spooled with 6 to "
            "10 lb monofilament line, a pack of small bait hooks (No. 6 to 8), a few split shot, "
            "two or three bobbers, and a tub of nightcrawlers.",
            "Add needle-nose pliers to take hooks out, a small tackle box to keep it sorted, and a "
            "life jacket if you'll be on or near deep water.",
            "That outfit catches bluegill, crappie and stocked trout from the bank. Lures, a "
            "landing net and a second rod can wait until you know what you like to fish for.",
            "FishEye's What to buy page shows a photo of each of these, and the license comes "
            "first: check your state's rules before you go.",
        ),
        source_ids=("tpwd-beginners", "tmf-weights", "tpwd-lifejacket"),
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
    # --------------------------------------------------------------- rigs
    HandbookTopic(
        id="rig-jigs",
        category="rigs",
        title="Jigs",
        body=(
            "A jig is a hook with a weighted head, dressed with bucktail, marabou or a plastic body. "
            "A live minnow, leech or nightcrawler can be added to the hook.",
            "Why use one: it catches almost anything, because it can be fished at any depth and "
            "moves like small prey.",
            "How to fish one: cast it, let it sink to the bottom, snap it up a foot or two, and let "
            "it fall back. Repeat, and change the rhythm until the fish show what they want.",
            "Sizes: 1/32–1/8 oz for crappie and sunfish, 1/8–1/4 oz for a tube or a Ned rig. For "
            "crappie, you can also reel a light jig slowly as it sinks, or hang it under a bobber "
            "and shake the bobber.",
        ),
        source_ids=("nydec-walleye", "nydec-crappie", "nydec-bass", "mndnr-crappie", "mndnr-sunfish"),
    ),
    HandbookTopic(
        id="rig-texas",
        category="rigs",
        title="Texas rig",
        body=(
            "A soft plastic worm rigged to slide through weeds and cover, used mostly for bass.",
            "How to set it up: a 1/4–1/2 oz worm weight on the line, then a 2/0 to 4/0 worm hook, "
            "with a 6–10 in ribbon-tail worm. June bug, plum and green pumpkin are common colors.",
            "How to fish it: let it sink to the bottom, then drag it back slowly, or move it a few "
            "feet, wait a few seconds, and move it again.",
        ),
        source_ids=("nydec-bass",),
    ),
    HandbookTopic(
        id="rig-wacky",
        category="rigs",
        title="Wacky rig",
        body=(
            "A soft stick worm hooked through its middle, so both ends flutter as it sinks. It "
            "works in shallow and deep water.",
            "How to set it up: a 4 in stick worm, an O-ring around its middle, and a size 1/0 circle "
            "or octopus hook through the ring. Green pumpkin and watermelon are common colors.",
            "How to fish it: let it sink slowly, with no weight. Once it reaches the bottom, raise "
            "it and let it fall again. Watch the line: a bite can show as a tap there before you feel it.",
        ),
        source_ids=("nydec-bass",),
    ),
    HandbookTopic(
        id="rig-ned",
        category="rigs",
        title="Ned rig",
        body=(
            "A short stick worm on a small jighead, for deep, clear water around rocks when fish "
            "are not chasing.",
            "How to set it up: a 3–4 in stick worm on a 1/8–1/4 oz mushroom jighead.",
            "How to fish it: let it sit on the bottom for 2–5 seconds, drag it a few feet, let it "
            "sit, and repeat.",
        ),
        source_ids=("nydec-bass",),
    ),
    HandbookTopic(
        id="rig-drop-shot",
        category="rigs",
        title="Drop shot",
        body=(
            "A hook tied above the weight, so the bait hangs off the bottom. Used in deep, clear water.",
            "How to set it up: a size 2 to 1/0 octopus hook with a 4–6 in straight-tail worm, and a "
            "1/8–1/2 oz drop-shot weight below it at the end of the line.",
            "How to fish it: when the weight reaches the bottom, let it sit a few seconds, shake the "
            "rod tip, move it a few feet, and repeat.",
        ),
        source_ids=("nydec-bass",),
    ),
    HandbookTopic(
        id="rig-slip-bobber",
        category="rigs",
        title="Slip bobber",
        body=(
            "A bobber that slides on the line, so bait can hang at any depth and you can still cast easily.",
            "How to set it up: put a bobber stop on the line, then a bead, then the bobber. Set the "
            "stop at the depth you want. After the cast, line slides through the bobber until it "
            "reaches the stop.",
            "When: when fish are deeper than a fixed bobber can reach, as crappie and walleye often are in summer.",
        ),
        source_ids=("nydec-walleye", "mndnr-crappie", "mndnr-walleye"),
    ),
    HandbookTopic(
        id="rig-bottom",
        category="rigs",
        title="Sliding sinker bottom rig",
        body=(
            "A weight that slides on the line, so a fish can take the bait without feeling it. The "
            "usual rig for catfish and carp.",
            "How to set it up for catfish: thread 15–20 lb line through a 1 oz egg sinker, tie on a "
            "barrel swivel, tie about 2 ft of heavy monofilament or fluorocarbon to the swivel, and "
            "finish with a 4/0 or 6/0 circle or bait hook.",
            "How to fish it: cast to the spot and let the bait rest on the bottom. Scale the sinker "
            "and hook down for smaller fish.",
        ),
        source_ids=("mn-ccf", "nydec-basics"),
    ),
    # -------------------------------------------------------------- more knots
    HandbookTopic(
        id="knot-tips",
        category="knots",
        title="Keeping line strong",
        body=(
            "A badly tied knot can take away half or more of the line's strength: on 4 lb line, it's "
            "like fishing with 2 lb line.",
            "Wet the knot with water or saliva before pulling it tight.",
            "Don't trim the end too close to the knot, and take care that clippers don't nick the line.",
        ),
        source_ids=("pfbc-knots",),
    ),
    HandbookTopic(
        id="knot-surgeons-loop",
        category="knots",
        title="Surgeon's loop for swivels and snelled hooks",
        body=(
            "For a loop at the end of the line: useful for snelled hooks, swivels and lures with a "
            "lot of action.",
            "Make a loop 1–2 in long and tie an overhand knot with it, without tightening.",
            "Pass the loop through the knot once more and tighten.",
            "To attach a hook, thread the loop through the eye and pass it over the hook.",
        ),
        source_ids=("pfbc-knots",),
    ),
    HandbookTopic(
        id="knot-joining",
        category="knots",
        title="Joining two lines: blood and surgeon's",
        body=(
            "Two ways to tie one piece of line to another, such as a leader to your main line.",
            "Blood: overlap them by about 2 in. Wrap the end of the first around the second five "
            "times and put that end between the two lines. Wrap the end of the second around the "
            "first five times, thread it through the same gap from the other side, and tighten.",
            "Surgeon's: lay them side by side, overlapping about 6 in. Tie an overhand knot with both, "
            "pull the loose ends through it again, hold the lines, and tighten.",
        ),
        source_ids=("pfbc-knots",),
    ),
    # ------------------------------------------------------------ ways to fish
    HandbookTopic(
        id="method-trolling",
        category="methods",
        title="Trolling",
        body=(
            "Pulling a lure or bait behind a moving boat, to cover water and find fish.",
            "Depth: pick a crankbait that dives to the depth you're fishing and touches the bottom "
            "now and then. Its lip size, your line's thickness, how much line is out and your speed "
            "all change how deep it runs. Lead core line, side planers and snap weights take it deeper.",
            "Speed: go slowly. Speeding up, slowing down or a sharp turn can trigger a strike. Kokanee "
            "are trolled at 0.8–1.5 mph and walleye at about 1 mph.",
            "Gear: for walleye, a 7–9 ft medium-heavy rod, a baitcasting reel and 10–12 lb "
            "monofilament or fluorocarbon.",
        ),
        source_ids=("nydec-walleye", "mndnr-crappie", "mndnr-walleye", "cdfw-kokanee"),
    ),
    HandbookTopic(
        id="method-ice",
        category="methods",
        title="Ice fishing",
        body=(
            "Check the ice first (see Ice safety), then fish through a hole. Trout, perch, crappie, "
            "bluegill, pike and walleye all bite in winter.",
            "What you need: a license, a short light rod, a bucket, and an auger or spud bar to make "
            "the hole. A 4–6 in hole is fine for panfish; trout and pike need a bigger one.",
            "How to fish: jig a small spoon up and down, often with bait on it, or set a tip-up, a "
            "spool on a stick that raises a flag when a fish pulls. Minnows and small fly larvae "
            "(spikes or mousies) are the usual baits.",
            "Where: pike, perch and sunfish in large shallow ponds; pike, walleye and lake trout in "
            "deep lakes. Trout and landlocked salmon are often just a few feet under the ice. "
            "Crappie hang in open water: start right under the ice and work down. A group of "
            "anglers or lots of old holes means fish were caught there.",
        ),
        source_ids=("nydec-ice", "wdfw-ice", "pfbc-ice", "nydec-crappie"),
    ),
    HandbookTopic(
        id="method-stream",
        category="methods",
        title="Reading a river or stream",
        body=(
            "Fish want a place to hide next to a place to feed. Where those two meet is the spot to try.",
            "Hiding places: undercut banks (often home to the biggest fish), sunken trees, rocks, "
            "eddies and deep water under overhanging trees.",
            "Feeding places: the outside of bends, where fast water carries food; seams, where two "
            "currents meet and the water slows; drop-offs; and where brooks and springs come in.",
            "Parts of a trout stream: a pocket is the calm spot behind a rock in fast water. A pool is "
            "slow and deep, and active fish are often at its head and tail. A run is where the flow "
            "narrows, deeper than a rapid and shallower than a pool.",
            "How to fish it: trout face upstream, so work your way upstream when you can, and move "
            "slowly. Polarized glasses help when wading. Below dams, take care: the water is swift and changes fast.",
        ),
        source_ids=("nydec-rivers", "nydec-trout", "nydec-walleye"),
    ),
    HandbookTopic(
        id="method-fly",
        category="methods",
        title="Fly fishing basics",
        body=(
            "The line's weight carries the cast, so rods are rated by line weight. Rods are "
            "commonly 7½–9 ft, and a 4, 5 or 6 weight suits trout-sized flies.",
            "Dry flies float and look like adult insects: cast upstream and let the fly pass over feeding fish.",
            "Nymphs look like young insects and tumble along the bottom. A strike indicator on the "
            "leader sets the depth, and a split shot sinks it.",
            "Streamers look like small fish: cast and work one back toward you, or let the current "
            "swing it on a tight line.",
        ),
        source_ids=("pfbc-fly",),
    ),
    HandbookTopic(
        id="method-night",
        category="methods",
        title="Fishing at dusk and after dark",
        body=(
            "Channel catfish feed mainly at night: fish riffles and shallows with a nightcrawler, "
            "chicken liver, cut minnow or stink bait.",
            "Walleye feed more actively in low light, just before and after sunset.",
            "Crappie have large eyes and can feed after dark. Bass take surface lures toward dark.",
            "Bluegill and northern pike hunt by sight and bite little at night, so fish them by day.",
        ),
        source_ids=("mn-ccf", "nydec-walleye", "nydec-crappie", "mndnr-lmb", "mndnr-sunfish", "mndnr-pike"),
    ),
    HandbookTopic(
        id="method-kayak",
        category="methods",
        title="Fishing from a kayak or small boat",
        body=(
            "Have a life jacket for everyone aboard. Some states require wearing it in the cold "
            "months: Pennsylvania does from Nov. 1 to April 30 in kayaks, canoes and boats under 16 ft.",
            "Leave a float plan: tell someone where you're going and when you'll be back.",
            "After dark, carry a white light you can show in time to avoid a collision. Bring a "
            "sound device, a change of clothes in a dry bag, and sun protection.",
            "Many states require a registration or launch permit even for a kayak: check yours.",
        ),
        source_ids=("pfbc-kayak",),
    ),
    # --------------------------------------------------------- through the year
    HandbookTopic(
        id="timing-through-year",
        category="timing",
        title="Where fish go through the year",
        body=(
            "Spring: fish come shallow to spawn. Backwaters and protected bays warm first, so crappie "
            "and bass show up there, in under 8 ft. Walleye crowd near shore, often on sand flats.",
            "Summer: on hot days, go deeper and cooler. Larger sunfish go to 10 ft and deeper, "
            "crappie hang over open water, and walleye move to mid-lake humps and points. Bass fishing "
            "is often best with the water at 60–75°F.",
            "Fall: as the water cools, fish come back toward shore, with walleye following shad. "
            "Shallow weedbeds and midday can be good.",
            "Winter: most fish go deep. Channel catfish look for deep water out of the current.",
            "Trout need cold water: don't fish for them when streams warm in summer. Brook trout "
            "prefer water under 72°F and brown trout under about 70°F.",
        ),
        source_ids=(
            "nydec-crappie", "nydec-bass", "nydec-walleye", "nydec-trout", "mndnr-lmb", "mndnr-crappie",
            "mndnr-sunfish", "mndnr-walleye", "mn-ccf", "mdc-brown-trout",
        ),
    ),
    HandbookTopic(
        id="timing-spawn-north",
        category="timing",
        title="Spawning temperatures of northern fish",
        body=(
            "Yellow perch spawn first, right after ice-out at 45–52°F, and walleye soon after, once "
            "the water passes 46°F. Northern pike go even earlier, sometimes under the ice.",
            "Sunfish in Minnesota begin at about 60°F, and bass build nests from about 60°F in 2–8 ft of water.",
            "Crappie spawn when the water reaches the high 60s. Bullheads spawn at 70–77°F and channel catfish at 75°F.",
        ),
        source_ids=("widnr-perch", "mdc-walleye", "mndnr-pike", "mndnr-sunfish", "mndnr-lmb", "nydec-crappie", "widnr-bullhead", "mn-ccf"),
    ),
    # -------------------------------------------------------- every state's
    HandbookTopic(
        id="rule-clean-drain-dry-us",
        category="rules",
        title="Clean, drain and dry: stop invasive species",
        body=(
            "Leaving any water, you can carry zebra mussels and other invasive species to the next one. "
            "Some states make these steps law.",
            "Clean: take plants, animals and mud off the boat, trailer and gear before you leave the "
            "access. Rinse with hot water where you can, and flush the motor with 120°F water for 2 "
            "minutes, or as its manual says. Bleach and other chemicals aren't recommended.",
            "Drain: empty the motor, bilge, livewell and anything else that holds water before you leave.",
            "Dry: let everything dry for at least five days, or wipe it with a towel, before using it elsewhere.",
            "Bait: put unwanted bait in the trash, and never release live fish, bait or plants into any "
            "water. Refill a bait container with spring water or dechlorinated tap water, not lake water.",
        ),
        source_ids=("usfws-cdd", "sah-prevention"),
    ),
    HandbookTopic(
        id="rule-clean-drain-dry-mn",
        category="rules",
        title="Clean, drain and dry (Minnesota)",
        body=(
            "In Minnesota these are law: clean plants and invasive animals off boats, trailers and gear; "
            "drain all water, bait containers and livewells included, before leaving the water; and "
            "keep drain plugs out while transporting.",
            "Unwanted bait goes in the trash, and bait, plants and pet fish may never be released.",
            "Docks, lifts and rafts must dry for 21 days before going into another water. Drying "
            "boats and gear for five days is recommended.",
            "Taking fish, frogs or crayfish for bait from infested waters is mostly prohibited, and live "
            "crayfish may be used as bait only in the water where they were taken.",
        ),
        source_ids=("mndnr-ais", "mndnr-ais-laws"),
        region="MN",
    ),
    HandbookTopic(
        id="care-advisories",
        category="care",
        title="Fish advisories: is this water's fish safe to eat?",
        body=(
            "All 50 states, and some territories and tribes, issue advice on fish from local waters, "
            "because of mercury, PFAS, PCBs and DDT.",
            "Take most care if you're pregnant or may be, are breastfeeding, or feed children. Mercury "
            "can harm a developing nervous system. Older adults, people with weak immune systems and "
            "anyone who eats a lot of fish should check too.",
            "To find yours: look for signs at the water's edge. If there are none, ask your state's "
            "health or environmental agency; the EPA lists them all.",
            "Avoid mussels and clams collected during or right after a harmful algal bloom.",
        ),
        source_ids=("epa-fish", "epa-fish-concern", "epa-fish-contacts"),
    ),
    # ------------------------------------------------------------- ice safety
    HandbookTopic(
        id="safe-ice",
        category="safety",
        title="Ice safety: how thick is safe",
        body=(
            "No ice is ever guaranteed safe, and state agencies don't check it for you. Ask locally, "
            "and test it with holes as you walk out from shore.",
            "How thick the ice must be, for new, clear ice: stay off anything under 4 in. Four inches is the least for fishing on "
            "foot; Pennsylvania's chart asks for 5 in. Cars and trucks need far more, and the "
            "agencies' tables differ, so follow your state's.",
            "White ice is about half as strong as clear ice, so double the numbers. Slush ice is also "
            "about half as strong, and ice over moving water is weaker: stay off rivers and away from "
            "where streams enter or leave.",
            "Never go alone. Carry ice picks and a rope, wear a life jacket, dress in layers without "
            "cotton, add boot cleats, and spread out rather than crowding one spot.",
        ),
        source_ids=("nydec-ice", "mndnr-ice", "wdfw-ice", "pfbc-ice"),
    ),

    # ------------------------------------------- added 2026-11-06: cold water
    HandbookTopic(
        id="id-steelhead-rainbow",
        category="identify",
        title="Steelhead or rainbow trout?",
        body=(
            "They are the same species. A rainbow trout that stays in fresh water all its life is "
            "a rainbow trout; one that goes out to the ocean, or to one of the Great Lakes, and comes "
            "back up a river to spawn is a steelhead.",
            "A steelhead is bigger (some reach 30 lb and 40 in; NOAA), and silvery when it has just "
            "come in from the lake or sea. Anglers call a bright one a chromer. The longer it stays "
            "in the river, the darker it turns and the more it looks like a stream rainbow, with the "
            "pink stripe along its side.",
            "Unlike Pacific salmon, a steelhead doesn't have to die after spawning: many go back to "
            "the lake or sea and return another year.",
            "Same species, same guide: the rainbow trout guide applies, but a state may have its own "
            "steelhead rules, seasons or stamp. Check before you keep one.",
        ),
        source_ids=("noaa-steelhead", "mndnr-trout", "nydec-steelhead"),
    ),
    HandbookTopic(
        id="id-salmon",
        category="identify",
        title="Chinook, coho or pink salmon?",
        body=(
            "Look in its mouth. A Chinook (king) salmon has black gums along the lower jaw, which is "
            "why it is also called blackmouth. A coho (silver) salmon's gums are lighter.",
            "Look at the tail. A Chinook has black spots on both halves of its tail; a coho has "
            "small spots on the upper half only.",
            "Size: Chinook are the biggest Pacific salmon (commonly around 30 lb at sea; in Lake "
            "Superior most are 3–4 lb). Coho run 8–12 lb at sea, about 1.5–3 lb in Lake Superior. "
            "Pink salmon are the smallest, about a pound in Lake Superior; a spawning male grows a "
            "big hump on its back, so anglers call them humpies.",
            "Colour changes: fresh from the lake or sea they are silver with a dark blue-green back. "
            "As they move upriver to spawn they turn olive, red or maroon, and the males grow a "
            "hooked jaw. Chinook, coho and pink salmon all die after spawning.",
        ),
        source_ids=("noaa-chinook", "noaa-coho", "mndnr-salmon"),
    ),
    HandbookTopic(
        id="id-whitefish-cisco",
        category="identify",
        title="Lake whitefish, cisco or burbot?",
        body=(
            "Whitefish and cisco are trout-shaped, silver, with a small fleshy fin (the adipose fin) "
            "near the tail. Ice anglers catch cisco often and whitefish less.",
            "Tell them apart by the snout: a whitefish's snout hangs over its lower jaw, while a "
            "cisco's lower jaw reaches the tip of its snout or past it. Whitefish grow bigger.",
            "Cisco go by several names: tullibee, lake herring or just herring are the same fish.",
            "A burbot (eelpout) is something else entirely: a long, smooth, slimy fish with one "
            "whisker under its chin, like a cross between an eel and a catfish. It is a freshwater "
            "cousin of the cod, and it bites in winter.",
        ),
        source_ids=("mndnr-whitefish", "mndnr-cisco", "mndnr-burbot"),
    ),
    HandbookTopic(
        id="timing-runs",
        category="timing",
        title="When salmon and steelhead run",
        body=(
            "Salmon and steelhead feed in a big lake (or the ocean), then swim up rivers to spawn. "
            "The run is when river anglers catch them.",
            "Fall: Chinook, coho and pink salmon, and brown and brook trout, run from about "
            "September until the rivers freeze (on Minnesota's North Shore). They die after spawning.",
            "Steelhead come in two waves on many Great Lakes rivers. Some enter in fall (in New York "
            "from mid-September; late October and November is often the best time, when they feed "
            "hard) and spend the winter in deep pools. They spawn in spring, from about March to "
            "April, then drop back to the lake, feeding heavily as they go.",
            "New fish move up on rising or falling water after rain, and in brief winter warm-ups; "
            "in very low or flooding water they hold where they are.",
        ),
        source_ids=("mndnr-sup-report", "mndnr-northshore", "nydec-steelhead"),
    ),
    HandbookTopic(
        id="method-steelhead",
        category="methods",
        title="Fishing a river for steelhead",
        body=(
            "Where they hold: where two currents meet (a seam); just above or below a boulder or log "
            "that breaks the current; and at the head and tail of a big pool. They dislike bright "
            "light, so on sunny days fish early and late.",
            "What they bite: things they eat in the river, fish eggs above all. Salmon eggs tied in "
            "a dime-sized mesh sack (a spawn sac) are the favourite natural bait; artificial eggs, "
            "small beads, little plastic worms, egg and nymph flies and streamers all work too.",
            "Drift fishing: let the bait roll along just off the bottom, a little slower than the "
            "current, with just enough split shot that you feel it tick the bottom now and then. "
            "Any pause, tug or upstream movement of the line can be a bite.",
            "Float fishing: a float (bobber) lets the bait drift a long way without snagging. Use "
            "enough split shot to sink about three quarters of the float, heaviest shot highest, so "
            "the bait drifts ahead of the float.",
            "Gear: a long spinning rod (8–10 ft, light to medium, for 6–12 lb line) keeps line off "
            "the water and feels the soft bite. When one is hooked, don't try to stop its first run: "
            "hold the rod up and let the drag work. Wading in winter is risky: wear studded boots "
            "and a life jacket, and fish with a friend.",
        ),
        source_ids=("nydec-steelhead",),
    ),
    HandbookTopic(
        id="method-great-lakes-trolling",
        category="methods",
        title="Trolling the Great Lakes for salmon and trout",
        body=(
            "Usual lures: spoons, long thin crankbaits (stickbaits) and a dodger with a fly behind "
            "it. Keep changing the lure, colour, depth and speed until something works, then stay "
            "with it.",
            "Getting lures out and down: planer boards carry lines out to the side, at least 100 ft "
            "behind the boat; weighted lines run 200 ft or more back; downriggers take a lure down "
            "deep and hold it there.",
            "Where in the year: from December to May trout and salmon are often close to shore in "
            "water under 30 ft. In late spring and summer, head offshore over 75–200 ft of water. "
            "Salmon and brown and rainbow trout swim nearer the surface than lake trout, which go "
            "deep (often below 90 ft) as the surface warms.",
            "Gear on Lake Superior: an 8 ft medium to medium-heavy trolling rod, a baitcasting reel "
            "with a line counter so you can repeat the depth that caught a fish, 30 lb or heavier "
            "braid and a 6 ft monofilament leader.",
        ),
        source_ids=("mndnr-sup-trolling",),
    ),
    HandbookTopic(
        id="method-lake-trout",
        category="methods",
        title="Catching lake trout",
        body=(
            "Lake trout need cold, clean, deep water that stays under about 65°F all summer, and "
            "plenty of fish to eat, ciscoes above all. They are slow growing: five to seven years "
            "to reach a size worth catching, and they can live 40 years.",
            "Where: through the ice, start in 30–40 ft and move out to 90–100 ft. Try points, reefs, "
            "islands, the mouths of bays and slowly dropping shorelines next to deep water. They "
            "roam open water after schools of cisco or smelt, so follow the bait fish.",
            "Jigging: they chase prey down and pin it on the bottom (or up against the ice), so "
            "work the whole depth, and expect bites as the lure falls. Silver or white lures work: "
            "jigging spoons, tube jigs, blade baits and swimbaits; a bit of sucker or chub meat on "
            "the hook adds scent.",
            "Tip-ups: a sucker or shiner hooked between the back fin and tail, on 10–20 lb line, "
            "set along the 40 to 60 ft contour or down a point at several depths. Check the bait "
            "about every half hour, and stay close to your tip-ups.",
        ),
        source_ids=("mndnr-laketrout-ice", "mndnr-sup-trolling"),
    ),
    HandbookTopic(
        id="method-sturgeon",
        category="methods",
        title="Catching a lake sturgeon",
        body=(
            "Lake sturgeon are ancient fish with a skeleton of cartilage, rows of bony plates instead "
            "of scales and whiskers under a flat snout. In Minnesota they pass 100 lb, and a female "
            "can live over 150 years; they take decades to mature, which is why the rules on them "
            "are strict.",
            "How: anchor just above a deep hole or seam in a big river and let bait sit on the "
            "bottom. Nightcrawlers, often with a minnow or two, on a large circle hook below a "
            "sliding sinker, swivel and short leader. Heavy tackle: a stout rod and braided line.",
            "When the line tightens, take up the slack and lift the rod to set the hook. The fight "
            "can last ten minutes or more.",
            "Handle with care: keep it in the water as much as you can, support its body level "
            "for a photo, and never touch the eyes or gills. Sturgeon seasons, tags and catch rules "
            "are tightly set and differ by water: read your state's rules before you go.",
        ),
        source_ids=("mndnr-sturgeon",),
    ),
    HandbookTopic(
        id="method-ice-perch",
        category="methods",
        title="Ice fishing for yellow perch",
        body=(
            "Yellow perch look like a small walleye, yellow with six or seven dark bars, and they "
            "bite worms eagerly. Many are small; a big one is a prize.",
            "Where through the winter: early on, in shallow water near green weeds. As winter goes "
            "on they move to deeper water, drop-offs and structure, and in spring back to the "
            "shallows to spawn. Fish just above the weed tops or along weed edges; a fish finder or "
            "underwater camera shows where they are.",
            "Bait and lures: wax worms, mealworms or other small larvae, on tiny jigs, flies or "
            "spoons (1/64 to 1/16 oz) and 2–4 lb line. Tungsten jigs sink faster than lead.",
            "Jig gently: too much movement scares perch off. Watch for the rod tip to twitch or the "
            "line to go slack, or use a slip bobber set to the depth. The best bites come near dawn "
            "and dusk.",
        ),
        source_ids=("mndnr-perch-ice",),
    ),
    HandbookTopic(
        id="method-stream-trout-bait",
        category="methods",
        title="Drifting bait for stream trout",
        body=(
            "Trout face into the current waiting for food to come to them, so the bait should come "
            "down the stream the way real food does.",
            "Walk up to the pool quietly from below. Cast upstream and let half a nightcrawler, "
            "hooked once near each end, drift back toward you on the current. Watch the floating line "
            "for a stop or twitch.",
            "Light gear: a short ultralight spinning rod with 4–6 lb line, small hooks (sizes 10–14) "
            "and just enough small split shot to get down in fast water.",
            "Where each trout lives: brown trout hide in the deepest pools under cover (undercut "
            "banks, fallen trees) and come into riffles to feed early and late; brook trout like "
            "small, clean, spring-fed streams; rainbows hold in faster, bigger water.",
            "Spinners work too. A common start: gold for browns, silver for rainbows, copper for "
            "brook trout. If your shadow falls on the pool, the trout may hide for an hour or two: "
            "move on.",
        ),
        source_ids=("mndnr-se-trout",),
    ),
    HandbookTopic(
        id="cond-thermocline",
        category="conditions",
        title="Summer layers: why fish go to a certain depth",
        body=(
            "From late spring, many lakes deeper than about 10 ft split into layers: warm water on "
            "top, cold water underneath, and between them a band where the temperature drops fast, "
            "the thermocline. The layers don't mix.",
            "The cold bottom water gets no fresh oxygen from the surface, and by midsummer there is "
            "too little down there for fish to stay. So fish hold in the warm layer, as close to "
            "the thermocline as they can, where it is cooler but still has oxygen.",
            "How deep: it depends on how clear the water is, about 5 ft in a murky lake and 16 ft or "
            "more in a clear one. A good depth finder often shows it as a fuzzy line; that line is "
            "the depth to fish.",
            "In fall the surface cools, the lake turns over and mixes, and fish can be at any depth "
            "again, usually from late September to mid-October.",
        ),
        source_ids=("iowadnr-thermocline",),
    ),
    HandbookTopic(
        id="bait-why-it-works",
        category="baits",
        title="Why bait works: how fish find food",
        body=(
            "Most fish hunt by sight, which is why many feed best in daylight and why a lure that "
            "flashes or moves like a small fish works.",
            "Bottom feeders such as catfish, sturgeon and suckers rely on smell, taste and touch "
            "instead. A catfish has taste buds all over its skin, so it can find food it can't see. "
            "These fish search the area the scent has spread through, which is why smelly baits "
            "(cut bait, worms, stink bait) catch them, and why a bait left in one spot for a while "
            "works better than one moved often.",
            "Fish also feel the water. The lateral line, the row of pores along each side, picks up "
            "slow vibrations such as something splashing into the water or struggling. A lure that "
            "wobbles, rattles or thumps sends those vibrations.",
            "Putting it together: in clear water and bright light, natural colours and lifelike "
            "movement matter; in murky water or at night, use bait with scent, or a lure that makes "
            "noise and vibration.",
        ),
        source_ids=("usbf-lateral-line",),
    ),
)

# Added 2026-11-08: what beginners ask that the handbook didn't answer, found
# by putting 177 beginner questions to Ask (bites, landing, no bites, bait
# thieves, snags, line twist, manners, kids, lightning, heat, cold water).
TOPICS += (
    HandbookTopic(
        id="technique-bite",
        category="technique",
        title="Is it a bite? Setting the hook",
        body=(
            "A bite looks different from fish to fish. A bobber can twitch, slide across the surface "
            "or plunge under; a stick bobber may lie flat or ride higher when a fish swims up with "
            "the bait. When the bobber goes under, a fish has the bait: reel up the slack and set "
            "the hook.",
            "Fishing on the bottom, watch for the rod tip to dip or shiver, or the line to go slack "
            "all at once. In your hand you may feel a tap, a tug or a steady pull; with a lure, any "
            "bump, or the line moving off sideways, can be a fish.",
            "Hold the rod firmly enough that a strike can't pull it away, but lightly enough to feel "
            "a small tug. After a few casts you learn to tell a fish from the wind or current pulling "
            "on the line.",
            "Before any bite: after the cast, turn the handle until the reel clicks into gear, then "
            "reel in loose line until the bobber just starts to move. Slack line misses fish.",
            "To set a J hook or a lure's hooks, reel up the slack, then sweep the rod up and back, "
            "quick and firm. Pulled through slack or a loop in the line, the hook won't go in and the "
            "fish lets go of the bait.",
            "How hard depends on the fish. Trout and panfish have small, soft mouths, and too hard a "
            "jerk can break light line; under a bobber, a lift just strong enough to move the bobber "
            "is plenty. Big fish and big hooks need more force.",
            "A circle hook is different: don't jerk. Start reeling, or pull back steadily, and it "
            "sets itself (see How to use a circle hook).",
            "Set the hook soon after the bite: given time, a fish swallows the bait, which is hard "
            "on one you mean to release.",
        ),
        source_ids=("mdc-tips", "utah-learn", "usfws-tips", "nydec-basics", "tpwd-cr", "nydec-guide"),
    ),
    HandbookTopic(
        id="technique-landing",
        category="technique",
        title="Playing a fish and landing it, with a net or by hand",
        body=(
            "Once the fish is on, keep the line tight and the rod tip up, with a bend in it: the "
            "rod is your shock absorber. A fish comes off easily when the line goes slack: it throws "
            "or wiggles out of the hook. Some swim straight at you, so keep reeling until you feel "
            "the weight again.",
            "When the fish pulls line off the reel, that is the drag doing its job. Stop turning "
            "the handle until the run ends, then reel again: reeling while the drag slips only "
            "twists the line. Resist tightening the drag in the middle of the fight (see Setting "
            "the drag).",
            "To gain line on a bigger fish, pump it: raise the rod to draw the fish in, then reel as "
            "you lower the tip. Use the rod's angle to lead the fish away from weeds, logs and dock "
            "posts.",
            "Fish often come off at the last moment, with a final lunge close to you. With a big "
            "fish, ease the drag slightly as it comes near.",
            "Getting it out of the water: a landing net lands more fish. Grabbing a fish by hand or "
            "dragging it up the bank is when the line breaks or the hook pulls out. Put the net in "
            "the water, lead the fish in head first, and lift as soon as it is over the bag. A "
            "shallow net of fine mesh is easiest on a fish you'll release.",
            "Do you need a landing net? For panfish it's optional; for trout, bring one.",
            "No net: tire the fish, then lift it with your hand. Bass, crappie and small catfish can "
            "be held by the lower lip, thumb inside. Walleye, pike, gar and big trout have sharp "
            "teeth: hold them over the back of the head instead (see Handling a fish without "
            "getting hurt).",
            "Don't play a fish until it is exhausted, above all in warm water: water of 70°F and "
            "warmer is hard on trout and other coldwater fish.",
        ),
        source_ids=("utah-learn", "mdc-tips", "mdc-rigging", "pfbc-start", "mdc-gear", "nydec-basics"),
    ),
    HandbookTopic(
        id="care-deep-hook",
        category="care",
        title="Swallowed the hook? Cut the line",
        body=(
            "A fish hooked deep, in the throat or the gut, is hurt more by digging for the hook than "
            "by leaving it. Cut the line as close to the mouth as you can and let the fish go with "
            "the hook in.",
            "A hook in the lip comes out the way it went in: hold the shank with pliers, turn the "
            "hook upside down and back it out, ideally with the fish in the water.",
            "Pinching down a hook's barb with pliers makes it quicker to take out, and kinder if it "
            "ever ends up in your own skin; you will lose a few more fish.",
            "Set the hook soon after the bite and fewer fish swallow it (see Is it a bite?).",
        ),
        source_ids=("pfbc-start", "nydec-basics", "utah-learn", "tpwd-cr"),
    ),
    HandbookTopic(
        id="trouble-no-bites",
        category="trouble",
        title="No bites, nothing caught? What to change",
        body=(
            "Hours without a bite happen to every angler: even the best spot has quiet spells, so "
            "give one some time. On water you don't know, though, it usually pays to move and look "
            "for fish rather than wait.",
            "Be quiet. Jumping, running or banging gear on a dock, the bank or a boat scares fish or "
            "stops them feeding; talking is fine. Keep your shadow off the water you're fishing.",
            "The bigger the fish, the warier it is. You can get closer when it's overcast or windy, "
            "and in moving water; for stream trout, wear dull colours and stay low.",
            "Cast past the spot you think holds fish and bring the bait into it, rather than "
            "landing it on top of them.",
            "Fish where fish hold: around docks, rocks and fallen trees, weed edges and drop-offs "
            "(see Cover and Points, drop-offs and inlets).",
            "Change the depth. Under a bobber, the bait should hang just above the weeds, logs or "
            "bottom; for why fish sit deeper in summer, see Summer layers.",
            "Go lighter. Use the smallest bobber that holds the bait up and can still be seen, with "
            "just enough split shot that a fish can pull it under easily; on a calm pond, one or two "
            "split shot hold bait on the bottom. A light rig alarms a fish less when it tries the "
            "bait.",
            "Try another time of day (see Best time of day).",
        ),
        source_ids=("mdc-tips", "mdc-rigging", "mdc-beginners", "nydec-basics", "usfws-tips"),
    ),
    HandbookTopic(
        id="trouble-stolen-bait",
        category="trouble",
        title="Bites, but nothing on the hook",
        body=(
            "If the bait keeps disappearing and nothing gets hooked, change one thing at a time.",
            "A smaller hook: a long-shanked No. 6 or 8 is the size to try for panfish.",
            "Less bait, threaded on: use a piece of nightcrawler rather than a whole one, run the "
            "hook through it more than once, and on a small hook push the point into the end, so "
            "little hangs free to be pulled off (see Worms and nightcrawlers).",
            "A lighter rig: a small bobber with only enough split shot under it lets a fish pull it "
            "down without feeling much.",
            "Set the hook sooner, with the slack reeled up first (see Is it a bite?).",
            "Baits that stay on: worms hold on the hook well, and so do the biodegradable baits made "
            "from natural ingredients.",
        ),
        source_ids=("nydec-basics", "mdc-rigging", "tamu-hook-bait", "nydec-kids"),
    ),
    HandbookTopic(
        id="trouble-snags",
        category="trouble",
        title="Snagged: freeing a hook, and snagging less",
        body=(
            "Rocks, sticks, logs, weeds, docks and cables catch every angler's hook sometimes. Snags "
            "are part of fishing.",
            "First, hold the rod tip high and jiggle it. Moving a few steps to one side, to pull "
            "from another angle, often frees it.",
            "If it won't come, don't heave on the rod: it can snap before the line does. Wrap the "
            "line several times around your hand, over a sleeve or a glove, point the rod tip "
            "straight at the snag, and pull steadily or walk backwards until the line breaks or the "
            "hook comes free. Turn your face away and keep others back: a hook that pulls free can "
            "fly at you.",
            "Then check the hook: replace it if it is bent or broken, and cut off and retie any line "
            "that is frayed near it.",
            "To snag less: a bobber keeps the bait up off the bottom; a hook point buried in a soft "
            "plastic slides through cover (see Texas rig); and a leader a little weaker than the "
            "main line breaks first, so a snag costs only the hook (see Leaders and swivels).",
            "Take broken line home: hooks and line left behind harm people and wildlife (see Old "
            "fishing line).",
        ),
        source_ids=("mdc-tips", "nydec-kids", "usfws-tips", "mndnr-minnaqua-safety"),
    ),
    HandbookTopic(
        id="trouble-line-twist",
        category="trouble",
        title="Line twist, loops and tangles on a spinning reel",
        body=(
            "Twisted line comes off a reel in loops that tangle. These habits stop it starting.",
            "Filling the reel: follow the directions that come with the reel and the line; most line "
            "packages say how to put it on without twist. Thread the line under the bail or through "
            "the cap, tie it to the spool (see Arbor knot) and reel it on.",
            "Don't overfill: stop when the line is about 1/16 to 1/8 in below the spool's rim.",
            "When a fish is pulling line off against the drag, don't turn the handle: every turn "
            "twists the line. Wait until the run stops.",
            "Reel in with a little tension on the line, letting it run between your thumb and "
            "finger, and after each cast turn the handle until the reel clicks, so loose line "
            "doesn't pile on the spool.",
            "Keep knots out of the line except at the end: they weaken it and spoil the cast.",
            "If it still twists, it's time for new line (see Changing your fishing line).",
        ),
        source_ids=("mdc-rigging", "nydec-basics", "nydec-guide"),
    ),
    HandbookTopic(
        id="rule-manners",
        category="rules",
        title="Sharing the water: manners on the bank",
        body=(
            "Give other anglers room. Don't wade or cast in front of someone, leave space for their "
            "back cast, and don't cast close to other people.",
            "Look behind you before every cast, for people and for trees.",
            "Keep it quiet: no loud music or shouting, and don't toss stones into the water or "
            "splash about, which spoils everyone's fishing.",
            "Let anglers with disabilities have the places built for them.",
            "Fishing private water takes the owner's permission. Ask before crossing private land, "
            "and don't trespass.",
            "Take your trash home, bait cups, fishing line and cigarette butts included, and keep to "
            "trails and parking areas.",
            "Before moving to other water, clean mud, plants and water off boots, boats and tackle, "
            "and don't move fish from one water to another (see Clean, drain and dry).",
        ),
        source_ids=("mdc-ethics", "usfws-tips", "nydec-basics", "mdc-beginners"),
    ),
    HandbookTopic(
        id="method-kids",
        category="methods",
        title="Taking kids fishing",
        body=(
            "Make the trip about the child, not your own fishing: lines will tangle and hooks need "
            "baiting. Keep a rod they can use for yourself, hand it over when theirs needs fixing, "
            "or hook a fish and let them reel it in.",
            "Keep it short: an hour, maybe two, is plenty for most children. Stop while it's still "
            "fun.",
            "The easiest setup for a child: a push-button (spincast) reel on a short rod, with a "
            "hook, a split shot and a bobber, catches most fish. The reel's closed cover keeps "
            "tangles to a minimum. A child can see the bobber go down, and it keeps the bait off the "
            "bottom, so there are fewer snags.",
            "Bait: worms stay on the hook, most fish eat them, and they survive being handled. "
            "Biodegradable baits made from natural ingredients need no care and stay on well too.",
            "Bring snacks, drinks, hats, sunglasses, sunscreen, bug spray and spare clothes. A small "
            "net for catching insects and tadpoles, let go afterwards, fills the time between bites.",
            "Let them help decide: point out two spots and ask which looks better.",
            "On or near deep water a child needs a life jacket that fits now, not one to grow into "
            "(see Life jackets).",
        ),
        source_ids=("nydec-kids", "usfws-tips", "mdc-beginners", "utah-learn", "tpwd-lifejacket"),
    ),
    HandbookTopic(
        id="safe-lightning",
        category="safety",
        title="Lightning and thunderstorms",
        body=(
            "Check the forecast before you go, and put the trip off if thunderstorms are likely.",
            "If you can hear thunder, you are close enough to be struck: get out of and away from "
            "the water. In a boat or a kayak, head for land and shelter at once.",
            "Shelter means a solid, enclosed building or a car or truck with a hard top. A small "
            "shed, a lone tree, a convertible or a rock overhang is not shelter.",
            "Caught with no shelter, keep away from tall objects and lone trees, and get down off "
            "hills and ridges.",
            "Wait 30 minutes after the last thunder before going back out.",
        ),
        source_ids=("nws-lightning",),
    ),
    HandbookTopic(
        id="safe-heat",
        category="safety",
        title="Heat: cramps, exhaustion and heat stroke",
        body=(
            "In hot, humid weather the body can't cool itself fast enough, above all when it loses "
            "water and salt through sweat.",
            "Heat cramps: painful cramps in the legs or belly, with heavy sweating. Press or gently "
            "rub the muscle and sip water, unless the person feels sick; get medical help if the "
            "cramps last over an hour.",
            "Heat exhaustion: heavy sweating, weakness, cool, pale and clammy skin, a fast weak "
            "pulse, dizziness, nausea, headache or fainting. Move somewhere cooler, loosen clothing, "
            "cool the skin with wet cloths and sip water; get medical help if the person vomits, or "
            "it gets worse or lasts over an hour.",
            "Heat stroke is an emergency: a throbbing headache, confusion, slurred speech, hot red "
            "skin, a body temperature above 103°F, fainting. Call 911, move the person somewhere "
            "cooler and cool them with wet cloths or a cool bath. Give no fluids.",
        ),
        source_ids=("nws-heat",),
    ),
    HandbookTopic(
        id="safe-cold-water",
        category="safety",
        title="Falling into cold water",
        body=(
            "Cold water is dangerous long before it feels icy. A sudden plunge can make you gasp in "
            "water as warm as 77°F, and water of 50–60°F can shock the body as badly as near-"
            "freezing water. Warm air doesn't mean warm water.",
            "For the first 2–3 minutes, cold shock brings gasping and fast breathing, which can "
            "draw in water, and a jump in heart rate and blood pressure. Then arms and legs weaken "
            "until you can't swim or hold on.",
            "A life jacket keeps you afloat through it: wear one on the water, and when fishing from "
            "slippery rocks and docks (see Life jackets).",
            "If you fall in, stay calm, keep your head up and get out as soon as you can. Then get "
            "warm and dry fast: body temperature keeps falling after you're out, and hypothermia "
            "begins when it drops to 95°F.",
            "Before going out on cold water, dress for how cold the water is, not the air, check "
            "the forecast and the water before you go, and tell someone where you're going and when "
            "you'll be back.",
        ),
        source_ids=("nws-coldwater",),
    ),
)

# Added 2026-11-08 from state fishing-education booklets (PDFs read for facts
# only; docs/data-sources.md): gear care, new line, push-button reel trouble,
# hook injuries, black spots, lead, trimming fillets, stocked trout.
TOPICS += (
    HandbookTopic(
        id="tackle-care",
        category="tackle",
        title="Looking after your rod, reel and tackle",
        body=(
            "A rod and reel last a long time with a little care. After each trip, look the rod "
            "over for cracked or loose guides (the rings the line runs through) and for damage to "
            "the reel seat and handle.",
            "Most rods are broken in car doors, trunk lids and tailgates, or by being stepped on: "
            "carry and store them where that can't happen. A broken tip can be replaced with a "
            "glue-on tip from a tackle shop.",
            "Wash a dirty rod with warm water and a little mild soap, rinse it, and let it dry "
            "before you put it away.",
            "Reels: clean and oil a reel at least once a year, more often if you fish a lot. Take "
            "it off the rod first and follow the maker's instructions, because each kind comes "
            "apart differently. Never spray a reel with a hose or pressure washer: it drives grit "
            "and water into the gears.",
            "Before you store a reel, back the drag off. A drag left tight flattens its washers and "
            "no longer works smoothly.",
            "After saltwater, rinse the rod, reel and lures gently with fresh water as soon as you can, "
            "without dunking them, and take the cover off a spincast reel to rinse inside. Let "
            "them air-dry, then give the reel a thin coat of a lubricant made for saltwater. One "
            "salty lure put back in the box can rust the rest.",
            "Leave the tackle box open until everything in it is dry: hooks, swivels and pliers "
            "rust when they're packed damp, and a silica gel packet helps. Keep different soft "
            "plastics in their own packets and out of the heat, or they can melt together.",
        ),
        source_ids=("tpwd-gear-care",),
    ),
    HandbookTopic(
        id="tackle-new-line",
        category="tackle",
        title="Changing your fishing line: how often, and putting new line on",
        body=(
            "All line wears out, braid too, even if it never breaks: sunlight weakens it, and old monofilament "
            "turns brittle. Replace your line every year.",
            "Change it sooner if it snaps easily while you tie a knot, if it comes off the reel in "
            "curls and twists again and again, or if the last few feet are nicked or rough.",
            "A reel sold already filled may have sat on a shelf for a long time, and the line "
            "comes off in coils the shape of the spool. Fresh line casts better.",
            "Which line: for most freshwater fishing, 6 to 10 lb monofilament; 4 to 8 lb for "
            "bluegill and perch, 8 to 12 lb for bass. Saltwater calls for 10 to 20 lb.",
            "Putting it on a spincast (closed-face) reel: unscrew the reel's cover and take the worn line off. "
            "Push the new line through the hole in the cover, tie it to the spool with an arbor "
            "knot, put the cover back and turn the handle. Let the line come straight off the new "
            "spool, held by a friend or lying on the floor, and keep a little tension on it with "
            "your fingers.",
            "Don't overfill: too much line is a main cause of reel trouble. A spincast reel is "
            "full at about 100 yards; on a spinning reel, fill to about ⅛ in below the rim (see Line "
            "twist).",
            "Thread the end through every guide, tie on your hook, and take the used line to a "
            "recycling bin (see Old fishing line).",
        ),
        source_ids=("tpwd-gear-care", "nydec-guide", "tpwd-tips-beginners"),
    ),
    HandbookTopic(
        id="trouble-spincast",
        category="trouble",
        title="Spincast reel won't cast or won't reel in",
        body=(
            "A push-button (spincast) reel hides the line under a cover, so when something goes "
            "wrong you can't see it. Most problems are one of these.",
            "The line won't go out: first look at the rod tip, where the line may be wrapped "
            "around it. If not, press and release the button and pull some line out by hand. If "
            "it feels rough and then suddenly runs freely, a loop was caught inside: pull "
            "line out until it runs smoothly, then reel it back in while pinching it lightly so "
            "it goes on tight.",
            "The button does nothing and no line comes out: unscrew the reel's cover. If the line "
            "is pulled tight around the small pin at the edge of the spool, the pin can't let go "
            "of it. Lift the line off the pin, untangle anything you find, and put the cover back.",
            "You turn the handle but the line doesn't come in: there is slack line on the reel. "
            "Pull the line tight, then reel.",
            "The handle came off: it was turned backwards. Put it back on and turn it the right "
            "way.",
            "Too much line on the reel causes many of these. If they keep happening, take some "
            "off or put on new line (see Changing your fishing line).",
        ),
        source_ids=("tpwd-gear-care", "nydec-guide"),
    ),
    HandbookTopic(
        id="safe-hook-injury",
        category="safety",
        title="Hooked yourself? A fish hook in your skin",
        body=(
            "Fish hooks are sharp and seldom clean. A hook stuck in a finger or a hand can get "
            "infected or cause tetanus, so wash it well and see a doctor about a tetanus shot.",
            "If the point went in but the barb did not, back the hook out gently the way it went "
            "in. Clean the wound, then put on antiseptic ointment and a bandage.",
            "If the barb is buried, or the hook is in the face or near an eye, don't pull it out "
            "yourself: that tears more tissue. Cover the hook, and any lure on it, with an "
            "upturned paper cup or tape so nothing knocks it, and go to an emergency clinic or "
            "hospital. In an emergency, call 911.",
            "A deep puncture should be seen by a doctor, even once the hook is out.",
            "Avoiding it: pinch the barbs down or use barbless hooks. Look behind you before every "
            "cast and keep at least a rod's length from the next angler. Walk, don't run, with a "
            "rod, and carry it upright with the hook fastened to a guide. A hat and sunglasses "
            "protect your head and eyes.",
        ),
        source_ids=("mndnr-minnaqua-safety", "tpwd-ae-guide", "nydec-guide"),
    ),
    HandbookTopic(
        id="care-black-spots",
        category="care",
        title="Black spots or dots in a fish fillet",
        body=(
            "Small black spots in a fillet, or under the skin, are a common parasite that gets "
            "into a fish's muscle and turns black.",
            "Cooking kills it. The fish is safe to eat once it is cooked through, and the spots "
            "don't change its flavor.",
            "Cook any fish you catch until the flesh is no longer see-through and flakes at the "
            "thickest part (145°F): undercooked fish can pass on parasites.",
        ),
        source_ids=("nydec-guide", "mndnr-minnaqua-eating", "foodsafety-temps"),
    ),
    HandbookTopic(
        id="tackle-lead",
        category="tackle",
        title="Lead sinkers and jigs, and wildlife",
        body=(
            "Most sinkers and jig heads are made of lead, and lead is poisonous. Ducks and other "
            "birds and small animals swallow lost sinkers while they feed, and can be poisoned "
            "and die.",
            "Wildlife agencies ask anglers to use sinkers and jigs that aren't lead, and tackle "
            "shops sell them (tungsten is one: see Sinkers).",
            "Some states restrict lead tackle; New York, for example, no longer allows small lead "
            "sinkers to be sold. Check your state's rules.",
            "Pinch split shot onto the line with pliers, never with your teeth.",
            "Use the smallest weight that does the job: the fish feels less of it, and you lose "
            "less.",
        ),
        source_ids=("nydec-guide", "mndnr-minnaqua-safety", "tpwd-tips-beginners"),
    ),
    HandbookTopic(
        id="clean-trim-fillet",
        category="care",
        title="Trimming a fillet: the dark strip and the fat",
        body=(
            "Many fillets have a dark strip along the skin side: a blood vessel running to the "
            "tail, with fat around it. Cut a shallow V along each side of it and lift it out.",
            "Trim off the fat along the back and the belly flap, and take the skin off.",
            "Some chemicals, such as PCBs, collect in a fish's fat, so skinning and trimming "
            "lowers how much of them you eat. Grilling, broiling or baking the fish helps too.",
            "Rinse the fillets, pat them dry, and keep them on ice or in the fridge until you cook or "
            "freeze them (see Freezing your catch). Check your state's advisories before eating "
            "fish from a lake (see Fish advisories).",
        ),
        source_ids=("mndnr-minnaqua-eating", "nydec-guide"),
    ),
    HandbookTopic(
        id="method-stocked-trout",
        category="methods",
        title="Catching stocked rainbow trout",
        body=(
            "Hatchery trout stocked in ponds and city lakes grew up eating food pellets. In Texas "
            "they are stocked in winter, because the water is too warm for them in summer, and "
            "they average 10 to 12 inches.",
            "Gear: a light or ultralight rod of 5 to 6½ ft with a push-button or spinning reel, "
            "and 4 to 10 lb line; 6 to 8 lb is a good middle. Trout see well in clear water, so "
            "keep the rig small, without big snaps, swivels, wire or heavy weights.",
            "Bait: kernel corn, cheese balls, salmon eggs, pieces of nightcrawler, mealworms, "
            "crickets, and scented dough or floating trout bait. Floating dough baits work "
            "especially well on fresh-stocked fish, which are used to pellets.",
            "A simple bottom rig: slide a small egg or bullet sinker (about ⅛ oz) onto the main "
            "line, tie on a swivel, then 18 to 24 in of 4 lb leader and a No. 6 or 8 hook. Mold "
            "enough floating bait onto the hook to lift it off the bottom.",
            "Or hang the bait under a small bobber, with the smallest split shot that sinks it, "
            "set a little way above the hook. Long-shank hooks from No. 4 to 8 work, and are easy "
            "to take out.",
            "Lures: small inline spinners, spoons, curly-tail jigs and tiny crankbaits.",
            "Cast and let it sit. No bite in about 10 minutes? Reel in, check the bait and cast "
            "again. Arrive early when the trout are stocked, give other anglers room, and bring ice if you "
            "keep some.",
        ),
        source_ids=("tpwd-trout-tips", "nydec-trout-synthetic"),
    ),
)

# Added 2026-11-08 from the second pass over forum questions (QUESTIONS ONLY,
# docs/data-sources.md): telling fresh fish from spoiled, and what to wear.
TOPICS += (
    HandbookTopic(
        id="care-fresh-or-spoiled",
        category="care",
        title="Is my fish good to eat? Fresh or spoiled",
        body=(
            "Smell it first. Fresh fish smells fresh and mild. Fish that smells fishy, sour or of "
            "ammonia has gone off: throw it away.",
            "A whole fish should have clear, shiny eyes, red gills with no smell, and firm flesh "
            "that springs back when you press it.",
            "A fillet should be firm, with red blood lines, and no discoloration, darkening or "
            "drying around the edges.",
            "Color alone doesn't tell you: what the fish ate and how it was handled change it. "
            "Fish that has been frozen may lose its bright eyes and firm flesh, but it should "
            "smell fresh and mild all the same.",
            "To keep it good, put it on ice soon after it's caught. Cleaned fish keeps up to two "
            "days in a refrigerator at 40°F or below, the closer to 32°F the better; freeze it if "
            "you won't cook it by then (see Freezing your catch).",
        ),
        source_ids=("fda-seafood", "nydec-guide"),
    ),
    HandbookTopic(
        id="safe-clothing",
        category="safety",
        title="What to wear fishing, warm days and cold",
        body=(
            "Dress for the weather in clothes that can get dirty. Light-colored long sleeves and "
            "long pants guard against sun and insects, and light fabrics keep you from "
            "overheating on hot days.",
            "When it's cold, wear layers under a windproof outer shell, which holds heat in better "
            "than a sweatshirt; take a layer off as it warms up. Water-repellent pants and jacket "
            "beat jeans, which take a long time to dry. Add gloves, a knit hat and waterproof "
            "boots.",
            "Wind and water of 50–60°F can bring on hypothermia, even in spring and fall. A life "
            "jacket also helps keep your body's core warm.",
            "Sturdy shoes, such as sneakers, keep you steady on an uneven bank and protect your "
            "feet from stray hooks.",
            "A hat with a brim and sunglasses, polarized if you can, shade your eyes and guard "
            "your head from a stray hook; polarized lenses also cut the glare so you can see into "
            "the water.",
            "Bring rain gear even on a sunny morning, and sunscreen of at least SPF 15: water "
            "reflects the sun. After sunscreen or bug spray, wash your palms, because the smell "
            "on bait or a lure can put fish off.",
        ),
        source_ids=("mndnr-minnaqua-safety", "nydec-guide", "tpwd-ae-guide"),
    ),
)

# Who needs a license, per state: one topic each, shown only in that state.
TOPICS += tuple(
    HandbookTopic(
        id=f"rule-license-{code.lower()}",
        category="rules",
        title=f"Do I need a fishing license? ({JURISDICTIONS[code].name})",
        body=license_body(JURISDICTIONS[code].name, entry, JURISDICTIONS[code].agency_label),
        source_ids=(f"license-{code.lower()}",),
        region=code,
    )
    for code, entry in STATE_LICENSES.items()
)


def limits_body(name: str, agency: str) -> tuple[str, ...]:
    """The answer to "how many can I keep" and "how big does it have to
    be": where the numbers are, not the numbers, which change every year
    and differ by fish and by water (added 2026-11-08)."""
    return (
        f"{name} sets how many fish of each kind you may keep in a day (the daily bag or creel "
        "limit) and, for many fish, the shortest, and sometimes the longest, one you may keep. "
        "They differ by kind of fish, and some lakes and rivers have their own.",
        f"FishEye doesn't copy the numbers, because they change: {agency}'s size and bag limits "
        "page lists them. Check it before you keep a fish.",
        "A fish you may not keep goes back at once, handled gently (see Catch and release).",
    )


# How many may be kept, and how big, per state: one topic each, shown only
# in that state, pointing to the agency's own limits page.
TOPICS += tuple(
    HandbookTopic(
        id=f"rule-limits-{code.lower()}",
        category="rules",
        title=f"How many fish can I keep, and how big? ({j.name})",
        body=limits_body(j.name, j.agency_label),
        source_ids=(limits_source_id(code),),
        region=code,
    )
    for code, j in JURISDICTIONS.items()
    if j.limits_url
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
