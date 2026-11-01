# 42. What Ask couldn't answer, and answers from the lake data

Date: 2026-11-01

## Context

Ask searched the guides and handbook and nothing else. That left two gaps. We
had no record of what people asked and didn't get answered, so what to write
next was a guess. And Ask couldn't say whether a fish was in a lake, or which
lakes had it, although the database knows.

## Decision

**Misses are recorded, without who asked** (`services/ask_misses.py`, the admin
console's Ask misses tab). A search that shows nothing keeps its question,
language, state and fish. No account, no IP. Email addresses, phone numbers and
links are taken out first. A repeat on the same day is a count on one row, and
rows go after 90 days. The privacy policy says so.

**A lake named, or "where to go", is answered from the database with no model**
(`services/rag/lake_facts.py`). The answer is a card beside the guide passages,
not text the model writes, so it can only say what is on record, with the
sources one tap away. "No record" is worded as no record, never as absent: most
lakes have never been surveyed. Closed lakes aren't suggested. A name in a
sentence has to match a lake's whole name give or take "lake" or "reservoir",
so "a small lake" and "near the bottom" look up nothing. Only the place after
"near" leaves the server, as the map's search already does.

**Guides written after the photo model was built stay out of its class list**
(`GUIDED_SINCE_BUILD`, `CLAIM_GROUPS`). A class's kind is part of the model's
digest, and a changed list refuses to load until rebuilt and retrained. So they
are checked through the existing classes until the next rebuild.

**The same rule stated for every state answers in any state**
(`rule-clean-drain-dry-us`), which the check that keeps other states' rules out
of an answer now allows.

## Consequences

- The next guides to write come from the misses tab, not from a guess.
- The lake facts don't reach the AI summary, which still answers from guide
  passages alone (ADR 0023). Worth revisiting once the card has been used.
- Bare "trout" and "perch" now route to several guides, so Texan "perch"
  (sunfish) and northern "perch" (yellow perch) both get an answer.
