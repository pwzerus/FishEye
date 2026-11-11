# 0055. 繁體中文, made from the Simplified

Date: 2026-11-11. Status: accepted.

## Context

The owner asked for Traditional Chinese beside the Simplified. FishEye's
Chinese is one body of text, written and reviewed in Simplified: the site's
own words (`frontend/src/i18n/zh.ts`, the zh tables in `names.ts` and
`weather.ts`), and the API's (the translation tables of ADR 0052, the trip
plan, refusals, Ask's replies). Writing all of it a second time would double
the work of every later edit, and the two would drift.

## Decision

**Traditional is made from the Simplified, never written by hand.** OpenCC's
`s2twp` (Apache-2.0) turns the characters Traditional and the words Taiwan's
(登录 → 登入, 信息 → 資訊, 密歇根州 → 密西根州). A short list, `FIXES`, puts back
what that rule gets wrong on a fishing site: its computer words where this site
means something else (发布 → 釋出 → 發布, 审核 → 稽核 → 審核, 权限 → 許可權 → 權限,
局部多云 → 區域性多雲 → 局部多雲), a misread measure word (只能 → 隻能 → 只能),
and the mainland words Taiwan says otherwise (邮箱 → 電子郵件, 反馈 → 意見回饋,
浮漂 → 浮標, 渔轮 → 捲線器, 得克萨斯 → 德克薩斯). Every word the rule swaps was
read once (`scripts/zh_hant.py --review`, 281 swaps).

The language is `zht` (`<html lang="zh-TW">`, so phones pick Traditional
glyphs and Taiwan's punctuation); the menu says 简体中文 and 繁體中文, and a
browser set to zh-TW, zh-HK, zh-MO or zh-Hant is offered the second.

**The site's own words are made ahead of time.** `frontend/scripts/zh_hant.py`
writes `src/i18n/zht.ts` from `zh.ts`, and a `zht:` entry beside every `zh:`
entry in `names.ts`, `weather.ts` and the /start kit list. The type check
fails if a table lacks one. Run it after changing any Chinese there; the
generated files say so at the top.

**The API's words are made as they go out.** `api/zh_hant.TraditionalChinese`
is the innermost middleware: a request with `lang=zht` (in the query, or in a
JSON body: Ask, the plan) goes to its route as `zh`, and the JSON answer comes
back Traditional, its `lang` and `*_lang` fields saying `zh-Hant`. No route
knows about `zht`. A question typed in Traditional is turned Simplified first
(`t2s`, characters only: `tw2sp` writes 鯰魚 as 鲇鱼 where the guides say
鲶鱼), and Ask's Chinese words gained Taiwan's 卷线器 (reel) and 浮标 (bobber).
Refusals (`error_text.tr`) and the reset mail read the language cookie and do
the same.

## Consequences

- One source: a fix to the Chinese is a fix to both, after the generator runs.
- What people write (catch titles, comments, names) is shown as written.
- A catch alert made in Traditional is stored as Chinese and would be mailed
  in Simplified; alerts send nothing yet (ADR 0054), so this waits for mail.
- Hong Kong's words differ from Taiwan's in places; FishEye writes Taiwan's.
- The backend needs `opencc==1.4.2` (wheels for Linux and Windows).
