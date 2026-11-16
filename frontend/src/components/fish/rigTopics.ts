import type { Messages } from "@/i18n/messages";

export type RigKey = keyof Messages["rigs"];

/**
 * Which drawing (RigDiagram) a handbook topic gets. A module of its own, not
 * RigDiagram's: that one is a client component, and a server page importing
 * a plain value from it gets a client reference instead of the object (the
 * fish page's link to a setup's drawing never showed, 2026-11-16).
 */
export const RIG_DIAGRAMS: Record<string, RigKey> = {
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
};
