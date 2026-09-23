"use client";

// Manual TPWD-refresh trigger for the demo's one operator (me). See
// docs/adr/0003-tpwd-manual-refresh.md for why this is a button hitting
// this backend's own API rather than anything running in the visitor's
// browser, and why the auth here is a single shared token rather than a
// real accounts system.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getTpwdRefreshStatus, triggerTpwdRefresh } from "@/lib/api/adminClient";
import type { RefreshStatus } from "@/lib/api/types";

const TOKEN_STORAGE_KEY = "fishpilot_admin_token";
const POLL_INTERVAL_MS = 2000;

function readSavedToken(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(TOKEN_STORAGE_KEY) ?? "";
  } catch {
    // sessionStorage unavailable (private browsing, etc.) — fine, the
    // field just starts empty.
    return "";
  }
}

export default function AdminPage() {
  const [token, setToken] = useState<string>(readSavedToken);
  const [dryRun, setDryRun] = useState(true);
  const [status, setStatus] = useState<RefreshStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const checkStatusOnce = useCallback(
    async (currentToken: string) => {
      try {
        const s = await getTpwdRefreshStatus(currentToken);
        setStatus(s);
        if (s.status !== "running") {
          stopPolling();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch refresh status.");
        stopPolling();
      }
    },
    [stopPolling],
  );

  const startPolling = useCallback(
    (currentToken: string) => {
      setIsPolling(true);
      void checkStatusOnce(currentToken);
      pollIntervalRef.current = setInterval(() => {
        void checkStatusOnce(currentToken);
      }, POLL_INTERVAL_MS);
    },
    [checkStatusOnce],
  );

  const handleTriggerClick = async () => {
    setError(null);
    const trimmed = token.trim();
    if (!trimmed) {
      setError("Admin token is required.");
      return;
    }
    try {
      window.sessionStorage.setItem(TOKEN_STORAGE_KEY, trimmed);
    } catch {
      // non-fatal — token just won't be remembered on reload
    }

    try {
      await triggerTpwdRefresh(trimmed, dryRun);
      startPolling(trimmed);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("A refresh is already running — showing its progress.");
        startPolling(trimmed);
        return;
      }
      if (err instanceof ApiError && err.status === 401) {
        setError("Invalid admin token.");
        return;
      }
      if (err instanceof ApiError && err.status === 503) {
        setError("Admin endpoints aren't configured on the backend (ADMIN_API_TOKEN is unset).");
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to start the refresh.");
    }
  };

  return (
    <main
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: "2rem 1.25rem",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>Admin — TPWD Data Refresh</h1>
      <p style={{ color: "#666", marginBottom: "1.5rem" }}>
        Manually runs the TPWD lake-survey scraper against the live TPWD site.
        See docs/adr/0002 and 0003 for what it does and why this exists instead
        of a fully automated schedule.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem", maxWidth: 420 }}>
        <label style={{ display: "block" }}>
          <span style={{ display: "block", marginBottom: "0.25rem", fontWeight: 600 }}>Admin token</span>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="X-Admin-Token"
            style={{ width: "100%", padding: "0.5rem", boxSizing: "border-box" }}
          />
        </label>

        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
          Dry run (fetch + parse only — don&apos;t write to the database)
        </label>

        <button
          onClick={handleTriggerClick}
          disabled={isPolling}
          style={{
            padding: "0.65rem 1.25rem",
            fontWeight: 600,
            width: "fit-content",
            cursor: isPolling ? "not-allowed" : "pointer",
            opacity: isPolling ? 0.6 : 1,
          }}
        >
          {isPolling ? "Refreshing…" : "Refresh TPWD Data"}
        </button>
      </div>

      {error && (
        <p style={{ color: "#b00020", marginTop: "1.25rem" }} role="alert">
          {error}
        </p>
      )}

      {status && (
        <section style={{ marginTop: "1.75rem" }}>
          <h2 style={{ fontSize: "1.1rem" }}>
            Status: <span style={{ fontFamily: "monospace" }}>{status.status}</span>
          </h2>

          {status.total_written !== null && status.total_written !== undefined && (
            <p>
              {status.dry_run ? "Would write" : "Wrote"} {status.total_written} species link(s)
              {status.dry_run ? " — dry run, nothing persisted." : "."}
            </p>
          )}

          {status.error && <p style={{ color: "#b00020" }}>Last run failed: {status.error}</p>}

          {status.lake_results && status.lake_results.length > 0 && (
            <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "1rem", fontSize: "0.9rem" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: "0.35rem 0" }}>
                    Lake
                  </th>
                  <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: "0.35rem 0" }}>
                    Result
                  </th>
                  <th style={{ textAlign: "right", borderBottom: "1px solid #ccc", padding: "0.35rem 0" }}>
                    Species
                  </th>
                  <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: "0.35rem 0" }}>
                    Detail
                  </th>
                </tr>
              </thead>
              <tbody>
                {status.lake_results.map((r) => (
                  <tr key={r.name}>
                    <td style={{ padding: "0.35rem 0" }}>{r.name}</td>
                    <td style={{ padding: "0.35rem 0" }}>{r.status}</td>
                    <td style={{ padding: "0.35rem 0", textAlign: "right" }}>{r.species_written}</td>
                    <td style={{ padding: "0.35rem 0", color: "#777" }}>{r.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </main>
  );
}
