/**
 * What the main map loads, and how far it may zoom, in each of its two modes.
 * One place, so the component that fetches and the one that draws cannot
 * drift apart.
 *
 * NATIONAL — the whole country, the map's opening view. Zoom locked to 3–4,
 * no lakes and no community pins: the states layer is the way in
 * (StatesLayer.tsx). Locking the zoom is deliberate. A scroll-wheel nudge
 * used to cross into state scale and pour every verified lake in Texas onto
 * the map as a dense clump, and it also kept requesting higher-zoom basemap
 * tiles nobody had asked for.
 *
 * EXPLORING — a state or a place. Zoom locked to 5–18. Entered only by an
 * explicit act: clicking a state that has lakes, searching, or allowing
 * location. Left only by the "All states" button. Once in, the map is an
 * ordinary map: pan across a state line and the other side's lakes load too.
 *
 *   5 – 7   verified lakes only — a statewide view holds thousands of
 *           OpenStreetMap lakes, and a capped subset of them would look like
 *           the full picture when it isn't.
 *   ≥ 8     every lake in view; the backend keeps the largest when a view
 *           holds more than the limit (docs/adr/0019).
 */
export type MapMode = "national" | "exploring";

export const MIN_ZOOM_FOR_LAKES = 5;
export const MIN_ZOOM_FOR_ALL_LAKES = 8;

/** Where the map opens for someone we know nothing about: the lower 48. */
export const US_CENTER: [number, number] = [39.5, -98.35];
export const US_ZOOM = 4;

const NATIONAL_MIN_ZOOM = 3;
const EXPLORING_MAX_ZOOM = 18;

export function zoomLimitsFor(mode: MapMode): { min: number; max: number } {
  return mode === "national"
    ? { min: NATIONAL_MIN_ZOOM, max: US_ZOOM }
    : { min: MIN_ZOOM_FOR_LAKES, max: EXPLORING_MAX_ZOOM };
}

export type LakeQuery = { tier?: "verified" } | null;

/** null means "don't ask the API for lakes at all". */
export function lakeQueryFor(mode: MapMode, zoom: number): LakeQuery {
  if (mode === "national" || zoom < MIN_ZOOM_FOR_LAKES) return null;
  if (zoom < MIN_ZOOM_FOR_ALL_LAKES) return { tier: "verified" };
  return {};
}

export type MapViewState = { center: [number, number]; zoom: number };

/** A view to reopen the overview at, pulled inside exploring's zoom range. */
export function asExploringView(view: MapViewState): MapViewState {
  const { min, max } = zoomLimitsFor("exploring");
  return { center: view.center, zoom: Math.min(max, Math.max(min, view.zoom)) };
}

/**
 * The single-lake map (LakeDetailMap.tsx) behaves like "← All lakes" once the
 * person zooms out two levels from where the lake settled — a pond fills the
 * screen at zoom 15, a 50-km reservoir at 9, and each exits two steps out
 * from its own framing. One step proved too twitchy in use: a single stray
 * scroll closed the lake. Zooming in is left alone.
 *
 * Returns the zoom BELOW which the detail map exits.
 */
export const LAKE_DETAIL_EXIT_STEPS = 2;
export function lakeDetailExitZoom(settledZoom: number): number {
  return settledZoom - LAKE_DETAIL_EXIT_STEPS + 1;
}

/** "Texas", "Texas and Oklahoma", "Texas, Oklahoma and Louisiana". */
export function listStateNames(names: string[]): string {
  if (names.length <= 1) return names[0] ?? "";
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}
