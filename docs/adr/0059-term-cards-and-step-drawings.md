# 0059. Term cards and step-by-step drawings

Date: 2026-11-16. Status: accepted.

## Context

Reading the handbook on a phone, the owner (2026-11-16) asked for:

- a drawing wherever a topic ties a knot, threads something or teaches a
  movement: every knot, putting line on a spincast reel, and so on;
- every technical word underlined. A tap opens a small card, not the page.
  A second tap, on the card's link, opens the topic that explains it.

The handbook already had twelve drawings (RigDiagram, 2026-11-16). Each was
one picture with numbered parts and a list under it. The two knots in that
set (improved clinch, arbor) put four steps side by side, about 80 px each on
a phone. Baits and lures were already tappable on fish pages (BaitTip).

## Decision

**Step drawings.** `components/fish/StepDrawings.tsx` holds 40 drawings, a
picture per step (160 × 120) with the step's words under it. On a phone each
step stacks, its picture up to 260 px wide; from 900 px wide, two to a row.
They cover:

- every knot: clinch, Palomar, arbor, surgeon's loop, blood, surgeon's,
  keeping a knot strong;
- line on a reel: spincast, spinning, a spincast that won't cast;
- casting a spinning and a baitcasting reel, setting the drag, from bite to
  hookset, playing and landing;
- releasing, taking out a hook, a hook in your skin, freeing a snag,
  holding a catfish;
- hooking worms, minnows, crickets, crayfish, shrimp and dough;
- split shot, working a jig, stream drifting, ice fishing, trolling, bank
  fishing;
- life jacket fit, keeping fish, filleting (two ways), skinning a catfish,
  scaling, measuring, bleeding.

The steps follow the topic's own text (backend `angling_handbook.py`),
nothing beyond it. Their words are messages (`rigs.<key>.parts`), so a
picture never has to be redrawn per language. The parts the reader moves
are drawn in the brand colour, and a movement is an animated dashed arrow
(none with reduced motion). The shared parts (hook, reels, rod, hand, fish,
knife) are in `rigParts.tsx`. `rigTopics.ts` maps a topic to one drawing or
several (`knot-joining` has the blood knot and the surgeon's knot).

**Term cards.** `lib/terms.ts` and `components/terms/TermText.tsx`.
`messages.terms.items` holds 65 terms: tackle, knots, rigs, reels, technique
and water. Each has, per language, the forms its text uses (`match`) and a
one-sentence definition. `TERM_TOPIC` names the handbook topic that explains
each.

`LinkedText` underlines terms (solid) beside baits and lures (dotted), each
once per card or list and never the card's own topic. A tap opens the card,
which is a bottom sheet above the tab bar on a phone. Its link says
"see the drawing" when the topic has one. The cards appear in handbook
cards and their drawings' captions, the fish pages' lists and rod-and-reel
setups, the gear page, and Ask's AI answers.

Matching is longest form first. Latin-script forms match only as whole
words. A one-syllable Korean form (찌) matches only on its own or before a
particle. `NOT_WHEN_FOLLOWED` handles words with another meaning that every
language's handbook and fish pages turned up when read in full:

- 带倒刺的硬棘 / 미늘 달린 가시: a catfish's barbed spines, not a hook's barb;
- "jig a spoon": the verb;
- "spawn sac": a bait;
- カバーを外す: a reel's cover, not cover for fish;
- "maraña de raíces": a tangle of roots, not a backlash.

Some forms were left out instead: 合わせ (usually "to match"), and
ガイド/가이드 (as often the species guide as a rod's guides).

## Consequences

- Adding a handbook sentence with a new technical word: add the word to
  `terms.items` in en, zh, es, ja and ko, then rerun `scripts/zh_hant.py`.
  The dictionary test counts a `match` list as one entry, since each
  language has as many forms as it needs.
- A new drawing needs its steps' words in all five languages, as many as the
  drawing has pictures (RigDiagram.test.tsx checks both).
- React renders twice in development: a text works out which terms the texts
  above it linked (`earlier`) instead of sharing a set between renders.
- The step drawings and term texts have not been read by native speakers of
  Spanish, Japanese or Korean.
