import type { TackleSetup } from "@/lib/api/types";

/** Lure setups and bait setups, grouped for the two sections of a guide. A
 * setup naming both (method "either") appears in both groups, since the
 * text already says it works either way. Pure, so a server page can call it. */
export function groupSetups(setups: TackleSetup[]) {
  return {
    lure: setups.filter((s) => s.method === "lure" || s.method === "either"),
    bait: setups.filter((s) => s.method === "bait" || s.method === "either"),
  };
}
