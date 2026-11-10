/** Keeps a popup on the main map clear of what floats over its top (the
 * search bar, "Use my location", the layer buttons) and its bottom (the
 * legend, the attribution) when Leaflet pans to show it. Every popup on that
 * map uses it: a shop's popup without it opened with its name under the
 * search bar (docs/ui-review-2026-11-08.md). */
export const MAP_POPUP_PAD = {
  autoPanPaddingTopLeft: [12, 150] as [number, number],
  autoPanPaddingBottomRight: [12, 40] as [number, number],
};
