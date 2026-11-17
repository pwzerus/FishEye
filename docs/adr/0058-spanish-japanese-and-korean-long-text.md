# 0058. The long text in Spanish, Japanese and Korean

Date: 2026-11-16. Status: accepted.

## Context

The owner asked Ask a question in Spanish, followed its link and landed on a
page that was half Spanish and half English. The interface had been translated,
but the guides, the handbook, the gear list, the states' bait rules and the
question library existed only in English and Chinese (ADR 0052). Ask in Spanish,
Japanese and Korean found the right passages, then quoted them in English under
"(en inglés)", and the page it linked to said the guide was in English for now.

## Decision

**The same tables, three more languages.** `knowledge/translations/` gains
`{es,ja,ko}_{guides,handbook,bait_rules,gear}.json`, keyed exactly like the
Chinese ones, and `{es,ja,ko}_qa.json` for the question library (Chinese keeps
its own fields in `angling_qa.py`). `LANGUAGES` is now zh, es, ja and ko; no
other value reaches the file system. Every string is translated, 3,690 per
language: guides 1,077, handbook 844, bait rules 167, gear 104, question
library 1,498. The per-state license and limits topics are written from the
state data, as the Chinese ones are.

**Written for each language's anglers.** US Spanish leaning Mexican (lobina,
bagre, carnada, mojarra de agallas azules, carrete de botón), Japanese in
です・ます with Japanese tackle words (道糸, ハリス, ガン玉, 遊動ウキ, 中通しオモリ),
Korean in 해요체 (원줄, 목줄, 좁쌀봉돌, 유동찌, 구멍봉돌). Fish, gear and handbook
names follow the frontend's `names.ts`. Agency, place, brand and document names
stay English and link to the source.

**Ask quotes them.** `Passage.text_tr` and `title_tr` hold (language, text)
pairs built from the same tables. A citation comes back in the asker's language
with its `lang`, and when every passage quoted is translated the intro no
longer says "(en inglés)" (`replies.passages_intro_translated`). The English
stays what is searched and what a summary reads, so no vector changes.

**Pages.** `?lang=es|ja|ko` works as `?lang=zh` does: `text_lang`, `body_lang`,
`bait_rules_lang` and each question's `lang` say what came back, and the
"still in English" note goes away. The English name under a translated fish or
gear name stays on purpose: it is what signs, regulations and packaging say.

**Editing English means editing four languages.** `tests/test_translations.py`
fails if a string is added or removed without its Spanish, Japanese and Korean,
if a number is lost, or if a long sentence is left in English.

## Consequences

- A change to the English text needs the same change in four tables; the
  failing test names the keys.
- The translations were written by the coding assistant and checked by script
  (keys, numbers, script) and by reading for consistent terms. No native
  speaker has read them yet. The Spanish is the first to show a tester, since
  that is where the report came from.
- Traditional Chinese is still made from the Simplified (ADR 0055).

## What was not done

- Translating at request time with a model: a cost on every page view, slower
  pages, wording that changes between visits, and nothing a test can hold.
- Keeping the English note and leaving the text in English: that is the half
  translation the owner reported.

## Addendum, 2026-11-16: the bait cards and a scan of every page

The owner opened a bait card on a Chinese fish page and read English. The
cards (`/api/baits`) were built from the handbook and guides but never read
their tables. They now take `lang` like the other routes: `what`, `why`,
`how` and each fish's reason come from `<lang>_handbook.json` and
`<lang>_guides.json`, the "Why they work:" label is cut in every language
(the card has its own heading), and `lang` says what came back. 繁體 pages
match baits by the Chinese names the API returns in Traditional.

Also changed after a headless-browser scan of every page (static pages,
28 fish, 51 states, Ask) in zh, zht, es, ja and ko, every bait and term card
opened:

- A handbook card's title no longer has its English title under it. Fish
  and gear keep their English names: those are what regulations and
  packaging say.
- `/sources` shows a guide's setups by their translated names.
- "<agency>: size and bag limits" is FishEye's wording, so its second half
  is translated (`lib/sourceLabel.ts`). Other sources keep their own English
  titles, which are what the linked pages say.
- `i18n.test.tsx` fails if a message of three or more words is left the
  same as the English.

What stays English on purpose: source titles, photo credits, agency,
program and brand names inside translated sentences, and the English names
under fish and gear.
