/**
 * Edits applied to the vector basemap's style before it is drawn
 * (src/components/map/BaseMap.tsx).
 *
 * Why this exists: rural Texas is full of private and historical
 * airstrips, and every stock MapTiler style with readable roads marks each
 * one with a plane icon — dozens in a single county view, drowning out the
 * lakes this map is for. With raster tiles those icons are baked into the
 * image; with a vector style each map feature is its own layer, so the
 * icons can be switched off and everything else kept.
 *
 * Only the icon/label layers go. The runway lines and the airport-zone
 * shading are real features on the ground, like railways, and stay.
 */
import type { LayerSpecification, StyleSpecification } from "maplibre-gl";

/**
 * Which layers to hide: `symbol` layers (icons and text) whose id names an
 * airport. In MapTiler's streets-v4 that is "Airport labels" (the plane
 * icon plus the airfield's name), "Airport terminal" and "Airport gate
 * labels". "Airport zone" is a `fill` and "Aeroway" a `line`, so the type
 * check is what keeps them.
 *
 * Matched by name pattern rather than exact ids so a MapTiler rename such as
 * "Airport labels" -> "Airport label" does not quietly bring the icons back.
 * If MapTiler moves them somewhere unrecognisable, the icons reappear; they
 * do not break the map.
 */
const AIRPORT_ICON = /airport|aerodrome|airfield|airstrip/i;

export function isHiddenLayer(layer: LayerSpecification): boolean {
  return layer.type === "symbol" && AIRPORT_ICON.test(layer.id);
}

/** A copy of `style` with the hidden layers set to visibility: none.
 * Hidden rather than removed, so nothing else in the style that refers to a
 * layer by id can break. Does not modify its argument. */
export function hideAirportIcons(style: StyleSpecification): StyleSpecification {
  return {
    ...style,
    layers: style.layers.map((layer) =>
      isHiddenLayer(layer)
        ? ({ ...layer, layout: { ...(layer.layout ?? {}), visibility: "none" } } as LayerSpecification)
        : layer,
    ),
  };
}

/**
 * The credit line for a vector basemap, taken from its style: each source's
 * attribution, trimmed, duplicates dropped, in order.
 *
 * Needed because the Leaflet bridge otherwise builds the credit itself from
 * every source *after* loading, and MapTiler's style names the same
 * "© MapTiler © OpenStreetMap contributors" on two sources (one in the style,
 * one arriving with the tile metadata), so the map showed it twice. Returns
 * `fallback` when the style names none, so the credit can never go missing.
 */
export function styleAttribution(style: StyleSpecification, fallback: string): string {
  const seen = new Set<string>();
  for (const source of Object.values(style.sources ?? {})) {
    const text = (source as { attribution?: unknown }).attribution;
    if (typeof text === "string" && text.trim()) seen.add(text.trim());
  }
  return seen.size ? [...seen].join(", ") : fallback;
}
