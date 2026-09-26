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
};

export function specFor(slug: string): FishSpec {
  return FISH_SPECS[slug] ?? FISH_SPECS["largemouth-bass"];
}

export function waterFor(slug: string): [string, string] {
  return specFor(slug).water;
}
