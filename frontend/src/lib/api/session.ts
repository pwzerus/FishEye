// Calls that depend on who is signed in: accounts, community pins, admin.
//
// Unlike client.ts these always run in the browser, always send the
// session cookie (`credentials: "include"`) and are never cached — a
// cached "who am I" or pin list would show one person's view to the next.
// The cookie itself is httpOnly: this code never sees or stores the token.
import { ApiError } from "./client";
import type {
  AiAllowance,
  AskRequest,
  AskResponse,
  AdminLakeReport,
  AdminPin,
  AdminReportGroup,
  AdminStats,
  AdminUser,
  AuditEntry,
  AuthProviders,
  FishIdResult,
  LakeReportInput,
  Paged,
  PinDetail,
  PinOptions,
  PinPlaces,
  PinSummary,
  PinWhere,
  WaterGroup,
  PinUpdate,
  User,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** FastAPI errors are `{detail: string}` or, for validation, `{detail: [{msg}]}`. */
export function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : null;
    return first.msg ? `${field ? `${String(field)}: ` : ""}${first.msg}` : fallback;
  }
  return fallback;
}

async function sfetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...init, credentials: "include", cache: "no-store" });
  } catch {
    throw new ApiError("Couldn't reach FishEye's server. Is the backend running?", 0);
  }
  if (res.status === 204) return undefined as T;
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // no JSON body
  }
  if (!res.ok) {
    // Sensitive account changes need a recent sign-in; the server says so
    // with this header (exposed via CORS) so the UI can ask to confirm.
    const code = res.status === 403 && res.headers.get("x-reauth-required") === "1" ? "reauth_required" : undefined;
    throw new ApiError(errorMessage(body, `Request failed (${res.status})`), res.status, code);
  }
  return body as T;
}

export const isReauthRequired = (err: unknown): boolean => err instanceof ApiError && err.code === "reauth_required";

const json = (method: string, data?: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: data === undefined ? undefined : JSON.stringify(data),
});

// ------------------------------------------------------------------ AI summaries

/** Have the model write an answer from the guide passages (docs/adr/0023).
 * Needs an account; a few per day. Refused with the server's own message:
 * 401 signed out, 422 not a question the guides cover, 429 none left today. */
export const postAskSummary = (payload: AskRequest) => sfetch<AskResponse>("/api/ask/summary", json("POST", payload));
export const getAskAllowance = () => sfetch<AiAllowance>("/api/ask/allowance");

// ------------------------------------------------------------------ auth

/** The signed-in user, or null. Uses /session, which answers "signed out"
 * with 200 rather than 401, so visitors' consoles stay clean. */
export async function getMe(): Promise<User | null> {
  return (await sfetch<{ user: User | null }>("/api/auth/session")).user;
}

export const getProviders = () => sfetch<AuthProviders>("/api/auth/providers");
export const register = (email: string, password: string, display_name: string) =>
  sfetch<User>("/api/auth/register", json("POST", { email, password, display_name }));
export const login = (email: string, password: string) =>
  sfetch<User>("/api/auth/login", json("POST", { email, password }));
export const logout = () => sfetch<void>("/api/auth/logout", { method: "POST" });
// Confirming the email address: a new link, and the link's token itself.
export const sendVerificationEmail = () => sfetch<User>("/api/auth/verify-email/send", { method: "POST" });
export const confirmEmail = (token: string) =>
  sfetch<{ verified: boolean; email: string }>("/api/auth/verify-email", json("POST", { token }));
export const updateProfile = (display_name: string) => sfetch<User>("/api/auth/me", json("PATCH", { display_name }));
export const changePassword = (new_password: string, current_password?: string) =>
  sfetch<User>("/api/auth/me/password", json("POST", { new_password, current_password: current_password ?? null }));
/** Confirm the password to get a fresh session for a sensitive change. */
export const reauth = (password: string) => sfetch<User>("/api/auth/reauth", json("POST", { password }));
export const disconnectGoogle = () => sfetch<User>("/api/auth/me/google/disconnect", { method: "POST" });
export const deleteAccount = (password?: string) =>
  sfetch<void>("/api/auth/me", json("DELETE", { password: password ?? null }));

/** A full-page navigation, not a fetch: Google's consent screen needs the browser. */
export function googleStartUrl(next: string): string {
  return `${API_BASE_URL}/api/auth/google/start?next=${encodeURIComponent(next)}`;
}

// ------------------------------------------------------------------ pins

export const getPinOptions = () => sfetch<PinOptions>("/api/pins/options");

/** Where catches are browsed: a state, a county in it, a lake or river in
 * that. A river is "r<id>" as a place (PinPlace.id); `river` is its id. */
export interface PinScope {
  state?: string;
  county?: string;
  lake?: string;
  river?: string;
}

function scopeQuery(qs: URLSearchParams, scope: PinScope) {
  if (scope.state) qs.set("state", scope.state);
  if (scope.county) qs.set("county", scope.county);
  if (scope.lake?.startsWith("r")) qs.set("river", scope.lake.slice(1));
  else if (scope.lake) qs.set("lake", scope.lake);
  if (scope.river) qs.set("river", scope.river);
}

export function listPins(params: { bbox?: string; species?: string; mine?: boolean; limit?: number } & PinScope = {}) {
  const qs = new URLSearchParams();
  if (params.bbox) qs.set("bbox", params.bbox);
  if (params.species) qs.set("species", params.species);
  if (params.mine) qs.set("mine", "true");
  if (params.limit) qs.set("limit", String(params.limit));
  scopeQuery(qs, params);
  const suffix = qs.toString() ? `?${qs}` : "";
  return sfetch<PinSummary[]>(`/api/pins${suffix}`);
}

/** Other people's catches in view, one group per water (backend ADR 0040). */
export const listWaterGroups = (bbox: string) =>
  sfetch<WaterGroup[]>(`/api/pins/waters?bbox=${encodeURIComponent(bbox)}`);

/** The places one level below `scope` that have catches, with counts. */
export function listPinPlaces(params: { species?: string; mine?: boolean } & Omit<PinScope, "lake" | "river"> = {}) {
  const qs = new URLSearchParams();
  if (params.species) qs.set("species", params.species);
  if (params.mine) qs.set("mine", "true");
  scopeQuery(qs, params);
  const suffix = qs.toString() ? `?${qs}` : "";
  return sfetch<PinPlaces>(`/api/pins/places${suffix}`);
}

/** The county a point is in (not stored by the server). Rounded to ~100 m
 * unless `precise`: placing a catch asks which water is under the pin, and
 * the bank is narrower than that. */
export const pinWhere = (lat: number, lng: number, precise = false) => {
  const digits = precise ? 5 : 3;
  return sfetch<PinWhere>(`/api/pins/where?lat=${lat.toFixed(digits)}&lng=${lng.toFixed(digits)}`);
};

/** What fish a photo shows and, given a species, whether it backs it. The
 * server checks again on save; this is the form's early warning. */
export function identifyFish(photo: File, claim: { species_slug?: string; species_other?: string } = {}) {
  const form = new FormData();
  form.append("photo", photo, photo.name);
  if (claim.species_slug) form.set("species_slug", claim.species_slug);
  if (claim.species_other) form.set("species_other", claim.species_other);
  return sfetch<FishIdResult>("/api/fish-id", { method: "POST", body: form });
}

export const getPin = (id: number) => sfetch<PinDetail>(`/api/pins/${id}`);
export const updatePin = (id: number, patch: PinUpdate) => sfetch<PinDetail>(`/api/pins/${id}`, json("PATCH", patch));
export const deletePin = (id: number) => sfetch<void>(`/api/pins/${id}`, { method: "DELETE" });
export const deletePhoto = (pinId: number, photoId: number) =>
  sfetch<PinDetail>(`/api/pins/${pinId}/photos/${photoId}`, { method: "DELETE" });
export const reportPin = (id: number, reason: string, detail?: string) =>
  sfetch<{ received: boolean; pin_hidden: boolean }>(`/api/pins/${id}/reports`, json("POST", { reason, detail: detail || null }));

/**
 * Multipart upload with progress. fetch() can't report upload progress,
 * and a phone uploading four photos over LTE needs a progress bar more
 * than anyone.
 */
function upload<T>(path: string, form: FormData, onProgress?: (fraction: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}${path}`);
    xhr.withCredentials = true;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
    };
    xhr.onerror = () => reject(new ApiError("Couldn't reach FishEye's server. Is the backend running?", 0));
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        // not JSON
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as T);
      else reject(new ApiError(errorMessage(body, `Upload failed (${xhr.status})`), xhr.status));
    };
    xhr.send(form);
  });
}

export interface NewPin {
  latitude: number;
  longitude: number;
  title: string;
  note?: string;
  species_slug?: string;
  species_other?: string;
  caught_on?: string;
  visibility: "public" | "private";
  // Show others the exact spot; by default they see the lake or county.
  share_exact?: boolean;
  photos: File[];
}

export function createPin(pin: NewPin, onProgress?: (fraction: number) => void): Promise<PinDetail> {
  const form = new FormData();
  form.set("latitude", String(pin.latitude));
  form.set("longitude", String(pin.longitude));
  form.set("title", pin.title);
  form.set("visibility", pin.visibility);
  if (pin.note) form.set("note", pin.note);
  if (pin.species_slug) form.set("species_slug", pin.species_slug);
  if (pin.species_other) form.set("species_other", pin.species_other);
  if (pin.caught_on) form.set("caught_on", pin.caught_on);
  if (pin.share_exact) form.set("share_exact", "true");
  for (const f of pin.photos) form.append("photos", f, f.name);
  return upload<PinDetail>("/api/pins", form, onProgress);
}

export function addPhotos(pinId: number, files: File[], onProgress?: (fraction: number) => void) {
  const form = new FormData();
  for (const f of files) form.append("photos", f, f.name);
  return upload<PinDetail>(`/api/pins/${pinId}/photos`, form, onProgress);
}

// ------------------------------------------------------------ lake reports

export const getLakeReportOptions = () => sfetch<{ reasons: { id: string; label: string }[] }>("/api/lake-reports/options");
export const reportLake = (report: LakeReportInput) =>
  sfetch<{ received: boolean; id: number }>("/api/lake-reports", json("POST", report));

// ----------------------------------------------------------------- admin

export const adminStats = () => sfetch<AdminStats>("/api/admin/stats");
export const adminReports = () => sfetch<AdminReportGroup[]>("/api/admin/reports");
export const adminLakeReports = (status: "open" | "resolved" = "open") =>
  sfetch<AdminLakeReport[]>(`/api/admin/lake-reports?status=${status}`);
export const adminResolveLakeReport = (id: number, resolution: "fixed" | "dismissed", note?: string) =>
  sfetch<void>(`/api/admin/lake-reports/${id}/resolve`, json("POST", { resolution, note: note || null }));
export const adminResolve = (pinId: number, action: "dismiss" | "hide" | "remove", note?: string) =>
  sfetch<AdminPin>(`/api/admin/reports/${pinId}/resolve`, json("POST", { action, note: note || null }));

export function adminPins(params: { status?: string; visibility?: string; state?: string; q?: string; page?: number }) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") qs.set(k, String(v));
  return sfetch<Paged<AdminPin>>(`/api/admin/pins?${qs}`);
}
export const adminSetPinStatus = (pinId: number, status: "published" | "hidden" | "removed", note?: string) =>
  sfetch<AdminPin>(`/api/admin/pins/${pinId}/status`, json("POST", { status, note: note || null }));
export const adminPurgePin = (pinId: number) => sfetch<void>(`/api/admin/pins/${pinId}`, { method: "DELETE" });

export function adminUsers(params: { q?: string; role?: string; status?: string; page?: number }) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") qs.set(k, String(v));
  return sfetch<Paged<AdminUser>>(`/api/admin/users?${qs}`);
}
export const adminUpdateUser = (id: number, patch: { role?: string; status?: string }) =>
  sfetch<AdminUser>(`/api/admin/users/${id}`, json("PATCH", patch));
export const adminAudit = (page = 1) => sfetch<Paged<AuditEntry>>(`/api/admin/audit?page=${page}`);
