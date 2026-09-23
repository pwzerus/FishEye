// Admin-only calls (see backend/app/api/admin.py + docs/adr/0003). Kept
// separate from client.ts because these need an admin token header and
// must never be cached — client.ts's apiFetch intentionally caches
// (`next: { revalidate: 30 }`), which is exactly wrong for a live job
// status the user is actively polling.
import type { RefreshStatus, RefreshTrigger } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(init?.headers ?? {}),
      "X-Admin-Token": token,
    },
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail ?? "";
    } catch {
      // response body wasn't JSON — fall back to the bare status
    }
    throw new ApiError(detail || `${path} failed with ${res.status}`, res.status);
  }
  return res.json() as Promise<T>;
}

export function triggerTpwdRefresh(token: string, dryRun: boolean): Promise<RefreshTrigger> {
  const qs = dryRun ? "?dry_run=true" : "";
  return adminFetch<RefreshTrigger>(`/api/admin/tpwd-refresh${qs}`, token, { method: "POST" });
}

export function getTpwdRefreshStatus(token: string): Promise<RefreshStatus> {
  return adminFetch<RefreshStatus>("/api/admin/tpwd-refresh/status", token);
}
