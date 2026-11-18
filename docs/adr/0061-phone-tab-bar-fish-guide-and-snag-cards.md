# 0061. Home in the phone's tab bar, a shorter fish guide, snag cards

Date: 2026-11-17. Status: accepted.

## Context

The owner opened FishEye from the iPhone home screen (2026-11-17) and
reported three things:

- The bottom bar had no Home. A home-screen app has no address bar and no
  back button, so the only way home was the logo, and on the home page the
  bar showed nothing selected. The bar also sat on the home indicator: the
  viewport didn't say `viewport-fit=cover`, so `env(safe-area-inset-bottom)`
  was 0 and the bars' padding for it did nothing.
- The fish guide still had too many words before the first fish: an
  eyebrow, a two-line lede, five boxed links two by two (one jumped down the
  page, one repeated the Handbook tab), the state picker on its own row, and
  one fish per row with "Bait and gear →" under each.
- What to do when snagged: is it weeds or a rock or a fish, what to try,
  when to cut the line, how to tie back on, with links and drawings.

## Decision

**Tab bar.** The phone's bar has six tabs, Home first, with short labels of
their own (`messages nav.tabs`: Map, Fish; 鱼类; Mapa, Peces; 釣り場, 手引き;
낚시터, 어종), so each stays on one line from 320 px up. Spanish, the longest,
gets a smaller size under 390 px. The desktop header is unchanged (the logo
is home there). The viewport is `viewport-fit=cover`; the bars already pad
themselves by the insets, and `html` pads its sides for a notch in
landscape.

**Fish guide.** Title, a one-line lede, three pill links (identify from a
photo, filled; what to buy; common questions), then the filters, with the
search and the state picker on one row. On a phone the fish are two to a
row, name and level only: the whole card opens the fish.

**Snag cards.** `trouble-snags` is rewritten: fish or snag (light pressure:
a fish gives or moves, a snag doesn't), weeds or rock (often unseen, and the
same steps work for both, gentlest first), jiggle, change angle, pluck the
line, free it by hand only from where you stand, and after a few tries break
the line by pulling with the rod pointed at the snag, which leaves far less
line in the water than cutting it at the reel. `trouble-retie` is new:
spares to carry, cut off frayed line, the clinch or Palomar knot, put back
the shot and bobber, refill a low spool. Sources: US Forest Service, NOAA,
Missouri, Minnesota, Texas and New York agencies, and one newspaper column
(docs/data-sources.md). Six step drawings for the first (four new), three
for the second; the knots and rigs they name are underlined and open their
own cards and drawings. Five eval questions, the owner's among them, and
Chinese ways of asking were added.

**Terms keep their punctuation.** A term is a button, and a line could
break between it and the 。 or ” touching it. `LinkedText` now wraps a term
with that punctuation in a span that doesn't break.

## Consequences

- A sixth tab means short labels; a new language needs `nav.tabs` too (the
  type check asks for it).
- No usable source gave a way to tell weeds from rock by feel (the one that
  did, MeatEater, forbids robots), so the card doesn't claim one.
- Not checked on a real iPhone: the safe-area change is the documented
  behaviour of `viewport-fit=cover`, and headless Chrome reports no insets.
