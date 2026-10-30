# ADR 0041: The site in English, Chinese, Spanish, Korean and Japanese

## Status
Accepted. Built and tested locally on 2026-10-30 (Korean and Japanese the
same day, then a wording review of all four); not deployed.

## Context

The 2026-10-29 personas put two groups first after the teen beginner: the
visiting angler who reads Chinese more easily than English, and, in Texas
and California especially, families whose first language is Spanish. The
first answer was Chinese hints for a Chinese-language browser (fish names
under the English ones). The owner asked for the pages to switch language:
English by default, then Chinese and Spanish; then Korean and Japanese, and
a check of all four that none reads like machine translation.

## Decision

- **One cookie, same URLs.** `fisheye.lang` (`en`, `zh`, `es`, `ko`, `ja`)
  is set by the language button in the header and read by the root layout,
  so a page renders on the server in the chosen language and links don't
  change. English is the default and the fallback. A browser set to another
  of the site's languages that hasn't chosen gets one line, in that
  language, offering it; English stays until the person says.
- **Dictionaries, typed.** `src/i18n/en.ts` holds every string the site
  shows; the others are typed as it, so a string added in English and not
  translated fails the type check. A string with something in it is a
  function (`t.catch.count(3)`). Client components read them with `useT()`,
  server components with `getT()`. Dates and numbers use the language's
  format (US formats for Spanish); the plan's times are 24-hour in Chinese,
  Japanese and Korean, each with its own range mark (5:00–8:00, 5:00〜8:00,
  5:00~8:00), and wind speeds read as each language writes them (时速 words,
  時速10マイル, 시속 10마일).
- **Each language's order.** A sentence split around a link or a name has
  its words before and after in every language (`tieWith`, `knot`,
  `tieEnd`), and the components add no spaces or full stops of their own:
  Japanese and Korean put the verb after the link ("針はインプルーブド
  クリンチノットで結びます。"), and English full stops no longer follow
  Chinese text. Korean templates never put a particle that changes with the
  word before it (을/를, 이/가, 은/는, 와/과, 으로/로) right after an
  inserted name; they use ones that don't (에서, 의, 처럼, 인 것 같아요).
- **Register.** Japanese sentences in です・ます and Korean in 해요체, buttons
  and labels as short nouns, as apps in those languages write them. No "you"
  where the language leaves it out (自分, 나, 我 for one's own catches).
- **Names by hand.** Fish names (19), Handbook topic titles (75) and
  categories, US state names (Korean as the National Institute of Korean
  Language spells them), the beginner's kit, the photo check's look-alike
  groups, and today's plan's lure and bait sentences (147,
  `backend/app/knowledge/plan_text.py`) are translated by hand, in each
  country's anglers' words: 좁쌀봉돌 and ガン玉 for split shot, 바이브레이션
  and バイブレーション for a lipless crankbait, ダウンショット, 떡밥, 朝マズメ,
  "acocil". The English name of a fish or a tackle item stays beside it,
  because it is the one on the regulations, at the tackle shop and on the
  lake's sign; the shopping list shows the English large, for the clerk.
  Hook sizes say they are US sizes: a Korean 6호 or a Japanese 6号 is a
  different hook.
- **Type.** `<html lang>` (ko-KR, ja-JP, zh-CN) picks Korean, Japanese or
  Chinese glyphs for the characters they share. Korean wraps between words
  (`word-break: keep-all`), Japanese keeps small kana off the start of a
  line, and emphasis is upright in all three (they have no italics; a
  browser slants the glyphs instead).
- **Ask.** A Spanish, Korean or Japanese question is put into the English
  words the guides use through a glossary of anglers' words
  (`services/rag/es.py`, `ko.py`, `ja.py`), as a Chinese one already was
  (ADR 0025). Japanese is told apart from Chinese by its kana, and what the
  Korean and Japanese glossaries don't know is dropped, so leftover kanji
  never reach the Chinese rules. Ask's own sentences (the line before the
  passages, the three kinds of "not covered", other states' rules) come back
  in the question's language, or the site's for an English question
  (`services/rag/replies.py`). A quoted passage's heading is the site's own
  heading for that section, in the reader's language.
- **What stays English.** The guides' and Handbook's text, the agencies'
  facts and rule lines, lake and river names, NWS alerts, and the legal
  pages. A note says so where it matters (the fish guide, the Handbook,
  Ask, the legal pages), and those blocks are marked `lang="en"` so a
  screen reader and the browser's own translator treat them as English.
- **Admin stays English.** It is for the operator.

## The wording review (2026-10-30)

Each dictionary was read through, then the pages were read in each language
with real data in them, where most of the problems were. Changed:

- Chinese (about 70 strings): English word order and translationese
  ("找到你的水域", "你的下一个钓鱼日", "这条渔获不在这里", "照片可能骗过任何
  模型", "风 5 to 10 mph，来自东北"), English full stops after Chinese text,
  the meteorological 16-point compass (东北偏北), 下水坡道 for a boat ramp.
- Spanish (about 60): "parece un(a) …" in five photo-check lines, "entrada"
  where Spanish says "acceso", literal lines ("Encuentra tu agua", "son su
  palabra", "Buscar lugares en su lugar"), gendered wording ("Bienvenido",
  "¿Atorado?"), English title case on a status pill.
- All languages: an unnamed OpenStreetMap access point showed its generic
  English name and then its kind again ("Boat ramp (OpenStreetMap) —
  ボートスロープ"); it now shows its kind once. The photo check named the fish
  in English inside a translated sentence; it names it in the reader's
  language.

`src/i18n/i18n.test.tsx` keeps them from coming back: no "(a)"-style
template marks, double spaces or English full stops after Chinese or
Japanese, and the split sentences are checked joined.

## Consequences

- Every new string needs five versions; the type check enforces it, and
  `i18n.test.tsx` checks none is empty.
- The review was done without native speakers. Korean, Japanese and
  Spanish still want one, the rules wording first.
- The guides' text is the biggest gap: a Chinese, Spanish, Korean or
  Japanese reader gets the headings, names and the plan in their language,
  and the paragraphs in English (the browser can translate those; the
  translate guard keeps React from crashing when it does). Translating the
  guides and rules is a content job that needs review, rules first.
- The Korean and Japanese Ask glossaries are small and hand-written: a
  question in words they don't have finds less than the same question in
  English. The tests hold the common ones (bait, hook size, knots, licence,
  how many to keep).
- Rules are never translated into something that reads like a rule: the
  rule lines stay English with the official link.
