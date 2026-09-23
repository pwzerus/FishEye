import type {
  RecommendationRequest,
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
}): Promise<WaterbodyListItem[]> {
  const qs = new URLSearchParams();
  if (params?.stateCode) qs.set("state_code", params.stateCode);
  if (params?.species) qs.set("species", params.species);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<WaterbodyListItem[]>(`/api/waterbodies${suffix}`);
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

export { ApiError };
