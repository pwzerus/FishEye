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
    if (typeof text === "string" && safeCredit(text)) seen.add(safeCredit(text));
  }
  return seen.size ? [...seen].join(", ") : safeCredit(fallback);
}

const LINK = /<a\s[^>]*?href\s*=\s*(["'])(https:\/\/[^"'<>\s]+)\1[^>]*>([^<]*)<\/a>/gi;

/** Text with every tag dropped and what's left escaped; entities such as
 * `&copy;` are kept as they are. */
function plain(text: string): string {
  return text
    .replace(/<[^>]*>/g, "")
    .replace(/&(?!(?:[a-z]+|#\d+|#x[0-9a-f]+);)/gi, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * A credit line safe to put in the page as HTML: plain text and
 * `<a href="https://…">text</a>` links, nothing else.
 *
 * Needed because Leaflet writes the credit into the page as HTML without
 * checking it, and part of it comes from another site (the style and its
 * TileJSON). MapLibre 6.4 fixed a hole in its own cleaning of credits
 * (GHSA-jrc7-96c5-q579, 2026-09); this keeps a credit from either site from
 * running script in FishEye's pages whatever the libraries do.
 */
export function safeCredit(html: string): string {
  const out: string[] = [];
  let last = 0;
  for (const m of html.matchAll(LINK)) {
    out.push(plain(html.slice(last, m.index)), `<a href="${m[2].replace(/&(?!amp;)/g, "&amp;")}">${plain(m[3])}</a>`);
    last = m.index + m[0].length;
  }
  out.push(plain(html.slice(last)));
  return out.join("").replace(/\s+/g, " ").trim();
}

/**
 * A copy of `style` in which every source that names no credit of its own
 * but points at a TileJSON (`url`) carries that TileJSON's `attribution`.
 *
 * Needed for styles that keep the credit only there: MapTiler's Satellite
 * Hybrid declares both its sources by `url` alone, so styleAttribution found
 * nothing and the map credited OpenStreetMap but not MapTiler, whose terms
 * require "© MapTiler". A TileJSON that fails to load is skipped; the
 * fallback credit still shows. Does not modify its argument.
 */
export async function withLinkedAttributions(
  style: StyleSpecification,
  fetchJson: (url: string) => Promise<unknown> = (url) => fetch(url).then((r) => (r.ok ? r.json() : null)),
): Promise<StyleSpecification> {
  const entries = await Promise.all(
    Object.entries(style.sources ?? {}).map(async ([id, source]) => {
      const s = source as { attribution?: unknown; url?: unknown };
      if ((typeof s.attribution === "string" && s.attribution.trim()) || typeof s.url !== "string") return [id, source];
      try {
        const tileJson = (await fetchJson(s.url)) as { attribution?: unknown } | null;
        const text = tileJson?.attribution;
        return [id, typeof text === "string" && text.trim() ? { ...source, attribution: text } : source];
      } catch {
        return [id, source];
      }
    }),
  );
  return { ...style, sources: Object.fromEntries(entries) };
}
