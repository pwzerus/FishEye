# 0068. An address for each language

Date: 2026-11-23. Status: accepted (deploy waits on the owner).

## Context

The site is written in English, Simplified and Traditional Chinese, Spanish,
Japanese and Korean, but every page had one address. The language was a
cookie the language menu set, read by the root layout, so the same address
showed one visitor Chinese and another English.

Search engines send no cookie, so they saw every page in English only. On
2026-11-23 Google had indexed no page of fisheyefishing.com at all (a
`site:` search found nothing; Search Console had not been set up), and once
it does, a search in Chinese ("德州钓鱼执照") could still never find the
Chinese rules page: Google records pages by address, and each address was
English to it. The owner promotes FishEye mostly in Chinese (Xiaohongshu),
and Google recommends a separate address for each language version rather
than a cookie
(developers.google.com/search/docs/specialty/international/managing-multi-regional-sites).
The owner asked for it the same day, along with a home page title that says
what FishEye is ("FishEye" alone is also a camera lens) and the site's name
as structured data.

## Decision

- **Each language has an address under the same domain:** `/zh/...`,
  `/zh-tw/...`, `/es/...`, `/ko/...`, `/ja/...` (`LOCALE_PATHS` in
  `i18n/config.ts`). English keeps the plain addresses, so no existing link
  changes. No new domain or server.
- **The proxy shows a language's address as the plain page in that
  language** (`src/proxy.ts`, Next 16's proxy, formerly middleware). It runs
  only on those addresses (its matcher), rewrites to the plain path with an
  `x-fisheye-locale` request header, and sets the language cookie so links or
  scripts that lead to a plain address keep the language for that visitor.
  Search engines keep no cookies from one page to the next.
- **The page's language is the address's, else the cookie's, else English**
  (`getLocale` in `i18n/server.ts`). Moving every page under `app/[lang]/`,
  the pattern in Next's internationalization guide, would have moved every
  route and changed the English addresses; the rewrite keeps the pages where
  they are.
- **Links keep the page's language** (`components/LocaleLink.tsx`, used for
  every `next/link` in the app): on a page rendered in Chinese, `/rules`
  leads to `/zh/rules`. They follow the rendered language, so a visitor whose
  cookie says Chinese moves onto Chinese addresses at their first click, and
  a search engine, always English at a plain address, follows plain links.
  `router.push` calls are left as they are: the cookie keeps the language.
- **Every page names all its addresses** (`pageAlternates`): the one being
  read as canonical, every language's as hreflang (languages and scripts,
  not countries: `zh-Hans`, `zh-Hant`), and the plain one as `x-default`. The
  sitemap lists each page in all six languages with the same alternates, and
  robots.txt keeps account pages out at every language's address.
- **The language menu goes to the new language's address** with a full page
  load (`lib/navigate.ts`): the root layout, which holds the language for
  client components, isn't re-rendered by a soft navigation between two
  addresses of one route. Where the address stays the same (back to English
  on a plain address), it refreshes as before.
- **Paths compared with routes ignore the language segment**
  (`i18n/pagePath.ts`): the header's current tab, the footer, the terms
  notice, the account menu's sign-in return and the visit counter, which
  counts `/zh/rules/x` as the page `/rules/…`.
- **The home page's title says what the site is** (`meta.homeTitle`, "FishEye:
  where to fish, what to use, and your state's fishing rules" and its
  translations), and the home page carries WebSite structured data with the
  name "FishEye" and the alternate names "FishEye Fishing" and
  "fisheyefishing.com" (Google's site names).

## Consequences

- Google can list each language's pages in that language's searches once it
  indexes the site; that still needs Search Console (the owner's account and
  a DNS record at Network Solutions) and time.
- A shared link carries its language: a Chinese page sent over WeChat opens
  in Chinese.
- Opening a language's address changes the visitor's saved language, as
  choosing it in the menu does.
- Pages in client state (a half-written question in Ask) are reloaded when
  the language changes; before, they were refreshed in place.
- The sitemap is six times as long (564 entries on 2026-11-23).
- `usePagePath` lives outside `i18n/client.tsx` on purpose: tests mock
  `next/navigation` with a factory that imports the app's providers, and an
  import of `next/navigation` in `i18n/client.tsx` made those tests wait on
  themselves forever.
