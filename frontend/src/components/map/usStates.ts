import type { FeatureCollection, Geometry, Position } from "geojson";

export type StateProps = { code: string; name: string };
export type StatesFile = FeatureCollection<Geometry, StateProps>;

/** [[south, west], [north, east]] — the shape L.latLngBounds accepts. */
export type BoundsTuple = [[number, number], [number, number]];

/** One state as the map uses it once someone is inside it. */
export interface StateRegion {
  code: string;
  name: string;
  bounds: BoundsTuple;
  /** Outer rings of the state's polygons, as [lat, lng] — the holes cut
   * into the dimming mask around the state. */
  rings: [number, number][][];
}

// Census state boundaries, built once from us-atlas (see the file's
// "source" field). A static file rather than a dependency: 55 KB gzipped,
// fetched only by the map page, cached across remounts of the map.
let statesFile: Promise<StatesFile> | null = null;
export function loadStates(): Promise<StatesFile> {
  statesFile ??= fetch("/geo/us-states.json")
    .then((r) => {
      if (!r.ok) throw new Error(`us-states.json: ${r.status}`);
      return r.json() as Promise<StatesFile>;
    })
    .catch((e: unknown) => {
      statesFile = null; // let a later call retry
      throw e;
    });
  return statesFile;
}

function outerRings(geometry: Geometry): Position[][] {
  if (geometry.type === "Polygon") return [geometry.coordinates[0]];
  if (geometry.type === "MultiPolygon") return geometry.coordinates.map((p) => p[0]);
  return [];
}

function inRing(lng: number, lat: number, ring: Position[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** A state's bounds and outline from its feature in the states file. */
export function regionOf(file: StatesFile, code: string): StateRegion | null {
  const feature = file.features.find((f) => f.properties.code === code);
  if (!feature) return null;
  const rings = outerRings(feature.geometry);
  let south = 90;
  let west = 180;
  let north = -90;
  let east = -180;
  for (const ring of rings) {
    for (const [lng, lat] of ring) {
      south = Math.min(south, lat);
      north = Math.max(north, lat);
      west = Math.min(west, lng);
      east = Math.max(east, lng);
    }
  }
  return {
    code,
    name: feature.properties.name,
    bounds: [
      [south, west],
      [north, east],
    ],
    rings: rings.map((ring) => ring.map(([lng, lat]) => [lat, lng] as [number, number])),
  };
}

/**
 * The state a point is in. The outlines are rounded to two decimals, so a
 * lake on a coast or a border can land a hair outside every shape; it then
 * goes to the state whose box holds it, preferring one in `prefer` (the
 * states FishEye has lakes for).
 */
export function stateCodeAt(
  file: StatesFile,
  lat: number,
  lng: number,
  prefer: Set<string> | null = null,
): string | null {
  // Alaska's outline runs west of -180 (the Aleutians), where a point east
  // of the date line (+172 to +180) is drawn; test both.
  const lngs = lng > 0 ? [lng, lng - 360] : [lng];
  for (const f of file.features) {
    if (outerRings(f.geometry).some((ring) => lngs.some((x) => inRing(x, lat, ring)))) return f.properties.code;
  }
  let fallback: string | null = null;
  for (const f of file.features) {
    const region = regionOf(file, f.properties.code);
    if (!region) continue;
    const [[s, w], [n, e]] = region.bounds;
    if (lat < s - 0.05 || lat > n + 0.05 || !lngs.some((x) => x >= w - 0.05 && x <= e + 0.05)) continue;
    if (prefer?.has(f.properties.code)) return f.properties.code;
    fallback ??= f.properties.code;
  }
  return fallback;
}

/**
 * Where to draw a longitude inside a state's view. Lakes are stored at their
 * real longitude, but Alaska's region runs west of -180 so the Aleutians stay
 * one continuous shape; a lake at +175 is drawn at -185 there, inside the
 * view, instead of across the world.
 */
export function displayLongitude(lng: number, region: StateRegion | null | undefined): number {
  if (region && region.bounds[0][1] < -180 && lng > 0) return lng - 360;
  return lng;
}
