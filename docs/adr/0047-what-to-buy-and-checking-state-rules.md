# 0047. What to buy, with photos; every state's rules checked again

Date: 2026-11-06. Status: accepted (local, not deployed).

## Context

FishEye is for learning to fish (ADR 0046). The guides say "a No. 6 hook
under a bobber with a split shot", which means nothing to someone who has
never seen those things on a shelf. The product owner asked for pictures of
baits, hooks, rods, reels and line, from images that may be used
commercially, so beginners know what to buy. They also asked that every
state's rules be checked again for being true and useful.

## Decision

- A gear catalogue (`app/knowledge/gear.py`): 52 things, each with what it
  is for, one tip, the fish it suits (guide slugs), the handbook topic that
  explains it, and whether it belongs in a first kit (11 items). Our own
  words, no brands, no prices. Served at `GET /api/gear`.
- Photos from Wikimedia Commons only, public domain, CC0 or CC BY, picked by
  eye (46 items); hot-linked with author and licence under each one. No SA,
  so the same files could train a model later.
- Shown in four places: the new `/gear` page (first kit on top, then by
  kind), a "Gear for this fish" strip on each fish page, small photos on the
  handbook cards whose topic explains the item, and a home-page card. A new
  handbook topic, "What to buy to start fishing", lets Ask answer "what gear
  does a beginner need" and links the page.
- State rules: every link fetched, every license age and bait-rule detail
  compared with its cited page (docs/data-sources.md, "Checked again
  2026-11-06"). Seven license entries corrected, five states added, so all
  50 and DC have one; one unsupported bait detail removed (Rhode Island).

## Not done

- No gear recognition from a photo (since done another way: ADR 0048). BioCLIP knows organisms, not lures, and
  Commons has a handful of open photos per item, not the hundreds a reliable
  classifier needs. The photos are for showing, not training, for now.
- Six items have no photo (circle hooks, wire leaders, plastic worms,
  lipless crankbaits, tackle box, bait bucket).
- Gear text is in English, like the handbook; names and categories are
  translated into the four other languages.
