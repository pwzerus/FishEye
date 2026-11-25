import type { Locale } from "@/i18n/config";

/** A handbook topic's id and its title in the reader's language. */
export type TopicTitle = { id: string; title: string; region?: string };
/** Where a reference to a topic sits in a text, and which topic it is. */
export type SeeRef = { start: number; end: number; topic: string };

/**
 * The handbook's cross-references, "(see Setting the drag)" and the same in
 * every language, found so a card can link them (2026-11-25: they were
 * plain text). A reference names a topic by its title or by the title's
 * first part ("Catch and release" for "Catch and release: handling a fish
 * you'll let go"), and may name several ("Split shot, Bobbers and Sliding
 * sinker bottom rig"). A name that is no topic's stays plain text.
 */
const GROUP: Record<Locale, RegExp> = {
  en: /\(see ([^()]+)\)/g,
  es: /\((?:consulta|ver) ([^()]+)\)/g,
  ko: /\(([^()]+) 참고\)/g,
  zh: /（见([^（）]+)）/g,
  zht: /（見([^（）]+)）/g,
  ja: /（([^（）]+)を参照）/g,
};

// Chinese and Japanese put each title in quotes, Korean often in single
// ones; the others list them bare.
const QUOTED = /[“「‘']([^”」’']+)[”」’']/g;
const OPENS_QUOTE = /^\s*[“「‘']/;
// In these a title is always quoted, even after words of the reference's
// own: （タングステンもその一つです。「オモリ」を参照）.
const QUOTES_TITLES = new Set<Locale>(["zh", "zht", "ja"]);
const SEPARATOR: Record<Locale, RegExp> = {
  en: /^(?:, and |, or |, | and | or )/,
  es: /^(?:, y |, o |, | y | o )/,
  ko: /^(?:와 |과 |, | 및 )/,
  zh: /^(?:、|和|，)/,
  zht: /^(?:、|和|，)/,
  ja: /^(?:、|と)/,
};

/** A title and its first part, before a colon, a comma or a bracket, or
 * up to its question mark ("Is it a bite?"). */
function names(title: string): string[] {
  const out = new Set([title]);
  const cut = title.search(/[:：,，、(（]/);
  if (cut > 0) out.add(title.slice(0, cut).trim());
  const ask = title.search(/[?？]/);
  if (ask > 0) out.add(title.slice(0, ask + 1));
  return [...out];
}

/** A quoted name that isn't a title or its first part: the one title it
 * begins ("旧鱼线" for "旧鱼线怎么处理"), if only one does. */
function begun(name: string, titles: TopicTitle[]): string | null {
  const ids = new Set(titles.filter((t) => t.title.startsWith(name) && (t.region ?? "all") === "all").map((t) => t.id));
  return ids.size === 1 ? [...ids][0] : null;
}

const TABLES = new WeakMap<TopicTitle[], Map<string, string>>();

/** Every name a reference may use, to its topic: a topic for all states
 * before one state's card of the same title. */
function table(titles: TopicTitle[]): Map<string, string> {
  let found = TABLES.get(titles);
  if (found) return found;
  found = new Map();
  const ordered = [...titles].sort((a, b) => Number((a.region ?? "all") !== "all") - Number((b.region ?? "all") !== "all"));
  for (const t of ordered) for (const n of names(t.title)) if (!found.has(n)) found.set(n, t.id);
  TABLES.set(titles, found);
  return found;
}

export function findSeeRefs(text: string, locale: Locale, titles: TopicTitle[]): SeeRef[] {
  const group = GROUP[locale];
  if (!group || titles.length === 0) return [];
  const known = table(titles);
  const refs: SeeRef[] = [];
  for (const m of text.matchAll(group)) {
    const inner = m[1];
    const offset = (m.index ?? 0) + m[0].indexOf(inner);
    if (QUOTES_TITLES.has(locale) ? /[“「]/.test(inner) : OPENS_QUOTE.test(inner)) {
      for (const q of inner.matchAll(QUOTED)) {
        const name = q[1].trim();
        const topic = known.get(name) ?? begun(name, titles);
        const at = offset + (q.index ?? 0) + 1 + q[1].indexOf(name);
        if (topic) refs.push({ start: at, end: at + name.length, topic });
      }
      continue;
    }
    const listed = list(inner, known, SEPARATOR[locale]);
    // Else a name at the end, after words of its own ("…. Sinkers").
    const found = listed.length > 0 ? listed : tail(inner, known);
    for (const r of found) refs.push({ start: offset + r.start, end: offset + r.end, topic: r.topic });
  }
  return refs;
}

/** A list of names: at each place the longest name that ends where the
 * list goes on (", ", " and ") or stops. */
function list(inner: string, known: Map<string, string>, separator: RegExp): SeeRef[] {
  const refs: SeeRef[] = [];
  let i = 0;
  while (i < inner.length) {
    let best: [string, string] | null = null;
    for (const [name, topic] of known) {
      if (best && name.length <= best[0].length) continue;
      if (!inner.startsWith(name, i)) continue;
      const rest = inner.slice(i + name.length);
      if (rest && !separator.test(rest)) continue;
      best = [name, topic];
    }
    if (!best) break;
    refs.push({ start: i, end: i + best[0].length, topic: best[1] });
    i += best[0].length;
    const sep = inner.slice(i).match(separator);
    if (!sep) break;
    i += sep[0].length;
  }
  return refs;
}

function tail(inner: string, known: Map<string, string>): SeeRef[] {
  let best: [string, string] | null = null;
  for (const [name, topic] of known) {
    if (best && name.length <= best[0].length) continue;
    if (!inner.endsWith(name)) continue;
    const before = inner.slice(0, inner.length - name.length);
    if (before && !/[\s.。]$/.test(before)) continue;
    best = [name, topic];
  }
  return best ? [{ start: inner.length - best[0].length, end: inner.length, topic: best[1] }] : [];
}
