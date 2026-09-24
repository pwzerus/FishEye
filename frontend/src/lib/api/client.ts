import type {
  AdvisorRequest,
  AdvisorResponse,
  GeocodeResult,
  RecommendationRequest,
  SpeciesGuide,
  RecommendationResponse,
  Weather,
  WaterbodyDetail,
  WaterbodyListItem,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    // Server data changes rarely relative to how often a demo page is
    // reloaded; a short cache keeps repeated clicks from hammering the
    // backend without going stale mid-session.
    next: { revalidate: 30 },
    ...init,
  });
  if (!res.ok) {
    throw new ApiError(`${path} failed with ${res.status}`, res.status);
  }
  return res.json() as Promise<T>;
}

export function listWaterbodies(params?: {
  stateCode?: string;
  species?: string;
  // Lets the map ask "what's near this point" instead of "everything in
  // this state" — the query the search box and geolocate button both
  // drive (see LocationSearchBar.tsx). The backend already supported this
  // filter (app/api/waterbodies.py); the map just never called it that way.
  lat?: number;
  lng?: number;
  radiusKm?: number;
  // The map's visible area, "west,south,east,north" — Leaflet's
  // LatLngBounds.toBBoxString() order, passed through unchanged.
  bbox?: string;
  tier?: "verified" | "osm";
  limit?: number;
}): Promise<WaterbodyListItem[]> {
  const qs = new URLSearchParams();
  if (params?.stateCode) qs.set("state_code", params.stateCode);
  if (params?.species) qs.set("species", params.species);
  if (params?.bbox) qs.set("bbox", params.bbox);
  if (params?.tier) qs.set("tier", params.tier);
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.lat !== undefined && params?.lng !== undefined) {
    qs.set("lat", String(params.lat));
    qs.set("lng", String(params.lng));
    if (params.radiusKm !== undefined) qs.set("radius_km", String(params.radiusKm));
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  // A search or a map pan is a user action, not a page load — always hit
  // the live path, same reasoning as getWeather below.
  const interactive = params?.lat !== undefined || params?.bbox !== undefined;
  const cacheOpt = interactive ? { cache: "no-store" as const } : undefined;
  return apiFetch<WaterbodyListItem[]>(`/api/waterbodies${suffix}`, cacheOpt);
}

export function geocodePlace(query: string): Promise<GeocodeResult> {
  const qs = new URLSearchParams({ q: query });
  return apiFetch<GeocodeResult>(`/api/geocode?${qs.toString()}`, { cache: "no-store" });
}

export function getWaterbody(id: number): Promise<WaterbodyDetail> {
  return apiFetch<WaterbodyDetail>(`/api/waterbodies/${id}`);
}

export function getWeather(lat: number, lng: number): Promise<Weather> {
  const qs = new URLSearchParams({ lat: String(lat), lng: String(lng) });
  // No `next.revalidate` override here — this always hits the live path.
  // The backend's own 15-minute cache and circuit breaker (PRD §17) are
  // what protect NWS from being hammered; a second cache layer in front of
  // it would just make the "is this stale?" question harder to answer, and
  // this call is inherently POST-adjacent (fired on demand as the user
  // picks a lake or a species), not a page-load fetch worth batching.
  return apiFetch<Weather>(`/api/weather?${qs.toString()}`, { cache: "no-store" });
}

export function postRecommendations(
  payload: RecommendationRequest,
): Promise<RecommendationResponse> {
  return apiFetch<RecommendationResponse>("/api/recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export function postAdvisorExplain(payload: AdvisorRequest): Promise<AdvisorResponse> {
  // Never cached client-side: the backend already caches on a hash of the
  // facts the answer was built from, which self-invalidates when the
  // weather or the ranking moves. A second cache here, keyed on the request
  // instead, would go stale in exactly the cases that matter.
  return apiFetch<AdvisorResponse>("/api/advisor/explain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

// Same rule as the backend's slugify (app/knowledge/species_guides.py).
export function speciesSlug(commonName: string): string {
  return commonName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function listSpeciesGuides(): Promise<SpeciesGuide[]> {
  // Reviewed reference content that changes only with a deploy: the default
  // short revalidation in apiFetch is plenty.
  return apiFetch<SpeciesGuide[]>("/api/species/guides");
}

export function getSpeciesGuide(slug: string): Promise<SpeciesGuide> {
  return apiFetch<SpeciesGuide>(`/api/species/guides/${encodeURIComponent(slug)}`);
}

export { ApiError };
