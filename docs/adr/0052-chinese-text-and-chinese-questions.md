# 0052. The long text in Chinese, and Chinese questions on Ask

Date: 2026-11-10. Status: accepted.

## Context

A tester who reads Chinese reported two things: much of the site stayed in
English after switching language, and Ask "answers something else", above all
in Chinese. The first was plain: the guides, the handbook, the gear list and
the states' bait rules existed only in English. The second was measured on 40
everyday questions written from that complaint and labelled by hand: the right
passage in the top four for 28 of them (MRR 0.55), and the passages it did find
were shown in English under a Chinese sentence saying so. The existing Chinese
eval was at 100%, because its questions use words the glossary already knew.

## Decision

**Translations are tables beside the English** (`knowledge/translations/`), one
JSON file per text and language, keyed by where a sentence sits
(`bait-worms#2`, `bluegill.setups#1.rod`, `TX#0`). English stays the source. The
API takes `?lang=zh` and says what it returned (`text_lang`, `body_lang`,
`bait_rules_lang`), so a page can say when something is still in English. Only
languages in `LANGUAGES` reach the file system. `tests/test_translations.py`
fails if a sentence is added, removed or loses a number; so **editing English
text means editing its Chinese too**.

**Ask quotes the Chinese** where there is one. `Passage.text_zh` is built from
the same tables. The English text stays what is searched and what a summary
reads, so no passage vector changes.

**Chinese questions are read three ways.** The glossary gained about 60 everyday
words. Two lines of rule-based gate words were added for what was being turned
away. And `zh_search.ZhTopics` ranks the handbook's Chinese titles and text by
pairs of characters, as one more list in the fusion, at half weight.

**"Where can I fish near me"** gets told to use the map, in the asker's language.
Only the map knows where the person is.

**Misspellings** (`spelling.py`): a word in an English question that nothing in
the guides contains is replaced by the fishing word it's one slip from, so "waht
bate for catfsh" finds the catfish bait passages. Only what is searched changes.
The first version corrected towards any fishing term and turned real words into
fishing ones ("story" into "storm", "measured" into "measure"). So it now
corrects only towards words that mean nothing but fishing, and real words near
them are listed and left alone: of a 125,000-word English dictionary it changes
four, two of them on purpose ("bate", "lour").

## What did not work

Measured on the same sets before being dropped:

- BM25 on pairs of characters over **every** passage. Each fish's sections repeat
  the same few words, and they crowded out the handbook topic that answers.
- Embedding the Chinese passages and searching them with the Chinese question.
  No better than the English vectors with the glossary's words added.
- Using the topic match to let a question past the on-topic gate. It let through
  "红烧肉怎么做" and "金鱼怎么养".

## Results

`python -m app.eval.rag_runner --compare`, semantic model on:

| | when first measured | now |
|---|---|---|
| 40 everyday questions, hit@4 | 70% (MRR 0.55), before any of this | 100% (0.85), tuned on these |
| 30 more, written after the first round of words, hit@4 | 57% (MRR 0.47) | 100% (0.90), tuned on these |
| 26 written after the glossary was finished, hit@4 | 81% (MRR 0.68) | the same, nothing tuned on them |
| Earlier Chinese set, MRR | 0.91 | 0.94 |

The 26 are the honest number for a question nobody has seen. All 96 are now
`ZH_EVERYDAY_CASES` (95%, MRR 0.82). English sets did not move, and no off-topic
Chinese question got through.

## Consequences

This is still search. It finds the passage that answers; it doesn't write an
answer or look anything up elsewhere. The tester also asked for an AI that
reads FishEye's material first and offers a web search when that falls short.
The AI summary already covers the first half for signed-in users, within the
monthly cap. Web search, and running the summary for everyone, spend money and
are the product owner's decision.

Chinese text was written by hand from the English, sentence by sentence. Agency
names, place names and fish with no common Chinese name stay in English, so that
they match signs and shops.
