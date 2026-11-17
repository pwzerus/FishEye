import { useEffect, useState } from "react";

import type { Locale } from "@/i18n/config";
import { useLocale } from "@/i18n/client";
import { listBaits } from "@/lib/api/client";
import type { BaitCard } from "@/lib/api/types";

// Fetched once per page load and language, and shared (backend app/api/baits.py).
// The cards' sentences come in the reader's language: an English card on a
// Chinese page was the owner's report (2026-11-16).
const baits = new Map<Locale, Promise<BaitCard[]>>();

export function useBaitCards(): BaitCard[] | null {
  const locale = useLocale();
  const [list, setList] = useState<{ locale: Locale; cards: BaitCard[] } | null>(null);
  useEffect(() => {
    let live = true;
    let request = baits.get(locale);
    if (!request) {
      request = listBaits(locale);
      baits.set(locale, request);
    }
    request
      .then((cards) => live && setList({ locale, cards }))
      .catch(() => {
        baits.delete(locale); // a later mount retries
      });
    return () => {
      live = false;
    };
  }, [locale]);
  return list && list.locale === locale ? list.cards : null;
}

export interface BaitMatch {
  start: number;
  end: number;
  card: BaitCard;
}

interface Matcher {
  re: RegExp;
  byName: Map<string, BaitCard>;
}

const matchers = new WeakMap<BaitCard[], Map<Locale, Matcher>>();

// English names (and Spanish) are matched as whole words; Chinese, Japanese
// and Korean have no spaces between words to anchor on.
const LATIN = /^[\p{Script=Latin}\d\s'-]+$/u;

function matcher(cards: BaitCard[], locale: Locale): Matcher {
  const cached = matchers.get(cards)?.get(locale);
  if (cached) return cached;
  const byName = new Map<string, BaitCard>();
  for (const c of cards) {
    // 繁體 pages get the Chinese names, made Traditional by the API (lang=zht).
    for (const lang of locale === "en" ? ["en"] : ["en", locale === "zht" ? "zh" : locale]) {
      for (const n of c.names[lang] ?? []) byName.set(n.toLowerCase(), c);
    }
  }
  const names = [...byName.keys()].sort((a, b) => b.length - a.length);
  const alts = names.map((n) => {
    const esc = n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return LATIN.test(n) ? `(?<![\\p{L}\\p{N}])${esc}(?![\\p{L}\\p{N}])` : esc;
  });
  const m = { re: new RegExp(alts.join("|"), "giu"), byName };
  if (!matchers.has(cards)) matchers.set(cards, new Map());
  matchers.get(cards)!.set(locale, m);
  return m;
}

/** The baits and lures a text names: each term once (its first mention),
 * at most `max`, and not a term about the page's own fish (shad on a shad's
 * page). */
export function findBaits(
  text: string,
  cards: BaitCard[],
  locale: Locale,
  { fish = null, max = 3, seen = new Set<string>() }: { fish?: string | null; max?: number; seen?: Set<string> } = {},
): BaitMatch[] {
  if (!text || cards.length === 0) return [];
  const { re, byName } = matcher(cards, locale);
  const out: BaitMatch[] = [];
  re.lastIndex = 0;
  for (const m of text.matchAll(re)) {
    const card = byName.get(m[0].toLowerCase());
    if (!card || seen.has(card.id) || (fish && card.skip_on.includes(fish))) continue;
    seen.add(card.id);
    out.push({ start: m.index ?? 0, end: (m.index ?? 0) + m[0].length, card });
    if (out.length >= max) break;
  }
  return out;
}
