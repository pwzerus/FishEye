# 0051. A question library, reached second by Ask

Date: 2026-11-09. Status: accepted.

## Context

The guides and handbook are reviewed and sourced, and they answer what a
beginner needs to catch a fish. They say little about choosing gear, reel
trouble, line problems or what to buy for a budget, which is much of what
anglers ask. The product owner asked for a set of 494 such questions to be
answered in English and Chinese, and on 2026-11-09 decided that those
answers belong in FishEye, including the ones that rest on general fishing
knowledge. The questions only say what to write about.

## Decision

**The library** is `knowledge/qa_library.json` (generated) and
`knowledge/angling_qa.py`. Each answer has a `basis`, shown on its card:
FishEye's guides, official sources and fisheries booklets, a tackle maker,
or general knowledge. "General knowledge" means no published source was
checked, and the page says so. This is the one place in FishEye where an
answer may rest on no source; the guides' rule (ADR 0011) is unchanged.

**A forum answer is still never a source.** 35 answers had been improved
from forum and article-site reading. In FishEye they use the wording they
had before that reading. The questions themselves are new wording; no post
text, user name or link to a post is stored (`docs/data-sources.md`).

**Ask reaches it second** (`services/rag/question_library.py`). The library
is not added to the guides' index: 494 question-shaped passages would shift
every BM25 average and crowd out the reviewed cards. It has its own index.
It adds nothing when a state's rule is the best match or nothing clearly
matches; it answers when the guides found nothing; and when a library
question asks nearly what the user asked, its card joins the guides' cards as
a fifth, so none is pushed out. It goes first if the guides' best card doesn't
plainly answer (its title shares less than half of the asker's weighted
words), second if it does.

A clear match is measured on the question's own words, weighted by rarity,
so a word the library has never seen counts against it. A Chinese question
is also compared with the Chinese wording by character pairs.

**In Chinese** the card's title and text are the library's own Chinese. The
other site languages show English.

**`/questions`** shows every answer under its own anchor, where Ask's
citations link, and `/sources#questions` lists the pages cited.

## Measurements (2026-11-09, hybrid retrieval)

- Each English question finds its own answer first: 494 of 494. Each Chinese
  question: first 492 of 494, in the top two 494 of 494.
- 54 off-topic questions in both languages, including "film reel" and
  "guitar strings": none finds anything.
- The 330 eval cases through the whole Ask search, library on and off: none
  loses its relevant passage (a library card only ever adds to the list).

## Consequences

- Ask now answers many gear questions it used to call not covered.
- 231 answers are general knowledge and no expert has reviewed them. They
  are labelled, and the review is still to do.
- The vectors for the library are made once, about 500 more passages, and
  cached like the guides' (ADR 0025).
