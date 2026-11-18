import type { Messages } from "@/i18n/messages";

export type RigKey = keyof Messages["rigs"];

/**
 * Which drawing (RigDiagram) a handbook topic gets. A module of its own, not
 * RigDiagram's: that one is a client component, and a server page importing
 * a plain value from it gets a client reference instead of the object (the
 * fish page's link to a setup's drawing never showed, 2026-11-16).
 */
export const RIG_DIAGRAMS: Record<string, RigKey | RigKey[]> = {
  "rig-bottom": "bottom",
  "tackle-leaders": "swivel",
  "knot-improved-clinch": "clinch",
  "tackle-hooks": "sizes",
  "tackle-circle-hooks": "circle",
  "rig-wacky": "wacky",
  "rig-texas": "texas",
  "rig-ned": "ned",
  "rig-drop-shot": "dropShot",
  "rig-slip-bobber": "slipBobber",
  "tackle-bobbers": "bobber",
  "knot-arbor": "arbor",
  // A step at a time (StepDrawings.tsx), added the same day: every knot,
  // threading and movement the handbook teaches.
  "knot-palomar": "palomar",
  "knot-surgeons-loop": "surgeonsLoop",
  "knot-joining": ["blood", "surgeonsKnot"],
  "tackle-new-line": "spincastSpool",
  "trouble-line-twist": "spinningFill",
  "cast-spinning": "castSpinning",
  "cast-baitcast": "castBaitcast",
  "technique-drag": "drag",
  "technique-bite": "setHook",
  "technique-landing": "landing",
  "care-release": "release",
  "care-deep-hook": "deepHook",
  "trouble-snags": "snag",
  "trouble-retie": "retie",
  "safe-handling": "catfishHold",
  "bait-worms": "worm",
  "bait-minnows": "minnow",
  "bait-insects": "cricket",
  "bait-crayfish": "crayfish",
  "tackle-split-shot": "splitShot",
  "rig-jigs": "jigWork",
  "clean-fillet": "fillet",
  "clean-catfish": "catfishSkin",
  "clean-scaling": "scaling",
  "technique-measure": "measure",
  "care-dispatch-bleed": "bleed",
  "knot-tips": "knotTips",
  "trouble-spincast": "spincastFix",
  "bait-dough-corn": "dough",
  "bait-shrimp": "shrimp",
  "clean-fillet-panfish": "panfishFillet",
  "safe-lifejacket": "lifejacket",
  "technique-shore": "shoreCast",
  "care-keeping": "keepFish",
  "method-stream-trout-bait": "streamDrift",
  "method-ice": "iceFish",
  "method-trolling": "trolling",
  "safe-hook-injury": "hookInjury",
};

/** The drawings a topic has, in order (none: an empty list). */
export function rigKeys(topic: string): RigKey[] {
  const k = RIG_DIAGRAMS[topic];
  return k === undefined ? [] : Array.isArray(k) ? k : [k];
}
