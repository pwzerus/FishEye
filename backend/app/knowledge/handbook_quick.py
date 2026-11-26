"""A handbook topic at a glance (the owner, 2026-11-25: "I don't want to read
that many words").

One line, then the few points to remember. The page shows them above the
topic's own text, which folds under a "Full explanation" tap with every fact
this leaves out. The topic's drawing or gear photos sit between the line and
the points, so the points don't repeat the drawing's steps.

Written from the topic's own sentences (angling_handbook.py): no fact,
number or condition that isn't there. A rule's "may" stays "may", and a
state's rule card says which state. Change the topic and this together.

Other languages: translations/<lang>_quick.json, keyed "<topic>.lead" and
"<topic>.points#<i>", like the handbook's own table.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuickTake:
    lead: str
    points: tuple[str, ...]


QUICK: dict[str, QuickTake] = {
    # The first, built for the owner to judge (2026-11-25). Its steps are
    # moving pictures with captions of their own (frontend QuickDrawings.tsx).
    "technique-landing": QuickTake(
        lead="Keep the line tight, bring the fish in slowly, and net it head first.",
        points=(
            "Slack line loses fish.",
            "Don't tighten the drag in the middle of the fight.",
            "Fish often lunge once more near you. With a big fish, ease the drag a little.",
            "In water of 70°F or more, land trout fast.",
        ),
    ),
    # Written from each topic's own sentences, 2026-11-25.
    "bait-worms": QuickTake(
        lead="Use nightcrawlers for bass and catfish, and a small worm or a piece of one for bluegill, crappie and trout.",
        points=(
            "Nearly every freshwater game fish eats worms.",
            "Redworms are a favorite for redear sunfish.",
            "Dig them up, or look under boards and rocks after rain.",
            "Keep them cool and they'll last up to a month.",
        ),
    ),
    "bait-minnows": QuickTake(
        lead="Use small minnows for crappie, medium ones for bass and larger trout, and large shiners for big bass.",
        points=(
            "Keep them in a minnow bucket, in the water they came from, and use them soon.",
            "Never dump unused bait into a lake. It can bring in unwanted animals.",
            "Check your state's bait rules before you buy. Some states restrict live fish as bait.",
            "California doesn't allow fish as bait in most of its inland waters.",
        ),
    ),
    "bait-insects": QuickTake(
        lead="Use a lively cricket for bluegill, especially big ones in summer and late fall.",
        points=(
            "Panfish, sunfish and trout eat crickets, grasshoppers, beetles, ants and caterpillars.",
            "Grasshoppers that fall from the bank are a summer staple for river bass.",
            "Push the hook in slowly. A hook through the front kills an insect quickly.",
        ),
    ),
    "bait-crayfish": QuickTake(
        lead="Crayfish are a main food of bass and catfish, and hooked well, they keep moving naturally.",
        points=(
            "Freshwater drum root along the bottom for them too.",
            "You can also use a cut-off tail to hide the hook.",
            "Catch them in rocky spots with a fine-mesh net, or a trap baited with chicken liver.",
            "Keep them in damp rags or moss.",
        ),
    ),
    "bait-shad-cut": QuickTake(
        lead="Shad, live or cut into pieces, are the top bait for blue catfish, stripers and hybrids.",
        points=(
            "Shad is their main food. Use it fresh when you can.",
            "Cut chunks with the skin on, and run the hook through the skin.",
            "Hook the chunk shallowly so the point stays exposed.",
        ),
    ),
    "bait-liver-soft": QuickTake(
        lead="Use chicken liver, hot dogs or cheese from the food store for channel catfish.",
        points=(
            "Channel catfish take non-living baits far more readily than flathead or blue catfish.",
            "Soft baits tear off the hook, so run the hook through several times.",
            "Let liver or clams firm up briefly in the sun.",
            "A small treble hook holds soft baits better.",
        ),
    ),
    "bait-dough-corn": QuickTake(
        lead="Dough baits work by scent, and they catch carp, catfish, trout and panfish.",
        points=(
            "Carp rarely hit lures, so fish a bait on the bottom, where they find it by smell.",
            "Carp also take canned or frozen corn, boiled field corn and bread.",
            "Stocked trout take dough baits such as PowerBait.",
            "Make your own dough from flour or cornmeal, hot water and a flavor such as garlic.",
        ),
    ),
    "tackle-reels": QuickTake(
        lead="A spincast reel is easy to learn and forgiving, so it's a good starter reel for beginners and kids.",
        points=(
            "Spinning reels are the most versatile. One medium outfit handles a wide range of lures.",
            "Baitcasting reels work best with heavier lures and line, and give more control.",
            "Baitcasting takes a practiced thumb, and brake adjustments when lures change.",
            "With a fly reel, you strip line off by hand, and the rod casts the weight of the line.",
        ),
    ),
    "tackle-rods": QuickTake(
        lead="A medium-light rod from 5½ to 6½ ft, with a reel for 4 to 12 lb line, suits most people as a first rod.",
        points=(
            "Ultralight power suits small trout and panfish. Heavy suits big fish and heavy baits.",
            "The rod's label gives its lure weight range, roughly ¼–¾ oz for a medium rod.",
            "A fast rod bends mostly in the top third, for accuracy and hard hooksets.",
            "Children manage a shorter rod more easily.",
            "The rod's length, action and the line it suits are printed just above the handle.",
        ),
    ),
    "tackle-line": QuickTake(
        lead="Mono is the cheapest and the standard, fluorocarbon is nearly invisible, and braid doesn't stretch.",
        points=(
            "Mono stretches, which can weaken a long-distance hookset, but holds up to rock and wood.",
            "Fluorocarbon is popular in clear water and as a leader, but it's stiffer and costs more.",
            "With braid, you feel bites and hooksets at once.",
            "Braid is less abrasion resistant and needs a mono or fluorocarbon leader.",
            "Cheap mono keeps coils from the spool.",
        ),
    ),
    "tackle-hooks": QuickTake(
        lead="Pick the hook size by the fish, and when in doubt, go smaller so the fish can take it.",
        points=(
            "Use thin wire for small fish and light hooksets (crappie, bluegill, trout).",
            "Use heavier wire for catfish and big fish. They can straighten a thin hook.",
            "The J hook (Aberdeen, round bend) is the most widely used.",
        ),
    ),
    "tackle-sinkers": QuickTake(
        lead="Use only enough weight to hold the bottom.",
        points=(
            "Most sinkers are lead. Tungsten is nearly indestructible but costs more.",
            "In a bottom rig, an egg sinker slides on the main line above a barrel swivel.",
            "Cone sinkers rig a worm Carolina-style. A bullet sinker goes ahead of a Texas-rigged worm.",
            "Pyramid sinkers are heavy weights for surf fishing.",
        ),
    ),
    "knot-palomar": QuickTake(
        lead="One of the easiest and strongest knots, for braid and mono, and even a child can tie it.",
        points=(
            "Many anglers find it easier than the clinch.",
            "Don't use it on crankbaits or lures with lots of hooks.",
        ),
    ),
    "care-release": QuickTake(
        lead="To release a fish unharmed, land it quickly, since a fish played to exhaustion can be harmed.",
        points=(
            "Set the hook quickly too, so the fish doesn't swallow the bait.",
            "Don't rub off the slime. It protects the fish from infection.",
            "The lower-jaw hold is for a small fish, under 5 lb.",
            "Don't jerk the line to break it off.",
            "From deep water, bring it up slowly so it can adjust to the pressure change.",
        ),
    ),
    "care-keeping": QuickTake(
        lead="Get a fish you'll eat into a cooler with plenty of ice soon after it's caught.",
        points=(
            "Use about 2 lb of ice per pound of fish, packed around it and into the gutted belly.",
            "Gutting removes a source of bacteria and lets the fish chill faster.",
            "It's illegal to let edible or bait fish from public waters die if you won't eat or use them.",
            "A stringer or wire basket keeps fish alive in cool water. In warm water, use ice.",
        ),
    ),
    "care-dispatch-bleed": QuickTake(
        lead="Kill a fish you'll keep quickly, so the meat doesn't bruise.",
        points=(
            "A sharp blow to the head stuns it.",
            "Bleed it while the heart still pumps.",
            "You can rip the gills with pliers, or cut the artery at the tail instead.",
            "Wait until the blood stops, then put it on ice.",
        ),
    ),
    "clean-fillet": QuickTake(
        lead="Lay the fish on its side and cut each fillet off along the backbone, then skin it.",
        points=(
            "Cut through the ribs as you go toward the tail.",
            "Lift the fillet off before you reach the tail.",
            "Freshwater drum fillet the same way and have no small bones in the fillet.",
            "On a drum, trim the dark red meat just under the skin.",
        ),
    ),
    "clean-fillet-panfish": QuickTake(
        lead="With a small fillet knife, cut along the top of the ribs, then slice the fillet off them.",
        points=(
            "Separate the fillet from the belly, then do the other side.",
            "Cutting along the outside of the ribs saves a little more of the belly meat.",
        ),
    ),
    "clean-catfish": QuickTake(
        lead="Catfish are skinned, not scaled, and the barbed spines in their side and back fins lock in place.",
        points=(
            "Fillet along the spine from tail to head, and work the fillet off the ribs.",
            "Or gut it and cut off the head and tail to cook it whole.",
            "Trim the dark lateral line, fat and connective tissue, where contaminants tend to collect.",
            "Soak fillets in milk or buttermilk for 30 minutes to an hour to take away a fishy taste.",
        ),
    ),
    "care-eating-safely": QuickTake(
        lead="Cook fish to 145°F inside, or until the flesh is no longer translucent and flakes easily with a fork.",
        points=(
            "A consumption ban means you can't keep fish from there. Catch and release is still legal.",
            "An advisory recommends limiting how much you eat, often by species and size.",
            "Advisories are strictest for women who are pregnant, nursing or may become pregnant, and children under 12.",
            "Check your state's current list before eating fish from a lake.",
        ),
    ),
    "id-catfish": QuickTake(
        lead="Start with the tail, which is deeply forked on a channel or blue catfish and almost square on a flathead.",
        points=(
            "A flathead's lower jaw sticks out past the upper. Channel and blue have longer upper jaws.",
            "A channel usually has dark spots, and a blue has none (outside the Rio Grande).",
            "A channel's anal fin is rounded with 24–29 rays, a blue's straight-edged with 30 or more.",
            "A flathead is yellow to brown and mottled. A blue is slate blue on the back.",
        ),
    ),
    "id-black-bass": QuickTake(
        lead="Close the fish's mouth and look at the jaw, which reaches well past the back of the eye only on a largemouth.",
        points=(
            "A largemouth has one dark stripe of blotches along each side.",
            "A spotted bass has a more broken stripe and rows of dark spots on a whitish belly.",
            "Most largemouth have no tooth patch on the tongue, and a spotted bass has one.",
            "A Guadalupe is green with a black diamond pattern reaching lower than a spotted bass's.",
            "Guadalupe bass live in flowing Hill Country streams and lack a smallmouth's vertical bars.",
        ),
    ),
    "id-temperate-bass": QuickTake(
        lead="The stripes are dark and unbroken on a striped bass, usually broken on a hybrid and faint on a white bass.",
        points=(
            "Several stripes reach the tail on a striped bass, only one on a white bass.",
            "Only a striped bass is slender, with body depth less than a third of its length.",
            "A white bass's tongue has one tooth patch, a striped bass's two distinct parallel ones.",
            "A hybrid's tongue has two tooth patches close together, or a single one.",
            "A white bass rarely gets big, but a hybrid can exceed 5 lb.",
        ),
    ),
    "id-panfish": QuickTake(
        lead="A bluegill has a black spot at the back of the dorsal fin, a small mouth and a flexible black ear flap.",
        points=(
            "Crappie are silvery and deep-bodied. White crappie have vertical bars and 5–6 dorsal spines.",
            "Black crappie have irregular black blotches and 7–8 dorsal spines.",
            "A redear has a red or orange edge on a short ear flap, and long pointed pectoral fins.",
            "Green sunfish (turquoise spots) and warmouth (dark lines from the eye) have large mouths.",
            "A longear has a long black ear flap edged in white.",
        ),
    ),
    "id-others": QuickTake(
        lead="Carp have whiskers, freshwater drum are silvery and grunt, and rainbow trout have a pink to red stripe.",
        points=(
            "A common carp is heavy and brassy to golden, with a long dorsal fin with a toothed spine.",
            "A freshwater drum's long dorsal fin is split in two.",
            "Its saltwater relative, the red drum, has a spot on the tail.",
            "A rainbow trout is slim and speckled all over, with a spotted tail.",
        ),
    ),
    "timing-day": QuickTake(
        lead="Low light is prime time for many fish, so try dawn, dusk, and cloudy or rainy days.",
        points=(
            "Catfish are most active at dawn, dusk and overnight. Big flatheads feed mostly at night.",
            "For bass, throw topwater lures early in the morning and toward dark.",
            "White bass and hybrids are most active at dawn and dusk.",
            "Hybrids are near the bank early and move deeper as the day goes on.",
            "On hot, sunny days, look deeper for Guadalupe bass.",
        ),
    ),
    "timing-season": QuickTake(
        lead="In spring, spawning gathers fish in the shallows, each kind at its own water temperature.",
        points=(
            "Largemouth spawn at about 60°F, crappie at 60–70°F, bluegill from about 70°F.",
            "Redear spawn when the water reaches the 70s, channel catfish at 75°F.",
            "White bass run up rivers to spawn in early spring.",
            "When bass and crappie slow in winter, try stocked rainbow trout, or blue catfish in Texas.",
            "Flathead catfish feed little while spawning but heavily before and after it.",
        ),
    ),
    "cast-spinning": QuickTake(
        lead="Let go of the line, or the button on a spincast, as the rod comes forward past your shoulder.",
        points=(
            "Cast over your dominant shoulder.",
            "The weight of the lure pulls the line off the reel.",
            "A spincast reel's enclosed housing keeps it from tangling, so it suits a beginner.",
        ),
    ),
    "cast-baitcast": QuickTake(
        lead="Put your thumb back on the spool as the lure hits the water, since a spool still spinning makes a backlash.",
        points=(
            "After the lure lands, reel once or twice to engage the anti-reverse.",
            "A baitcaster isn't the reel to learn to cast on.",
            "Baitcasting is an acquired skill, worth learning for heavy lures and heavy line.",
        ),
    ),
    "technique-drag": QuickTake(
        lead="Set the drag before your first cast, since adjusting it while a fish is on is difficult.",
        points=(
            "When a fish pulls harder than the drag, the spool turns backwards and gives line.",
            "Too tight, and a big fish breaks the line. Too loose, and the fight drags on.",
            "If your line breaks when a fish makes a run, the drag is too tight, so loosen it.",
            "With braid, pull the line against pliers or a pencil, since braid cuts fingers.",
        ),
    ),
    "technique-measure": QuickTake(
        lead="Measure in a straight line from the tip of the snout to the extreme tip of the tail fin.",
        points=(
            "If the tail is hard, turn it to get the longest overall measurement.",
            "Length limits are set on this measurement, and they vary by water body.",
            "Check your state's rules for the lake you're on (in Texas, TPWD's) before you keep a fish.",
        ),
    ),
    "technique-shore": QuickTake(
        lead="On a lake or pond, cast parallel to the shoreline, since fish often hold within a foot or two of the bank.",
        points=(
            "Fish away from roads, ramps and crowds. Noise and fishing pressure mean fewer bites.",
            "Try the docks, laydowns, vegetation, rock piles and drop-offs within reach.",
            "Under a pier, fish right against the pilings.",
            "On a river, look for slower water like eddies and the slack behind rocks and log jams.",
            "Where a bridge or pilings rub the line, use a heavier leader.",
        ),
    ),
    "start-what-to-buy": QuickTake(
        lead="Start with a spincast or spinning rod and reel already spooled with 6 to 10 lb monofilament line.",
        points=(
            "Add bait hooks (No. 6 to 8), a few split shot, two or three bobbers and nightcrawlers.",
            "Get needle-nose pliers to take hooks out, and a small tackle box to keep it sorted.",
            "If you'll be on or near deep water, add a life jacket.",
            "Lures, a landing net and a second rod can wait until you know what you like to fish for.",
            "Before you go, get your license and check your state's rules.",
        ),
    ),
    "cond-cover": QuickTake(
        lead="Cast first to cover like weeds, downed trees, rock piles and docks, where fish find shelter and food.",
        points=(
            "Fish the edges and openings of weed beds and lily pads.",
            "The best weed beds run into deeper water.",
            "Docks are good at any time of day because of their shade.",
            "Don't fish only a dock's outside edge. The biggest fish often sit far underneath.",
            "Big fish hold right under overhanging trees and brushy banks, sometimes a foot from shore.",
        ),
    ),
    "cond-points": QuickTake(
        lead="Cast to points and drop-offs, and where a creek runs into the lake.",
        points=(
            "On a point that slopes gradually into deeper water, fish the tip and the corners.",
            "A point that drops off sharply, or has no deep water near it, is worth less.",
            "A drop-off is where the bottom falls away. Fish follow it to move between depths.",
            "A creek brings food, and fish gather there, most of all before moving upstream to spawn.",
        ),
    ),
    "cond-clarity": QuickTake(
        lead="How far you can see into the water tells you what to throw.",
        points=(
            "In clear water (two feet or more), use natural, prey-colored or flashy lures.",
            "In stained water (a few inches), use bright colors, such as chartreuse, gold or copper.",
            "In muddy water (an inch or two), use dark colors and lures that vibrate.",
        ),
    ),
    "cond-fronts": QuickTake(
        lead="Plan your trip for the day before a front, or three to four days after one.",
        points=(
            "Fish feed hard ahead of a storm, as a low-pressure system moves in.",
            "A bright high-pressure “bluebird” day after a storm is the hardest fishing of all.",
            "On those days, fish hold tight to cover and sit on the bottom.",
            "Bluebird days are hardest in clear lakes in late winter and early spring.",
        ),
    ),
    "cond-light": QuickTake(
        lead="On a bright, sunny day, fish deeper, in shade, or later in the day once the shallows have warmed.",
        points=(
            "Cloud and rain cut the light, so fish roam further for food. Rain also washes insects in.",
            "A bright spring day is good on a shallow, stained lake, and poor on a deep, clear one.",
            "In cold water, use small lures and light line, and retrieve slowly near the bottom.",
        ),
    ),
    "safe-lifejacket": QuickTake(
        lead="Of those who drowned in recreational boating accidents in 2019, 86 percent weren't wearing a life jacket.",
        points=(
            "Drowning was the reported cause in 79 percent of 2019's recreational boating deaths.",
            "Each state sets who must wear one, and when. Your state's law is on its own card.",
            "Don't buy a jacket for a child to grow into.",
        ),
    ),
    "safe-handling": QuickTake(
        lead="Catfish have stiff, barbed fin spines, the usual reason someone goes home early.",
        points=(
            "The spines are in the dorsal fin and both pectoral fins.",
            "You can also use pliers and a grip instead of your hand.",
            "Take hooks from any fish with long-nosed pliers or a hook-out, not your fingers.",
            "Give a fish that's going back wet hands and as little time out of the water as possible.",
            "Put a fish you're keeping on ice straight away.",
        ),
    ),
    "rule-line-disposal": QuickTake(
        lead="Old fishing line never belongs on the bank or in the water.",
        points=(
            "Discarded line tangles birds and other animals and doesn't break down in a landfill.",
            "Recycle monofilament and fluorocarbon at a collection bin, not in household recycling.",
            "Take off hooks and lures first, and leave out line with weed or growth on it.",
            "Keep a coffee can in the tackle box until you have enough to drop off.",
            "Braided and fused line can't be recycled. Cut it under a foot long and put it in a covered bin.",
        ),
    ),
    "cook-methods": QuickTake(
        lead="Cook fish ten minutes per inch of thickness, turning once.",
        points=(
            "A piece under half an inch thick needs less time and no turning.",
            "The ten-minute rule doesn't apply to deep frying or the microwave.",
            "It's done when it's opaque, flakes easily with a fork, and has reached 145°F inside.",
            "Color alone does not tell you it's done.",
            "Bake an inch-thick piece at 400°F with a little broth or lemon juice, about five minutes a side.",
        ),
    ),
    "cook-freezing": QuickTake(
        lead="Freezing keeps quality but adds none, so gut and chill the fish quickly first.",
        points=(
            "Don't freeze fish with soft flesh or blood clots in it.",
            "Vacuum pack it, or press the air out of heavy freezer bags. Don't add water.",
            "Use the coldest setting and don't pack the freezer full, so it's solid within 24 hours.",
            "Fatty fish such as trout stay in excellent condition about three months, lean fish roughly twice that.",
            "In the freezer, raw fish is safe for three to eight months.",
        ),
    ),
    "rig-jigs": QuickTake(
        lead="A jig catches almost anything, because you can fish it at any depth and it moves like small prey.",
        points=(
            "Use 1/32–1/8 oz jigs for crappie and sunfish, 1/8–1/4 oz for a tube or a Ned rig.",
            "You can add a live minnow, leech or nightcrawler to the hook.",
            "For crappie, reel a light jig slowly as it sinks, or hang it under a bobber you shake.",
        ),
    ),
    "rig-texas": QuickTake(
        lead="Let the worm sink to the bottom, then drag it back slowly through weeds and cover.",
        points=(
            "It's used mostly for bass.",
            "Or move it a few feet, wait a few seconds, and move it again.",
            "June bug, plum and green pumpkin are common colors.",
        ),
    ),
    "rig-wacky": QuickTake(
        lead="Let the stick worm sink slowly with no weight, then raise it off the bottom and let it fall again.",
        points=(
            "Watch the line. A bite can show as a tap there before you feel it.",
            "A wacky rig works in shallow and deep water.",
            "Green pumpkin and watermelon are common colors.",
        ),
    ),
    "rig-drop-shot": QuickTake(
        lead="Let the weight sit on the bottom a few seconds, shake the rod tip, move it a few feet, and repeat.",
        points=(
            "The bait hangs above the bottom, because the hook is tied above the weight.",
            "Use it in deep, clear water.",
        ),
    ),
    "rig-slip-bobber": QuickTake(
        lead="A slip bobber lets bait hang at any depth, and you can still cast easily.",
        points=(
            "Use it when fish are deeper than a fixed bobber can reach.",
            "Crappie and walleye are often that deep in summer.",
        ),
    ),
    "rig-bottom": QuickTake(
        lead="Cast to the spot and let the bait rest on the bottom.",
        points=(
            "The sinker slides on the line, so a fish can take the bait without feeling it.",
            "This is the usual rig for catfish and carp.",
            "Scale the sinker and hook down for smaller fish.",
        ),
    ),
    "knot-joining": QuickTake(
        lead="Use a blood knot or a surgeon's knot to tie one line to another, such as a leader to your main line.",
        points=(
            "A blood knot needs about 2 in of overlap and five wraps with each end.",
            "A surgeon's knot needs about 6 in of overlap.",
            "For a surgeon's knot, tie an overhand knot with both, then pull the ends through again.",
        ),
    ),
    "method-trolling": QuickTake(
        lead="To cover water and find fish, troll slowly with a crankbait that dives to the depth you're fishing.",
        points=(
            "Lip size, line thickness, how much line is out and speed all change the lure's depth.",
            "To go deeper, use lead core line, side planers or snap weights.",
            "For walleye, use a 7–9 ft medium-heavy rod, a baitcasting reel and 10–12 lb line.",
        ),
    ),
    "method-ice": QuickTake(
        lead="Check the ice first (see Ice safety), then fish through a hole.",
        points=(
            "You need a license, a short light rod and a bucket.",
            "Trout and pike need a bigger hole than panfish.",
            "Minnows and small fly larvae (spikes or mousies) are the usual baits.",
            "Trout and landlocked salmon are often just a few feet under the ice.",
            "A group of anglers or lots of old holes means fish were caught there.",
        ),
    ),
    "method-stream": QuickTake(
        lead="Cast where a place for fish to hide meets a place for them to feed.",
        points=(
            "Undercut banks often hold the biggest fish. Sunken trees, rocks and eddies hide fish too.",
            "Fish feed on the outside of bends, along seams where two currents meet, and at drop-offs.",
            "In a pool, active fish are often at the head and tail.",
            "Trout face upstream, so work your way upstream when you can, and move slowly.",
            "Take care below dams, where the water is swift and changes fast.",
        ),
    ),
    "method-fly": QuickTake(
        lead="Dry flies float, nymphs tumble along the bottom, and streamers look like small fish.",
        points=(
            "Cast a dry fly upstream and let it pass over feeding fish.",
            "With a nymph, a strike indicator on the leader sets the depth and a split shot sinks it.",
            "Cast a streamer and work it back toward you, or let the current swing it on a tight line.",
            "Rods are rated by line weight, and a 4, 5 or 6 weight suits trout-sized flies.",
        ),
    ),
    "method-kayak": QuickTake(
        lead="Have a life jacket for everyone aboard.",
        points=(
            "Some states make you wear one in cold months, like Pennsylvania from Nov. 1 to April 30.",
            "Leave a float plan. Tell someone where you're going and when you'll be back.",
            "After dark, carry a white light you can show in time to avoid a collision.",
            "Bring a sound device, a change of clothes in a dry bag, and sun protection.",
            "Many states require a registration or launch permit even for a kayak. Check yours.",
        ),
    ),
    "timing-through-year": QuickTake(
        lead="Fish shallow in spring and fall, and deeper on hot summer days and in winter.",
        points=(
            "In spring, crappie and bass show up in backwaters and protected bays, in under 8 ft.",
            "In summer, walleye move to mid-lake humps and points, and crappie hang over open water.",
            "In fall, walleye follow shad, and shallow weedbeds and midday can be good.",
            "Bass fishing is often best with the water at 60–75°F.",
            "Trout need cold water, so don't fish for them when streams warm in summer.",
        ),
    ),
    "rule-clean-drain-dry-us": QuickTake(
        lead="Clean, drain and dry, so you don't carry invasive species to other water. Some states make it law.",
        points=(
            "Before you leave the access, take plants, animals and mud off the boat, trailer and gear.",
            "Flush the motor with 120°F water for 2 minutes, or as its manual says.",
            "Drain the motor, bilge, livewell and anything else that holds water before you leave.",
            "Let everything dry at least five days, or wipe it with a towel, before using it elsewhere.",
            "Never release live fish, bait or plants into any water.",
        ),
    ),
    "care-advisories": QuickTake(
        lead="Before eating fish from local waters, check your state's advice on mercury, PFAS, PCBs and DDT.",
        points=(
            "Take most care if you're pregnant or may be, are breastfeeding, or feed children.",
            "Mercury can harm a developing nervous system.",
            "Check too if you're an older adult, have a weak immune system or eat a lot of fish.",
            "Look for signs at the water's edge, or ask your state's health or environmental agency.",
            "Avoid mussels and clams collected during or right after a harmful algal bloom.",
        ),
    ),
    "safe-ice": QuickTake(
        lead="No ice is ever guaranteed safe, so ask locally and test it with holes as you walk out from shore.",
        points=(
            "Stay off new, clear ice under 4 in. Pennsylvania's chart asks for 5 in to fish on foot.",
            "Cars and trucks need far more, and tables differ, so follow your state's.",
            "White ice and slush ice are about half as strong as clear ice, so double the numbers.",
            "Stay off rivers and away from where streams enter or leave, since that ice is weaker.",
            "Never go alone. Carry ice picks and a rope, wear a life jacket, and spread out.",
        ),
    ),
    "id-steelhead-rainbow": QuickTake(
        lead="A steelhead is a rainbow trout that went out to the ocean or a Great Lake and came back up a river to spawn.",
        points=(
            "Steelhead are bigger, and silvery when they've just come in from the lake or sea.",
            "Anglers call a bright one a chromer.",
            "The longer one stays in the river, the darker it gets, looking more like a stream rainbow.",
            "Unlike Pacific salmon, steelhead don't have to die after spawning.",
            "A state may have its own steelhead rules, seasons or stamp, so check before you keep one.",
        ),
    ),
    "id-salmon": QuickTake(
        lead="Look in its mouth, since a Chinook (king) has black gums along the lower jaw and a coho's are lighter.",
        points=(
            "Chinook have black spots on both tail halves, coho small spots on the upper half only.",
            "Chinook are the biggest Pacific salmon, and pink salmon are the smallest.",
            "A spawning male pink grows a big hump on its back, so anglers call pinks humpies.",
            "Silver when fresh, they turn olive, red or maroon upriver, and males grow a hooked jaw.",
            "Chinook, coho and pink salmon all die after spawning.",
        ),
    ),
    "id-whitefish-cisco": QuickTake(
        lead="A whitefish's snout hangs over its lower jaw, while a cisco's lower jaw reaches the tip of its snout or past it.",
        points=(
            "Both are trout-shaped and silver, with a small fleshy fin (the adipose fin) near the tail.",
            "Whitefish grow bigger, and ice anglers catch cisco more often.",
            "Cisco also go by the names tullibee, lake herring or just herring.",
            "A burbot (eelpout) is long, smooth and slimy, with one whisker under its chin.",
            "A burbot looks like a cross between an eel and a catfish, and bites in winter.",
        ),
    ),
    "timing-runs": QuickTake(
        lead="Time your trip to the run, when salmon and steelhead swim up rivers to spawn.",
        points=(
            "On Minnesota's North Shore, fall runs go from about September until the rivers freeze.",
            "In New York, late October and November is often the best time for steelhead.",
            "Steelhead that enter in fall spend the winter in deep pools.",
            "Steelhead spawn from about March to April, then feed heavily on the way back to the lake.",
            "New fish move up after rain or a brief winter warm-up, not in very low or flooding water.",
        ),
    ),
    "method-steelhead": QuickTake(
        lead="Drift a spawn sac just off the bottom, a little slower than the current.",
        points=(
            "Look where two currents meet, by boulders and logs, and at the head and tail of big pools.",
            "On sunny days, fish early and late, since steelhead dislike bright light.",
            "Any pause, tug or upstream movement of the line can be a bite.",
            "Don't try to stop a hooked fish's first run. Hold the rod up and let the drag work.",
            "Wading in winter is risky. Wear studded boots and a life jacket, and fish with a friend.",
        ),
    ),
    "method-great-lakes-trolling": QuickTake(
        lead="Keep changing the lure, color, depth and speed until something works, then stay with it.",
        points=(
            "Use spoons, long thin crankbaits (stickbaits) or a dodger with a fly behind it.",
            "From December to May, trout and salmon are often close to shore in water under 30 ft.",
            "In late spring and summer, head offshore over 75–200 ft of water.",
            "As the surface warms, lake trout go deep, often below 90 ft, while salmon stay higher.",
            "A baitcasting reel with a line counter lets you repeat the depth that caught a fish.",
        ),
    ),
    "method-lake-trout": QuickTake(
        lead="Through the ice, start in 30–40 ft and move out to 90–100 ft.",
        points=(
            "Try points, reefs, islands, bay mouths and slowly dropping shorelines next to deep water.",
            "Lake trout roam open water after schools of cisco or smelt, so follow the bait fish.",
            "Work the whole depth with silver or white lures, and expect bites as the lure falls.",
            "Set tip-ups with a sucker or shiner along the 40 to 60 ft contour.",
            "Check tip-up bait about every half hour, and stay close to your tip-ups.",
        ),
    ),
    "method-sturgeon": QuickTake(
        lead="Anchor just above a deep hole or seam in a big river, and let your bait sit on the bottom.",
        points=(
            "Use nightcrawlers on a large circle hook, with a stout rod and braided line.",
            "When the line tightens, take up the slack and lift the rod to set the hook.",
            "Keep the fish in the water as much as you can, and never touch the eyes or gills.",
            "For a photo, support its body level.",
            "Seasons, tags and catch rules differ by water, so read your state's rules before you go.",
        ),
    ),
    "method-ice-perch": QuickTake(
        lead="Jig gently, because too much movement scares perch off.",
        points=(
            "Look near green weeds in shallow water early in winter, and deeper as winter goes on.",
            "Fish just above the weed tops or along weed edges.",
            "Use wax worms or mealworms on tiny jigs (1/64 to 1/16 oz) and 2–4 lb line.",
            "Watch for the rod tip to twitch or the line to go slack.",
            "The best bites come near dawn and dusk.",
        ),
    ),
    "method-stream-trout-bait": QuickTake(
        lead="Let your bait come down the stream the way real food does, since trout face the current.",
        points=(
            "Use a short ultralight spinning rod, 4–6 lb line and small hooks (sizes 10–14).",
            "Brown trout hide in the deepest pools under cover and feed in riffles early and late.",
            "Brook trout like small, clean, spring-fed streams. Rainbows hold in faster, bigger water.",
            "With spinners, try gold for browns, silver for rainbows and copper for brook trout.",
            "If your shadow falls on the pool, trout may hide for an hour or two, so move on.",
        ),
    ),
    "cond-thermocline": QuickTake(
        lead="In summer, fish hold just above the thermocline, the band where the temperature drops fast.",
        points=(
            "From late spring, many lakes deeper than about 10 ft split into warm and cold layers.",
            "By midsummer the cold bottom water has too little oxygen for fish to stay.",
            "The thermocline is about 5 ft down in a murky lake and 16 ft or more in a clear one.",
            "A good depth finder often shows it as a fuzzy line. That line is the depth to fish.",
            "After the fall turnover, usually late September to mid-October, fish can be at any depth.",
        ),
    ),
    "bait-why-it-works": QuickTake(
        lead="Use natural colors and lifelike movement in clear water, and scent or noise in murky water or at night.",
        points=(
            "Most fish hunt by sight, so many feed best in daylight.",
            "Catfish find food by smell, so smelly baits like cut bait, worms and stink bait work.",
            "For catfish, leave the bait in one spot for a while instead of moving it often.",
            "Fish feel vibrations with their lateral line. Lures that rattle or thump send them.",
        ),
    ),
    "technique-bite": QuickTake(
        lead="When the bobber goes under, reel up the slack and set the hook before the fish swallows the bait.",
        points=(
            "A bite can also make a bobber twitch or slide, or a stick bobber lie flat or ride higher.",
            "On the bottom, the rod tip may dip or shiver, or the line go slack all at once.",
            "Hold the rod firm enough that a strike can't pull it away, but light enough to feel a tug.",
            "With slack or a loop in the line, the hook won't go in and the fish lets go.",
            "With trout and panfish, too hard a jerk can break light line.",
        ),
    ),
    "care-deep-hook": QuickTake(
        lead="A fish hooked deep is hurt more by digging for the hook than by leaving it in.",
        points=(
            "Back a lip hook out with the fish in the water, if you can.",
            "A pinched barb is kinder if the hook ever ends up in your own skin.",
            "With barbs pinched down, you'll lose a few more fish.",
            "Set the hook soon after the bite and fewer fish swallow it (see Is it a bite?).",
        ),
    ),
    "trouble-no-bites": QuickTake(
        lead="On water you don't know, move and look for fish around docks, rocks, fallen trees, weed edges and drop-offs.",
        points=(
            "Don't jump, run or bang gear, and keep your shadow off the water. Talking is fine.",
            "Cast past the spot you think holds fish and bring the bait into it.",
            "Change the depth so the bait hangs just above the weeds, logs or bottom.",
            "Go lighter, with the smallest bobber that holds the bait up and can still be seen.",
            "Try another time of day.",
        ),
    ),
    "trouble-stolen-bait": QuickTake(
        lead="If the bait keeps disappearing and nothing gets hooked, change one thing at a time.",
        points=(
            "Try a smaller hook, a long-shanked No. 6 or 8 for panfish.",
            "Run the hook through a piece of nightcrawler more than once, so little hangs free.",
            "A small bobber with only enough split shot lets a fish pull it down without feeling much.",
            "Set the hook sooner, with the slack reeled up first.",
            "Worms hold on the hook well, and so do biodegradable baits made from natural ingredients.",
        ),
    ),
    "trouble-snags": QuickTake(
        lead="Try the gentlest steps first, and if a few tries don't free the hook, break the line.",
        points=(
            "Mind your footing on wet rocks, roots and logs. The bottom can drop off suddenly.",
            "Bare line can cut your fingers, so wrap it around your hand over a sleeve or a glove.",
            "Turn your face away and keep others back. A hook that pulls free can fly at you.",
            "To snag less, use a bobber to keep the bait up off the bottom.",
            "Take broken line home. Hooks and line left behind harm people and wildlife.",
        ),
    ),
    "trouble-retie": QuickTake(
        lead="Cut off any frayed end, tie on a new hook, and put back what came off with it.",
        points=(
            "Use the improved clinch knot for monofilament, or the Palomar knot for braid or mono.",
            "Wet the knot, pull it tight, and trim the end, not too close.",
            "Keep spare hooks, sinkers, bobbers and line in your tackle box.",
            "When the spool runs low, put new line on.",
        ),
    ),
    "trouble-line-twist": QuickTake(
        lead="Don't turn the handle while a fish pulls line off against the drag, since every turn twists the line.",
        points=(
            "After each cast, turn the handle until the reel clicks, so loose line doesn't pile up.",
            "Keep knots out of the line except at the end. They weaken it and spoil the cast.",
            "If it still twists, it's time for new line.",
        ),
    ),
    "rule-manners": QuickTake(
        lead="Give other anglers room, and look behind you before every cast.",
        points=(
            "Don't wade or cast in front of someone, and leave space for their back cast.",
            "Keep it quiet. No loud music, shouting, tossing stones or splashing about.",
            "Fishing private water takes the owner's permission. Ask before crossing private land.",
            "Take your trash home, bait cups, fishing line and cigarette butts included.",
            "Don't move fish from one water to another (see Clean, drain and dry).",
        ),
    ),
    "method-kids": QuickTake(
        lead="Make the trip about the child, keep it to an hour, maybe two, and stop while it's still fun.",
        points=(
            "Use a push-button (spincast) reel on a short rod, with a hook, a split shot and a bobber.",
            "Bait with worms. They stay on the hook, and most fish eat them.",
            "Hand them your rod when theirs needs fixing, or hook a fish and let them reel it in.",
            "Bring snacks, drinks, hats, sunglasses, sunscreen, bug spray and spare clothes.",
            "On or near deep water, a child needs a life jacket that fits now, not one to grow into.",
        ),
    ),
    "safe-lightning": QuickTake(
        lead="If you can hear thunder, you're close enough to be struck, so get out of and away from the water.",
        points=(
            "Check the forecast before you go, and put the trip off if thunderstorms are likely.",
            "In a boat or a kayak, head for land and shelter at once.",
            "Shelter is a solid, enclosed building or a hard-top car or truck, not a lone tree or shed.",
            "With no shelter, keep away from tall objects and lone trees, and get off hills and ridges.",
            "Wait 30 minutes after the last thunder before going back out.",
        ),
    ),
    "safe-heat": QuickTake(
        lead="Heat stroke is an emergency, so call 911, move the person somewhere cooler, cool them and give no fluids.",
        points=(
            "Heat stroke brings confusion, slurred speech, hot red skin and a temperature above 103°F.",
            "Heavy sweating, weakness and cool, pale, clammy skin can mean heat exhaustion.",
            "For heat exhaustion, move somewhere cooler, loosen clothing, cool the skin and sip water.",
            "Get medical help if the person vomits, or it gets worse or lasts over an hour.",
            "Gently rub a cramp, sip water unless you feel sick, and get help if it lasts over an hour.",
        ),
    ),
    "safe-cold-water": QuickTake(
        lead="Wear a life jacket on the water and when fishing from slippery rocks and docks.",
        points=(
            "A sudden plunge can make you gasp in water as warm as 77°F.",
            "Water of 50–60°F can shock the body as badly as near-freezing water.",
            "If you fall in, stay calm, keep your head up and get out as soon as you can.",
            "Get warm and dry fast. Hypothermia begins when body temperature drops to 95°F.",
            "Dress for how cold the water is, not the air, and tell someone where you're going and when you'll be back.",
        ),
    ),
    "tackle-care": QuickTake(
        lead="After each trip, check the rod for cracked or loose guides, and keep it clear of car doors and tailgates.",
        points=(
            "Before you store a reel, back the drag off. A drag left tight flattens its washers.",
            "Never spray a reel with a hose or pressure washer. That drives grit into the gears.",
            "Clean and oil a reel at least once a year, following the maker's instructions.",
            "After saltwater, rinse the rod, reel and lures gently with fresh water.",
            "Leave the tackle box open until everything in it is dry, or hooks and pliers rust.",
        ),
    ),
    "tackle-new-line": QuickTake(
        lead="Replace your line every year, braid too, even if it never breaks.",
        points=(
            "Change it sooner if it snaps easily as you tie it, keeps curling, or the end is nicked.",
            "For most freshwater fishing, use 6 to 10 lb monofilament.",
            "Use 4 to 8 lb for bluegill and perch, 8 to 12 lb for bass, 10 to 20 lb in saltwater.",
            "Fill a spinning reel to about ⅛ in below the rim. Overfilling causes reel trouble.",
            "Take the used line to a recycling bin.",
        ),
    ),
    "trouble-spincast": QuickTake(
        lead="If the line won't go out, look at the rod tip first, where the line may be wrapped around it.",
        points=(
            "Press and release the button and pull line out by hand to feel for a loop caught inside.",
            "Pull line out until it runs smoothly, then reel it back in while pinching it lightly.",
            "If the handle came off, it was turned backwards. Put it back and turn it the right way.",
            "If problems keep happening, take some line off or put on new line.",
        ),
    ),
    "safe-hook-injury": QuickTake(
        lead="A hook stuck in your skin can get infected or cause tetanus, so see a doctor about a tetanus shot.",
        points=(
            "After backing a hook out, clean the wound and put on antiseptic ointment and a bandage.",
            "Don't pull out a hook in your face. Pulling tears more tissue.",
            "Cover the hook and any lure on it with a paper cup or tape, so nothing knocks it.",
            "A deep puncture should be seen by a doctor, even once the hook is out.",
            "Pinch the barbs down or use barbless hooks, and look behind you before every cast.",
        ),
    ),
    "tackle-lead": QuickTake(
        lead="Lost lead sinkers can poison the birds that swallow them, so use tackle that isn't lead.",
        points=(
            "Tackle shops sell sinkers and jigs that aren't lead, such as tungsten.",
            "Check your state's rules. Some, like New York, restrict lead tackle.",
            "Pinch split shot on with pliers. Never use your teeth.",
            "Use the smallest weight that does the job. The fish feels less, and you lose less.",
        ),
    ),
    "clean-trim-fillet": QuickTake(
        lead="Cut out the dark strip and trim the fat, since some chemicals, such as PCBs, collect in a fish's fat.",
        points=(
            "Cut a shallow V along each side of the dark strip and lift it out.",
            "Trim off the fat along the back and the belly flap, and take the skin off.",
            "Grilling, broiling or baking also helps lower how much of those chemicals you eat.",
            "Rinse, pat dry, and keep fillets on ice or in the fridge until you cook or freeze them.",
            "Check your state's advisories before eating fish from a lake (see Fish advisories).",
        ),
    ),
    "method-stocked-trout": QuickTake(
        lead="Floating dough bait works especially well on fresh-stocked trout, which are used to pellets.",
        points=(
            "In Texas, trout are stocked in winter because summer water is too warm for them.",
            "Use a light rod, 4 to 10 lb line and a small rig, with no big snaps or heavy weights.",
            "On a bottom rig, mold enough floating bait onto the hook to lift it off the bottom.",
            "Cast and let it sit. After about 10 minutes with no bite, check the bait and cast again.",
            "Arrive early when the trout are stocked, and give other anglers room.",
        ),
    ),
    "care-fresh-or-spoiled": QuickTake(
        lead="Smell it first, and throw it away if it smells fishy, sour or of ammonia.",
        points=(
            "A whole fish should have clear, shiny eyes, red gills with no smell, and firm flesh.",
            "A fillet should be firm, with red blood lines and no discoloration, darkening or dry edges.",
            "Color alone doesn't tell you. Frozen fish should still smell fresh and mild.",
            "Cleaned fish keeps up to two days at 40°F or below, so freeze what you won't cook by then.",
        ),
    ),
    "safe-clothing": QuickTake(
        lead="Dress for the weather in clothes that can get dirty, and bring rain gear even on a sunny morning.",
        points=(
            "Light-colored long sleeves and long pants guard against sun and insects.",
            "When it's cold, wear layers under a windproof shell, and skip jeans, which dry slowly.",
            "Wind and water of 50–60°F can bring on hypothermia, even in spring and fall.",
            "Sturdy shoes, a brimmed hat and sunglasses guard you from stray hooks.",
            "After sunscreen (at least SPF 15) or bug spray, wash your palms so fish aren't put off.",
        ),
    ),
}
