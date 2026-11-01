import { useEffect, useState } from "react";

import type { Locale } from "@/i18n/config";
import { listBaits } from "@/lib/api/client";
import type { BaitCard } from "@/lib/api/types";

// Fetched once per page load and shared (backend app/api/baits.py).
let baits: Promise<BaitCard[]> | null = null;

export function useBaitCards(): BaitCard[] | null {
  const [list, setList] = useState<BaitCard[] | null>(null);
  useEffect(() => {
    let live = true;
    baits ??= listBaits();
    baits
      .then((l) => live && setList(l))
      .catch(() => {
        baits = null; // a later mount retries
      });
    return () => {
      live = false;
    };
  }, []);
  return list;
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
    for (const lang of locale === "en" ? ["en"] : ["en", locale]) {
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
