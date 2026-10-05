# ADR 0011: Species guides — how to catch each fish

## Context

The app could tell a beginner *which* fish are confirmed in a lake and *where*
to stand, but not what to put on the end of the line. The project owner asked
for, per species: how to fish for it, what it eats and bites, and several
rod/reel/line/hook combinations.

This is advice a first-time angler will act on at the tackle shop and on the
water, so it gets the same treatment as the rest of the app's facts: sourced,
no invented numbers, and no regulations beyond what's needed to use bait
legally.

## Decision

**Reviewed content in code, not scraped or generated.** The twelve guides live
in `app/knowledge/species_guides.py` as typed data, one per species the TPWD
scraper can create (10 sport fish, 2 bait fish). They're served by
`GET /api/species/guides` and `GET /api/species/guides/{slug}` and shown in two
places: a "How to catch it" expander under each species in a lake's panel
(fetched on first open), and a `/fish` page listing every guide.

**How the content was produced:**
1. Three research passes, run in parallel, collected facts from state agencies
   (TPWD first; then Missouri, Minnesota, Oklahoma, Florida, Virginia,
   Arkansas, Utah, Alabama), Texas Parks & Wildlife magazine, and a few
   established publications. Each fact came back tagged with its URL.
2. The guides were written from those facts only. Where no source gave a
   number (a hook size for white bass, spotted bass, hybrids), a setup
   describes the jighead or lure weight instead of guessing.
3. An independent fact-check agent, which hadn't seen the writing, re-read
   the cited pages and checked every legal statement and numeric claim. It
   found 11 problems out of roughly 80 checked claims, all fixed before
   release:
   - one unsourced regulation claim, "some lakes have special length limits",
     which was removed;
   - a bait-transport rule summarised more broadly than TPWD's wording, and
     missing its exceptions;
   - a hook range misread: "1–3/0" had been written as "1/0–3/0";
   - three setups combining numbers from different tips or rigs in the same
     source;
   - five overstatements or unsupported wording.

**Rules the content follows, enforced by `tests/test_species_guides.py`:**
- Every species the scraper can create has a guide.
- Every tackle setup cites at least one known source, and the guide's source
  list includes it.
- Sport fish have at least two setups and at least one bait. Bait fish (the
  two shad) have no rod-and-reel setups, because TPWD says they rarely or
  almost never bite a hook. Instead they say how to get them (cast net) and
  what they're bait for.
- No bag, length, size or slot limits appear in any guide. Every guide links
  to TPWD's limits page instead (PRD §4.7).

**Sources are shown, and weighed.** Each setup shows its sources on the card.
The few that are a fishing-guide or tackle website, rather than an agency or
publication, are labelled "(fishing guide site)" in the UI.

**The scraper uses the guides for species metadata.** Species rows created by
the TPWD scraper used to get an empty scientific name, a placeholder profile
and a made-up "intermediate" difficulty. `upsert_species` now fills these from
the guide and backfills existing placeholder rows, but never overwrites a
value set by hand.

## Consequences

- Adding a species to the scraper's `KNOWN_SPECIES` now requires writing its
  guide; the test fails otherwise. That's intentional.
- Guides are Texas-focused (TPWD sources, Texas lakes in examples). Expanding
  to other states means adding state-specific notes, not rewriting setups.
- The AI advisor doesn't use the guides yet. The obvious next step is to pass
  the target species' setups into its facts so its gear and bait suggestions
  are grounded too, instead of the mock's generic placeholder. One catch: the
  species grounding check would reject a guide that names another species not
  confirmed in the lake, e.g. a shad guide mentioning "blue catfish". The
  facts passed in would need to exclude those cross-references.
- Tackle advice goes stale more slowly than regulations, but it isn't
  permanent: sources should be rechecked when the guides are next revised.
