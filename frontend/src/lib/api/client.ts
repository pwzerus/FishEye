import type {
  AdvisorRequest,
  AdvisorResponse,
  AskRequest,
  AskResponse,
  SpeciesPhotos,
  GeocodeResult,
  RecommendationRequest,
  SpeciesGuide,
  StateCoverage,
  RecommendationResponse,
  Weather,
  WaterbodyDetail,
  WaterbodyListItem,
} from "./types";

const PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * Where to reach the API from wherever this code is running.
 *
 * In the browser it's NEXT_PUBLIC_API_BASE_URL, inlined at build time. On
 * the server (server components and their revalidation) it can be a
 * different address: under Docker Compose, the browser's "localhost:8000"
 * is the frontend container itself, and the backend is "backend:8000".
 * API_INTERNAL_URL has no NEXT_PUBLIC_ prefix, so Next never inlines it
 * into the browser bundle and the server reads it at run time. Unset (plain
 * `npm run dev`), the server uses the public URL, as before.
 */
function apiBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.API_INTERNAL_URL || PUBLIC_API_BASE_URL;
  }
  return PUBLIC_API_BASE_URL;
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    /** Set when the server wants something specific, e.g. "reauth_required". */
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBaseUrl()}${path}`, {
    // Server data changes rarely relative to how often a demo page is
    // reloaded; a short cache keeps repeated clicks from hammering the
    // backend without going stale mid-session.
    next: { revalidate: 30 },
    ...init,
  });
  if (res.status === 429) {
    // Over a request limit (backend app/api/rate_limits.py). The server's
    // message says whether to wait a moment or come back later, so show it.
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const message =
      typeof body?.detail === "string" ? body.detail : "Too many requests. Please wait a moment and try again.";
    throw new ApiError(message, 429, "rate_limited");
  }
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

export function listStates(): Promise<StateCoverage[]> {
  return apiFetch<StateCoverage[]>("/api/states");
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

export async function listSpeciesPhotos(): Promise<SpeciesPhotos> {
  // Photos come from Wikipedia via the backend, which caches good results
  // for days and never caches a failure. A long cache here would undo that
  // by pinning one bad moment's empty answer, so it's kept short. A failure
  // isn't an error for the page — the illustrations stand on their own.
  try {
    return await apiFetch<SpeciesPhotos>("/api/species/photos", { next: { revalidate: 60 } });
  } catch {
    return {};
  }
}

export function postAsk(payload: AskRequest): Promise<AskResponse> {
  // Not cached here: the backend caches accepted answers keyed on the
  // question and the passages it was grounded in.
  return apiFetch<AskResponse>("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export { ApiError };
