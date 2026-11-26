# 0069. A quick take on every long handbook card

Date: 2026-11-25. Status: accepted (deploy waits on the owner).

## Context

The owner, reading the handbook on a phone on 2026-11-25: too many words;
pictures and a short version first. A prototype on "Playing a fish and
landing it" (one line, six moving pictures, four points, and the card's own
text folded under "Full explanation") went live in 375cefb, and the owner
asked the same day for every long card to follow it.

## Decision

- **Which cards:** every general card (region "all") of 72 words or more,
  93 of the 117 general cards. The 115 state cards (licenses, limits, clean
  drain dry, a state's first trip) keep their text as it is: each states one
  state's rules beside its official page, and a summary that drops a
  condition ("a pond owned by a government is not private") would misstate
  the law. That is the owner's call to change.
- **The text lives in the backend, beside the cards:**
  `app/knowledge/handbook_quick.py` (English: a line and 2 to 5 points per
  card) and `translations/<lang>_quick.json` for zh, es, ja and ko, keyed
  `<topic>.lead` and `<topic>.points#<i>` like the handbook's own table.
  `GET /api/species/handbook` sends it as `quick: {lead, points, lang}`;
  Traditional Chinese comes from the Simplified at request time, as the rest
  of the Chinese does (ADR 0058's tables, `api/zh_hant.py`).
- **Written from the card's own sentences:** no fact or number the card
  doesn't state (a test checks the numbers), its conditions and hedges kept
  ("unless the person feels sick", "some states"). A line of at most 120
  characters, points of at most 110, no colon or semicolon joining two
  sentences. Four agents drafted them from the cards; every draft was read
  against its card, the safety and health cards line by line. The
  translations reuse the terms of the card's own translation, which sits
  right under them.
- **The picture sits between the line and the points:** the card's steps
  moving (only landing so far, `QuickDrawings.tsx`), else its drawing (38
  cards), else its gear photos (11), else none (43). Points don't repeat
  what the drawing shows; the gear photos then don't show twice.
- **The card's own text stays,** folded under "Full explanation" and open
  while searching. Ask still cites the cards' own text; a quick take is not
  a passage.
- A "(see …)" in a quick take links like one in the card's text (the
  handbook passes its titles). Terms are underlined in the points, not in
  the line.

## Consequences

- Changing a card means checking its quick take too: `handbook_quick.py` and
  the four tables. `tests/test_translations.py` fails on a missing or extra
  key and on a lost number; `tests/test_handbook.py` on a number the card
  doesn't state.
- Found on the way: the salmon-run card said "They die after spawning" right
  after brown and brook trout, which don't. It now says "The salmon die
  after spawning" in English, Spanish, Japanese and Korean (the Chinese
  already said 鲑鱼), as the salmon card does.
- Also found: "(see Clean, drain and dry)" linked only "Clean" in English,
  Spanish and Korean, because a title's first part was cut at its first
  comma even when its colon came later. `names()` in `lib/seeRefs.ts` now
  cuts at each kind of mark. And the Chinese dough-bait card's
  "面粉或玉米粉加热水" could be read as "heat the water"; it now says
  "和热水调成".
- Left for the owner: the Chinese uses 调 (中调竿, 轻调纺车竿) for a rod's
  power in about 50 places, as Chinese shops write "M调", while the rod card
  defines 调性 as action. The quick takes follow their cards.
