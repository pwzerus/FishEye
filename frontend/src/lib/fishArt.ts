/**
 * Visual specs for the fish illustrations (components/fish/FishArt.tsx).
 *
 * Each species is drawn from a handful of real field marks — the features a
 * beginner would actually use to tell it apart — exaggerated a little, the
 * way a comic would: largemouth bass's jaw running past the eye and dark
 * side band, striped bass's bold stripes, crappie's vertical bars or
 * speckles, bluegill's black "ear" flap and orange breast, catfish
 * whiskers and forked tails, shad's shoulder spot and trailing dorsal
 * thread, threadfin's yellow tail. Original drawings, not traced from any
 * photo or artwork.
 */

export type TailShape = "notched" | "forked" | "deep-fork";
export type DorsalKind = "bass" | "split" | "crappie" | "sunfish" | "cat" | "shad";
export type MouthKind = "huge" | "big" | "small" | "up" | "cat";

export type Pattern =
  | { kind: "lateral-band"; blotchy?: boolean }
  | { kind: "spots-below" }
  | { kind: "stripes"; count: number; width: number; opacity: number; broken?: boolean }
  | { kind: "bars"; count: number; opacity: number }
  | { kind: "speckles" }
  | { kind: "dots" };

export interface FishSpec {
  length: number; // nose to tail base, in a 260×160 viewBox
  depthTop: number;
  depthBottom: number;
  peak: number; // where the back is highest, as a fraction of length
  peduncle: number; // half-height at the tail base
  flatHead?: boolean;
  hump?: boolean;
  mouth: MouthKind;
  eye: { r: number; x: number; y: number; iris: string }; // x as fraction of length, y as fraction of depthTop
  colors: {
    back: string;
    side: string;
    belly: string;
    fin: string;
    mark: string;
    breast?: string;
    tail?: string;
  };
  dorsal: DorsalKind;
  tail: TailShape;
  patterns: Pattern[];
  barbels?: boolean;
  shoulderSpot?: boolean;
  earFlap?: boolean;
  dorsalSpot?: boolean;
  /** Card and hero background tint behind the fish. */
  water: [string, string];
}

const BASS_WATER: [string, string] = ["#dff3ec", "#b9e3d6"];
const OPEN_WATER: [string, string] = ["#e0eef7", "#bcd8ea"];
const MUDDY_WATER: [string, string] = ["#ece7d8", "#d6ccb0"];
const WEED_WATER: [string, string] = ["#e6f1db", "#c8e0b3"];

export const FISH_SPECS: Record<string, FishSpec> = {
  "largemouth-bass": {
    length: 168,
    depthTop: 36,
    depthBottom: 33,
    peak: 0.42,
    peduncle: 11,
    mouth: "huge",
    eye: { r: 7.5, x: 0.1, y: 0.32, iris: "#d9a520" },
    colors: { back: "#46652b", side: "#8fa65a", belly: "#eef0d6", fin: "#9fb06a", mark: "#2c3b1a" },
    dorsal: "bass",
    tail: "notched",
    patterns: [{ kind: "lateral-band" }],
    water: BASS_WATER,
  },
  "spotted-bass": {
    length: 164,
    depthTop: 34,
    depthBottom: 31,
    peak: 0.42,
    peduncle: 10,
    mouth: "big",
    eye: { r: 7.5, x: 0.1, y: 0.32, iris: "#c9491f" },
    colors: { back: "#566631", side: "#a6a868", belly: "#f3f0da", fin: "#b3b27a", mark: "#363c1d" },
    dorsal: "bass",
    tail: "notched",
    patterns: [{ kind: "lateral-band", blotchy: true }, { kind: "spots-below" }],
    water: BASS_WATER,
  },
  "white-bass": {
    length: 158,
    depthTop: 42,
    depthBottom: 36,
    peak: 0.38,
    peduncle: 10,
    mouth: "big",
    eye: { r: 8, x: 0.1, y: 0.3, iris: "#e0c24a" },
    colors: { back: "#58788a", side: "#c9d4da", belly: "#f6f8f9", fin: "#aebcc4", mark: "#5d717c" },
    dorsal: "split",
    tail: "forked",
    patterns: [{ kind: "stripes", count: 6, width: 1.6, opacity: 0.55 }],
    water: OPEN_WATER,
  },
  "striped-bass": {
    length: 178,
    depthTop: 30,
    depthBottom: 27,
    peak: 0.4,
    peduncle: 9,
    mouth: "big",
    eye: { r: 7, x: 0.09, y: 0.3, iris: "#b8c2c7" },
    colors: { back: "#3b5b6a", side: "#d3dde2", belly: "#f7f9fa", fin: "#9fb0b8", mark: "#23323a" },
    dorsal: "split",
    tail: "forked",
    patterns: [{ kind: "stripes", count: 7, width: 2.8, opacity: 0.9 }],
    water: OPEN_WATER,
  },
  "hybrid-striped-bass": {
    length: 168,
    depthTop: 38,
    depthBottom: 33,
    peak: 0.38,
    peduncle: 10,
    mouth: "big",
    eye: { r: 7.5, x: 0.1, y: 0.3, iris: "#c8cfd2" },
    colors: { back: "#46687a", side: "#cfdae0", belly: "#f7f9fa", fin: "#a6b6bd", mark: "#2e414b" },
    dorsal: "split",
    tail: "forked",
    patterns: [{ kind: "stripes", count: 6, width: 2.4, opacity: 0.85, broken: true }],
    water: OPEN_WATER,
  },
  "channel-catfish": {
    length: 176,
    depthTop: 26,
    depthBottom: 24,
    peak: 0.32,
    peduncle: 8,
    flatHead: true,
    mouth: "cat",
    eye: { r: 5, x: 0.1, y: 0.2, iris: "#4a4a3a" },
    colors: { back: "#56686f", side: "#9fb0b6", belly: "#f0f2ee", fin: "#7f9098", mark: "#27343a" },
    dorsal: "cat",
    tail: "deep-fork",
    patterns: [{ kind: "dots" }],
    barbels: true,
    water: MUDDY_WATER,
  },
  "blue-catfish": {
    length: 180,
    depthTop: 36,
    depthBottom: 25,
    peak: 0.3,
    peduncle: 8,
    flatHead: true,
    hump: true,
    mouth: "cat",
    eye: { r: 5, x: 0.1, y: 0.18, iris: "#3c4652" },
    colors: { back: "#3b5b7c", side: "#8fa9c2", belly: "#eef3f7", fin: "#6f8aa6", mark: "#233446" },
    dorsal: "cat",
    tail: "forked",
    patterns: [],
    barbels: true,
    water: MUDDY_WATER,
  },
  "white-crappie": {
    length: 150,
    depthTop: 44,
    depthBottom: 41,
    peak: 0.5,
    peduncle: 10,
    mouth: "up",
    eye: { r: 9, x: 0.12, y: 0.24, iris: "#b7b98f" },
    colors: { back: "#657a55", side: "#d7dcc6", belly: "#f5f6ee", fin: "#c9ceb4", mark: "#4c5a3a" },
    dorsal: "crappie",
    tail: "notched",
    patterns: [{ kind: "bars", count: 7, opacity: 0.5 }],
    water: WEED_WATER,
  },
  "black-crappie": {
    length: 150,
    depthTop: 45,
    depthBottom: 42,
    peak: 0.5,
    peduncle: 10,
    mouth: "up",
    eye: { r: 9, x: 0.12, y: 0.24, iris: "#9c9b7a" },
    colors: { back: "#3c4733", side: "#c5c9b4", belly: "#eef0e4", fin: "#a9ad98", mark: "#262d21" },
    dorsal: "crappie",
    tail: "notched",
    patterns: [{ kind: "speckles" }],
    water: WEED_WATER,
  },
  bluegill: {
    length: 140,
    depthTop: 50,
    depthBottom: 47,
    peak: 0.45,
    peduncle: 10,
    mouth: "small",
    eye: { r: 8, x: 0.11, y: 0.26, iris: "#3a3a32" },
    colors: {
      back: "#3a573c",
      side: "#7f9a6a",
      belly: "#f2c75b",
      breast: "#e8893a",
      fin: "#6f8a64",
      mark: "#243424",
    },
    dorsal: "sunfish",
    tail: "notched",
    patterns: [{ kind: "bars", count: 6, opacity: 0.3 }],
    earFlap: true,
    dorsalSpot: true,
    water: WEED_WATER,
  },
  "gizzard-shad": {
    length: 160,
    depthTop: 40,
    depthBottom: 40,
    peak: 0.42,
    peduncle: 9,
    mouth: "small",
    eye: { r: 7, x: 0.09, y: 0.22, iris: "#d4d8da" },
    colors: { back: "#62798a", side: "#d9e2e7", belly: "#f7f9fa", fin: "#b8c6ce", mark: "#34434c" },
    dorsal: "shad",
    tail: "deep-fork",
    patterns: [{ kind: "stripes", count: 5, width: 1, opacity: 0.25 }],
    shoulderSpot: true,
    water: OPEN_WATER,
  },
  "threadfin-shad": {
    length: 150,
    depthTop: 34,
    depthBottom: 34,
    peak: 0.42,
    peduncle: 8,
    mouth: "small",
    eye: { r: 7, x: 0.09, y: 0.24, iris: "#d4d8da" },
    colors: {
      back: "#597a8b",
      side: "#dde6ea",
      belly: "#f7f9fa",
      fin: "#c8d3d8",
      mark: "#34434c",
      tail: "#f2c94c",
    },
    dorsal: "shad",
    tail: "deep-fork",
    patterns: [],
    shoulderSpot: true,
    water: OPEN_WATER,
  },
  // Added with the knowledge-base expansion (docs/adr/0024). Same approach:
  // the field marks the guide uses to tell each one apart, a little
  // exaggerated.
  "flathead-catfish": {
    // Broad flat head with the lower jaw out front, mottled yellow-brown,
    // an almost square tail.
    length: 182,
    depthTop: 27,
    depthBottom: 24,
    peak: 0.34,
    peduncle: 10,
    flatHead: true,
    mouth: "cat",
    eye: { r: 4.5, x: 0.11, y: 0.22, iris: "#5a4a2a" },
    colors: { back: "#6b5a2e", side: "#c2a865", belly: "#f3ead0", fin: "#9a8550", mark: "#3a2f17" },
    dorsal: "cat",
    tail: "notched",
    patterns: [{ kind: "speckles" }],
    barbels: true,
    water: MUDDY_WATER,
  },
  "smallmouth-bass": {
    // Bronze-brown with faint mottling and vertical bars, no side band; the
    // jaw reaches the back of the eye. Red-orange eye, like most photos show.
    length: 160,
    depthTop: 35,
    depthBottom: 31,
    peak: 0.42,
    peduncle: 10,
    mouth: "big",
    eye: { r: 7.5, x: 0.1, y: 0.32, iris: "#c4421c" },
    colors: { back: "#5c4a26", side: "#a98d55", belly: "#efe6c9", fin: "#a8905c", mark: "#3b2c14" },
    dorsal: "bass",
    tail: "notched",
    patterns: [{ kind: "bars", count: 9, opacity: 0.35 }],
    water: BASS_WATER,
  },
  "guadalupe-bass": {
    // Green, a diamond-blotched side band, spots in rows on the belly; the
    // jaw stops at the eye.
    length: 158,
    depthTop: 33,
    depthBottom: 30,
    peak: 0.42,
    peduncle: 10,
    mouth: "big",
    eye: { r: 7, x: 0.1, y: 0.32, iris: "#c0392b" },
    colors: { back: "#3f5f2c", side: "#93a96a", belly: "#eef0d8", fin: "#91a46a", mark: "#26381a" },
    dorsal: "bass",
    tail: "notched",
    patterns: [{ kind: "lateral-band", blotchy: true }, { kind: "spots-below" }],
    water: BASS_WATER,
  },
  "redear-sunfish": {
    // A bluegill's shape with yellow-green sides, a pale belly and a short
    // ear flap; no dark spot on the dorsal fin.
    length: 142,
    depthTop: 48,
    depthBottom: 45,
    peak: 0.45,
    peduncle: 10,
    mouth: "small",
    eye: { r: 8, x: 0.11, y: 0.26, iris: "#3a3a32" },
    colors: { back: "#4a5f33", side: "#b8c172", belly: "#f6f2dc", breast: "#f0d98a", fin: "#8f9a62", mark: "#2f3b20" },
    dorsal: "sunfish",
    tail: "notched",
    patterns: [{ kind: "bars", count: 6, opacity: 0.15 }],
    earFlap: true,
    water: WEED_WATER,
  },
  "rainbow-trout": {
    // Slim, speckled all over, with a pink flush along the side.
    length: 172,
    depthTop: 29,
    depthBottom: 27,
    peak: 0.45,
    peduncle: 10,
    mouth: "big",
    eye: { r: 6, x: 0.09, y: 0.3, iris: "#c9c2a0" },
    colors: { back: "#5d6b45", side: "#e0b3b5", belly: "#f6f3ee", fin: "#b9a98f", mark: "#2f3524" },
    dorsal: "cat",
    tail: "notched",
    patterns: [{ kind: "speckles" }],
    water: OPEN_WATER,
  },
  "freshwater-drum": {
    // Deep, arched, silvery, with a long dorsal fin split in two.
    length: 160,
    depthTop: 46,
    depthBottom: 30,
    peak: 0.36,
    peduncle: 10,
    hump: true,
    mouth: "small",
    eye: { r: 7, x: 0.1, y: 0.3, iris: "#cfd3d4" },
    colors: { back: "#7d8a8f", side: "#d6dcde", belly: "#f6f8f8", fin: "#b5bfc2", mark: "#4a5559" },
    dorsal: "split",
    tail: "notched",
    patterns: [],
    water: OPEN_WATER,
  },
  "common-carp": {
    // Heavy, golden, with whiskers on the upper jaw.
    length: 172,
    depthTop: 40,
    depthBottom: 33,
    peak: 0.4,
    peduncle: 11,
    mouth: "small",
    eye: { r: 6, x: 0.09, y: 0.3, iris: "#d8b24a" },
    colors: { back: "#6e5a24", side: "#c9a34a", belly: "#f3e3b0", fin: "#a5833d", mark: "#4a3a14" },
    dorsal: "crappie",
    tail: "forked",
    patterns: [{ kind: "dots" }],
    barbels: true,
    water: MUDDY_WATER,
  },
  walleye: {
    // Long and slim, olive-gold, with a big glassy eye and two dorsal fins.
    length: 178,
    depthTop: 25,
    depthBottom: 23,
    peak: 0.42,
    peduncle: 9,
    mouth: "big",
    eye: { r: 8, x: 0.09, y: 0.32, iris: "#e7e2c0" },
    colors: { back: "#5e5a2e", side: "#b9a55a", belly: "#f4f1e2", fin: "#8c8452", mark: "#3a3719" },
    dorsal: "split",
    tail: "forked",
    patterns: [{ kind: "bars", count: 5, opacity: 0.22 }],
    dorsalSpot: true,
    water: OPEN_WATER,
  },
  "northern-pike": {
    // Very long and low, with a duck-bill snout and light spots along the side.
    length: 196,
    depthTop: 20,
    depthBottom: 19,
    peak: 0.62,
    peduncle: 9,
    flatHead: true,
    mouth: "huge",
    eye: { r: 6, x: 0.11, y: 0.34, iris: "#d9cf8f" },
    colors: { back: "#3f5a3a", side: "#7f9a63", belly: "#eef0dc", fin: "#7b7a44", mark: "#dfe2a6" },
    dorsal: "shad",
    tail: "forked",
    patterns: [{ kind: "dots" }],
    water: WEED_WATER,
  },
  "yellow-perch": {
    // Golden and deep-bodied, with dark bars down the side.
    length: 150,
    depthTop: 36,
    depthBottom: 26,
    peak: 0.4,
    peduncle: 9,
    mouth: "small",
    eye: { r: 7, x: 0.1, y: 0.32, iris: "#e0c95e" },
    colors: { back: "#5f6a2c", side: "#d8b940", belly: "#f5efd6", fin: "#c98a2e", mark: "#2f3517" },
    dorsal: "split",
    tail: "forked",
    patterns: [{ kind: "bars", count: 7, opacity: 0.62 }],
    water: WEED_WATER,
  },
  "brook-trout": {
    // Dark olive with light spots, and a square-ish tail.
    length: 164,
    depthTop: 29,
    depthBottom: 27,
    peak: 0.45,
    peduncle: 10,
    mouth: "big",
    eye: { r: 6, x: 0.09, y: 0.3, iris: "#d8c88a" },
    colors: { back: "#3f4f33", side: "#7f8a55", belly: "#e9a26f", fin: "#c96a3f", mark: "#e6d9a0" },
    dorsal: "cat",
    tail: "notched",
    patterns: [{ kind: "dots" }],
    water: OPEN_WATER,
  },
  "brown-trout": {
    // Buttery brown with dark spots.
    length: 172,
    depthTop: 30,
    depthBottom: 27,
    peak: 0.45,
    peduncle: 11,
    mouth: "big",
    eye: { r: 6, x: 0.09, y: 0.3, iris: "#d8b870" },
    colors: { back: "#5d4a26", side: "#b8934d", belly: "#f1e2b4", fin: "#8f7238", mark: "#2c2110" },
    dorsal: "cat",
    tail: "notched",
    patterns: [{ kind: "speckles" }],
    water: MUDDY_WATER,
  },
  "golden-trout": {
    // Bright gold, with a red belly and dark oval marks along the side.
    length: 160,
    depthTop: 27,
    depthBottom: 26,
    peak: 0.45,
    peduncle: 10,
    mouth: "big",
    eye: { r: 6, x: 0.09, y: 0.3, iris: "#e0c95e" },
    colors: { back: "#5f6a2c", side: "#e0bb3a", belly: "#d9502f", fin: "#d9772f", mark: "#3a3d1a" },
    dorsal: "cat",
    tail: "notched",
    patterns: [{ kind: "bars", count: 8, opacity: 0.32 }, { kind: "speckles" }],
    water: OPEN_WATER,
  },
  "cutthroat-trout": {
    // Olive with black spots and a pink band along the side.
    length: 168,
    depthTop: 28,
    depthBottom: 27,
    peak: 0.45,
    peduncle: 10,
    mouth: "big",
    eye: { r: 6, x: 0.09, y: 0.3, iris: "#d9c58a" },
    colors: { back: "#566338", side: "#d9b98f", belly: "#f4eee0", fin: "#a7905f", mark: "#26291a", breast: "#d9502f" },
    dorsal: "cat",
    tail: "notched",
    patterns: [{ kind: "speckles" }],
    water: OPEN_WATER,
  },
  "kokanee-salmon": {
    // Silver with a blue-green back and a deeply forked tail.
    length: 164,
    depthTop: 26,
    depthBottom: 25,
    peak: 0.44,
    peduncle: 8,
    mouth: "small",
    eye: { r: 7, x: 0.09, y: 0.3, iris: "#d5dadb" },
    colors: { back: "#2f5a6b", side: "#cfdce0", belly: "#f7f9f9", fin: "#9fb1b7", mark: "#223b46" },
    dorsal: "cat",
    tail: "deep-fork",
    patterns: [],
    water: OPEN_WATER,
  },
  "brown-bullhead": {
    // A small, mottled brown catfish with whiskers and a square tail.
    length: 150,
    depthTop: 25,
    depthBottom: 24,
    peak: 0.35,
    peduncle: 12,
    flatHead: true,
    mouth: "cat",
    eye: { r: 4, x: 0.1, y: 0.42, iris: "#c7b98a" },
    colors: { back: "#4a3a1f", side: "#8c7238", belly: "#efe5be", fin: "#5e4d2a", mark: "#2c2110" },
    dorsal: "cat",
    tail: "notched",
    patterns: [{ kind: "lateral-band", blotchy: true }],
    barbels: true,
    water: MUDDY_WATER,
  },
};

export function specFor(slug: string): FishSpec {
  return FISH_SPECS[slug] ?? FISH_SPECS["largemouth-bass"];
}

export function waterFor(slug: string): [string, string] {
  return specFor(slug).water;
}
