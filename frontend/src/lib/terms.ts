import type { Locale } from "@/i18n/config";
import type { Messages } from "@/i18n/messages";

/**
 * Fishing terms as linked words (added 2026-11-16: the owner asked for every
 * technical word to be underlined, a tap to open a small card saying what it
 * is, and a second tap, on the card's link, to open the handbook topic that
 * explains it). Baits and lures have their own cards (lib/baits.ts); these
 * are the tackle, knot, rig and technique words.
 *
 * What a term is called and what it means are messages (`terms.items`), so
 * each language matches the words its own text uses; which topic explains it
 * is here.
 */

export type TermId = keyof Messages["terms"]["items"];
export type TermItem = Messages["terms"]["items"][TermId];

export const TERM_TOPIC: Record<TermId, string> = {
  leader: "tackle-leaders",
  swivel: "tackle-leaders",
  splitShot: "tackle-split-shot",
  eggSinker: "rig-bottom",
  sinker: "tackle-sinkers",
  bobber: "tackle-bobbers",
  slipBobber: "rig-slip-bobber",
  bobberStop: "rig-slip-bobber",
  circleHook: "tackle-circle-hooks",
  jHook: "tackle-hooks",
  hookSize: "tackle-hooks",
  treble: "tackle-hooks",
  barb: "care-deep-hook",
  jig: "rig-jigs",
  texasRig: "rig-texas",
  wackyRig: "rig-wacky",
  nedRig: "rig-ned",
  dropShot: "rig-drop-shot",
  bottomRig: "rig-bottom",
  clinch: "knot-improved-clinch",
  palomar: "knot-palomar",
  arbor: "knot-arbor",
  surgeonsLoop: "knot-surgeons-loop",
  bloodKnot: "knot-joining",
  surgeonsKnot: "knot-joining",
  overhand: "knot-surgeons-loop",
  braid: "tackle-line",
  mono: "tackle-line",
  fluoro: "tackle-line",
  drag: "technique-drag",
  bail: "cast-spinning",
  spool: "tackle-reels",
  spincast: "tackle-reels",
  spinning: "tackle-reels",
  baitcaster: "tackle-reels",
  freeSpool: "cast-baitcast",
  backlash: "cast-baitcast",
  lineTwist: "trouble-line-twist",
  guides: "tackle-rods",
  rodPower: "tackle-rods",
  setHook: "technique-bite",
  landingNet: "technique-landing",
  slime: "care-release",
  catchRelease: "care-release",
  hemostat: "care-release",
  bleed: "care-dispatch-bleed",
  fillet: "clean-fillet",
  livewell: "care-keeping",
  thermocline: "cond-thermocline",
  front: "cond-fronts",
  cover: "cond-cover",
  dropOff: "cond-points",
  trolling: "method-trolling",
  flyFishing: "method-fly",
  spawn: "timing-spawn-north",
  lateralLine: "bait-why-it-works",
  cleanDrainDry: "rule-clean-drain-dry",
  bulletSinker: "tackle-sinkers",
  snapSwivel: "tackle-leaders",
  octopusHook: "tackle-hooks",
  wormHook: "rig-texas",
  baitHolder: "tackle-hooks",
  finesse: "rig-ned",
  oRing: "rig-wacky",
  tippet: "method-fly",
};

// Words that are also everyday words in English: not a term when what
// follows shows the other meaning ("drag it along the bottom").
// The same in the other languages, found reading every linked word in the
// handbook (2026-11-16): a catfish's spines are barbed like a hook (带倒刺的
// 硬棘, 미늘 달린 가시) without being its barb; "jig a spoon" is the verb; a
// spawn sac is a bait; a spincast reel's cover (カバーを外す) isn't cover.
const NOT_WHEN_FOLLOWED: Partial<Record<TermId, RegExp>> = {
  drag: /^\s+(?:it|them|the|a|an|your|along|across|baits?|lures?|on)\b/i,
  spool: /^\s+(?:on|up)\b/i,
  barb: /^(?:的硬棘|的硬刺|ed spines|\s*달린)/,
  jig: /^\s+(?:a|an|it|the|your|them)\b/i,
  spawn: /^\s+sacs?\b/i,
  cover: /^(?:を外|を回|の穴|を戻|を開|を閉)/,
  // "una maraña de raíces": a tangle of roots, not a backlash.
  backlash: /^\s+de\b/,
};

export interface TermMatch {
  start: number;
  end: number;
  id: TermId;
}

interface Matcher {
  re: RegExp;
  byName: Map<string, TermId>;
}

const cache = new Map<string, Matcher>();

const LATIN = /^[\p{Script=Latin}\d\s'’/,.-]+$/u;
const HANGUL_SYLLABLE = /^[가-힣]$/u;

function escape(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function pattern(name: string): string {
  const esc = escape(name);
  if (LATIN.test(name)) return `(?<![\\p{L}\\p{N}])${esc}(?![\\p{L}\\p{N}])`;
  // A one-syllable Korean word (찌, a bobber) is also part of others (찌르다,
  // to stab): only on its own or before a particle.
  if (HANGUL_SYLLABLE.test(name)) return `(?<![가-힣])${esc}(?=[은는이가을를의에도와로만]|[^가-힣]|$)`;
  return esc;
}

function matcher(locale: Locale, items: Messages["terms"]["items"], english: Messages["terms"]["items"]): Matcher {
  const key = locale;
  const hit = cache.get(key);
  if (hit) return hit;
  const byName = new Map<string, TermId>();
  const sources = locale === "en" ? [english] : [items, english];
  for (const source of sources) {
    for (const id of Object.keys(source) as TermId[]) {
      for (const n of source[id].match) {
        const k = n.toLowerCase();
        if (!byName.has(k)) byName.set(k, id);
      }
    }
  }
  const names = [...byName.keys()].sort((a, b) => b.length - a.length);
  const m = { re: new RegExp(names.map(pattern).join("|"), "giu"), byName };
  cache.set(key, m);
  return m;
}

/** The terms a text names: each once (its first mention), at most `max`,
 * and not the ones explained by `skipTopic` (a topic's own card). */
export function findTerms(
  text: string,
  locale: Locale,
  items: Messages["terms"]["items"],
  english: Messages["terms"]["items"],
  { skipTopic = null, max = 4, seen = new Set<string>() }: { skipTopic?: string | null; max?: number; seen?: Set<string> } = {},
): TermMatch[] {
  // max 0: none (a quick take's line links only its references).
  if (!text || max <= 0) return [];
  const { re, byName } = matcher(locale, items, english);
  const out: TermMatch[] = [];
  for (const m of text.matchAll(re)) {
    const id = byName.get(m[0].toLowerCase());
    if (!id || seen.has(id) || TERM_TOPIC[id] === skipTopic) continue;
    const start = m.index ?? 0;
    const end = start + m[0].length;
    if (NOT_WHEN_FOLLOWED[id]?.test(text.slice(end))) continue;
    seen.add(id);
    out.push({ start, end, id });
    if (out.length >= max) break;
  }
  return out;
}
