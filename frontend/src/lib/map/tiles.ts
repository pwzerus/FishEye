/** Where the basemap tiles come from — one answer, shared by every map.
 *
 * Read here rather than in each map component so that changing provider is a
 * change of environment, not a change of code, and so the three maps in the
 * app (the main map, a lake's detail map, a catch pin's mini map) can never
 * drift onto different basemaps.
 *
 * THE DEFAULT IS FOR DEVELOPMENT ONLY
 * -----------------------------------
 * Falling back to OpenStreetMap's own tile server keeps `npm run dev` working
 * with no setup, and that is all it is for. The OSMF Tile Usage Policy treats
 * those tiles as a service for OSM's own maps rather than as free
 * infrastructure for other applications: an app that leans on them in
 * production can be throttled or blocked without notice, and the policy is
 * explicit that doing so is not a supported use. Anything deployed sets
 * NEXT_PUBLIC_TILE_URL to a provider this project actually has an account
 * with.
 *
 * (The default drops the old `{s}.` subdomain rotation these components used
 * to carry. OSM serves from the bare host now, and sharding across
 * subdomains defeats HTTP/2 connection reuse rather than helping. No hosted
 * provider uses `{s}` either.)
 *
 * ON THE KEY IN THAT URL
 * ----------------------
 * Both values are NEXT_PUBLIC_, so Next inlines them into the client bundle
 * at build time. A provider key in the URL is therefore public — unavoidably,
 * since the browser is what fetches the tiles. That is how every raster tile
 * provider works, and it is why they all restrict keys by HTTP origin
 * instead: the key is not a secret to hide but a key to lock down in the
 * provider's dashboard. Keep it in .env.local (gitignored), never in
 * .env.local.example.
 *
 * Being inlined at build time also means the dev server has to be restarted
 * after editing .env.local — a browser reload alone still serves the old
 * value.
 */

// `||` rather than `??`: a variable that is present but blank — a half-edited
// .env.local, a CI secret that didn't resolve — should fall back to a working
// map rather than render an empty grey grid.
export const TILE_URL =
  process.env.NEXT_PUBLIC_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export const TILE_ATTRIBUTION =
  process.env.NEXT_PUBLIC_TILE_ATTRIBUTION ||
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
