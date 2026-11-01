# 43. One sources page, not sources on every line

Date: 2026-11-01

## Context

The guides named their sources in their sentences ("... not deep (Take Me
Fishing)"), under every tackle setup and handbook topic, and again in a list at
the bottom of each fish page. Someone reading about bait had to read past all
of it. The sources are there so the facts can be checked and credited; they
aren't what the reader came for.

## Decision

**The sources live on `/sources`.** It is grouped by what they were used for:
each fish (its guide, then each setup), the handbook by category, state rules
by state, the lake and map datasets, and photos. It is built from the same
APIs the pages read, so a new guide or topic is listed without touching it.

**A page has one small link to its part of that page** (`/sources#fish-walleye`,
`/sources#handbook`), and the site's footer links to the whole page.

**Sentences say the fact without the source.** A credit in brackets is gone, and
"TPWD suggests hooks size 6-14" is "hooks size 6-14". An agency stays when it
is the subject of the fact, not the credit for it: "TPWD stocks", "report it to
CDFW". A place stays when the fact depends on it, as Pennsylvania's months do.

**Some things stay where they are:**

- A state's rule keeps its official link beside it (bait rules, license topics,
  limits): the reader needs it to check the rule before going.
- A photo keeps its credit, which CC BY and CC BY-SA ask for with the work.
- The map keeps © OpenStreetMap contributors, which ODbL asks for.
- A lake's Sources tab and "Data: <agency>" stay: there the source is the
  evidence ("TPWD's 2022 survey recorded ...").
- Ask's cards keep the small source line for now. The card is the answer, and
  its title is the only link to where the passage sits.

## Consequences

- Each fact's record still names its pages (`source_ids`), and a test requires
  every guide and topic to have one, so nothing has lost its source.
- Sources can be named per guide and per setup, not per paragraph: the data
  doesn't record which sentence came from which page. Writing that down would
  mean re-reading every page.
- The data-sourcing rule changed with this (rule 3, rule 7). This is a reading
  of the licences, not legal advice; have a lawyer look before launch.
