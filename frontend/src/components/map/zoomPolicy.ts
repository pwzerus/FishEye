/**
 * What the main map loads at each zoom. One place, so the three tiers can't
 * drift between the component that fetches and the one that draws.
 *
 *   zoom < 5   the whole country. No lakes, no community pins: the states
 *              layer is the way in (StatesLayer.tsx). A national view of
 *              lake pins is either an unreadable clump or a meaningless
 *              sample, and this app's coverage is per state anyway.
 *   5 – 7      a state. Verified lakes only — a statewide view holds
 *              thousands of OpenStreetMap lakes, and a capped subset of them
 *              would look like the full picture when it isn't.
 *   ≥ 8        everything in view; the backend keeps the largest when a view
 *              holds more than the limit (docs/adr/0019).
 */
export const MIN_ZOOM_FOR_LAKES = 5;
export const MIN_ZOOM_FOR_ALL_LAKES = 8;

/** Where the map opens for someone we know nothing about: the lower 48. */
export const US_CENTER: [number, number] = [39.5, -98.35];
export const US_ZOOM = 4;

export type LakeQuery = { tier?: "verified" } | null;

/** null means "don't ask the API for lakes at this zoom at all". */
export function lakeQueryForZoom(zoom: number): LakeQuery {
  if (zoom < MIN_ZOOM_FOR_LAKES) return null;
  if (zoom < MIN_ZOOM_FOR_ALL_LAKES) return { tier: "verified" };
  return {};
}

/** "Texas", "Texas and Oklahoma", "Texas, Oklahoma and Louisiana". */
export function listStateNames(names: string[]): string {
  if (names.length <= 1) return names[0] ?? "";
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}
