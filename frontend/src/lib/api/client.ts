import type { WaterbodyDetail, WaterbodyListItem } from "./types";

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

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    // Server data changes rarely relative to how often a demo page is
    // reloaded; a short cache keeps repeated clicks from hammering the
    // backend without going stale mid-session.
    next: { revalidate: 30 },
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

export { ApiError };
