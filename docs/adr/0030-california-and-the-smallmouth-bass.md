# ADR 0030: California, and a guide for smallmouth bass

## Status
Accepted. The third state (ADRs 0027-0029), and the first new species
guide since ADR 0024.

## California's rules

Sources, all opened: CDFW's licence page, its 2026 freshwater sport fishing
regulations booklet (Title 14), Fishing in the City, its mussel page, and
the Division of Boating and Waterways' safety-equipment and invasive-mussel
pages. Same rules as before: close paraphrase, conditions kept, no creel or
length numbers (the limits link is CDFW's interactive regulations map).

- `Jurisdiction("CA")`: CDFW, licence page, limits map, and bait rules.
- Handbook cards tagged `CA`: the licence (16 and older; report cards for
  steelhead and sturgeon at any age; Second Rod validation; ocean piers and
  Free Fishing Days), the life-jacket law (under 13, including kayaks and
  canoes), Clean Drain Dry with mussel inspections and the Mussel Fee
  sticker (the only part DBW states as law), measuring and keeping fish,
  and a first trip (Fishing in the City).

**The rule that contradicts the guides.** California does not allow live or
dead fin fish as bait in most of its inland waters; each district lists a
few exceptions, usable only where caught. The species guides were written
in Texas and recommend live minnows. So, unlike Texas and Georgia:

- `Jurisdiction.bait_rules_on_every_bait_question`: in California every bait
  question shows the state's bait rules in second place, whatever they rank
  (keyword and semantic search both ranked "live minnows" passages above
  them for "can I use live minnows as bait").
- On a guide page, the live-bait list carries a California warning linking
  the rules (`LiveBaitWarning`).
- The general "Minnows and shiners" card now says to check your state's
  bait rules, naming California.

**The gate.** Rules questions that name no fishing word were turned away as
"not a fishing question": "does my 14 year old need a license", "do I need a
report card for sturgeon", "what is a mussel fee sticker". Added: "need a
license", "report card(s)", "mussel fee", "golden mussel", and sturgeon,
steelhead, kokanee and quagga as fishing words. The off-topic set still
rejects 29 of 30 (unchanged).

## Smallmouth bass

The most-asked fish without a guide, common in all three states, and the
app's own example of "no guide for that fish". Sources: TPWD and Missouri
MDC species pages (identification, habitat, spawning, size), Minnesota DNR
and New York DEC (where to look, tackle), Take Me Fishing (rivers, murky
water). Two setups (tube or Ned rig on 8-10 lb spinning tackle; jig and
minnow on the bottom), the usual sections, a fishing-plan entry, and an
illustration. Names: smallmouth, smallie(s), bronzeback(s), 小口黑鲈/小嘴鲈/
小口鲈; "black bass" now includes it. A bare "bass" still means largemouth,
spotted and Guadalupe, so existing answers don't shift.

Commons couldn't be reached to choose a photo by hand, so the species is
listed in `AWAITING_CURATION`: the server looks up Wikipedia's freely
licensed lead image at run time, with its author and licence, as for the
other newer guides. No attribution was written from memory.

The unguided-fish examples in tests and the eval moved to rock bass and
黄金鲈 (yellow perch).

## Results

- Backend 612 tests, frontend 212.
- Eval (hybrid, the default): original set 99% / MRR 0.90, newest topics
  100% of 42 (8 new smallmouth questions), everyday-word names 100%,
  rephrasings 96% / 90% untuned, off-topic 97%; unchanged elsewhere. The
  one wrong-fish case (a Texas-rig question naming no fish) now pulls in
  smallmouth lures instead of redear sunfish.
- 11 California questions in tests, English and Chinese, each finding
  California's card and none of Texas's or Georgia's.
- In the browser with California chosen: five California cards and no
  Texas or Georgia ones, California's bait rules on the guide page, and the
  warning above the smallmouth's live-bait list.

## Map data

`--state CA` in both importers. To be run where Overpass and GBIF are
reachable (README). California's OSM query is large; if Overpass times out,
run it again later.
