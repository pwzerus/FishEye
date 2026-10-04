"use client";

// Manual TPWD-refresh trigger (docs/adr/0003-tpwd-manual-refresh.md). Signed-in
// admins are authorised by their session; the shared token field is only
// for backends where accounts aren't set up.

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, getTpwdRefreshStatus, triggerTpwdRefresh } from "@/lib/api/adminClient";
import type { RefreshStatus } from "@/lib/api/types";

const POLL_INTERVAL_MS = 2000;

export function TpwdRefresh() {
  const [token, setToken] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [status, setStatus] = useState<RefreshStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
    setIsPolling(false);
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const check = useCallback(
    async (t: string) => {
      try {
        const s = await getTpwdRefreshStatus(t);
        setStatus(s);
        if (s.status !== "running") stopPolling();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch refresh status.");
        stopPolling();
      }
    },
    [stopPolling],
  );

  // Show the last run's result when the tab opens.
  useEffect(() => {
    getTpwdRefreshStatus("")
      .then(setStatus)
      .catch(() => undefined);
  }, []);

  async function trigger() {
    setError(null);
    const t = token.trim();
    try {
      await triggerTpwdRefresh(t, dryRun);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("A refresh is already running. Showing its progress.");
      } else if (err instanceof ApiError && (err.status === 401 || err.status === 503)) {
        setError(err.status === 401 ? "Not authorised." : "The backend has no admin token configured.");
        return;
      } else {
        setError(err instanceof Error ? err.message : "Failed to start the refresh.");
        return;
      }
    }
    setIsPolling(true);
    void check(t);
    pollRef.current = setInterval(() => void check(t), POLL_INTERVAL_MS);
  }

  return (
    <div className="admin-panel">
      <p className="muted">
        Runs the TPWD lake-survey scraper against the live TPWD site. See ADR 0002 and 0003 for what it does and why
        it&apos;s a button rather than a schedule.
      </p>
      <div className="tpwd-controls">
        <label className="check-row">
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
          Dry run (fetch and parse only; don&apos;t write to the database)
        </label>
        <details className="token-details">
          <summary>Use a shared admin token instead</summary>
          <label className="field">
            <span>X-Admin-Token</span>
            <input type="password" value={token} onChange={(e) => setToken(e.target.value)} autoComplete="off" />
          </label>
        </details>
        <button type="button" className="btn btn-primary btn-sm" onClick={trigger} disabled={isPolling}>
          {isPolling ? (
            <>
              <span className="spinner" aria-hidden="true" /> Refreshing…
            </>
          ) : (
            "Refresh TPWD data"
          )}
        </button>
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {status && (
        <section className="tpwd-status">
          <h3>
            Status: <code>{status.status}</code>
          </h3>
          {status.total_written !== null && status.total_written !== undefined && (
            <p>
              {status.dry_run ? "Would write" : "Wrote"} {status.total_written} species link(s)
              {status.dry_run ? "; dry run, nothing saved." : "."}
            </p>
          )}
          {status.error && <p className="form-error">Last run failed: {status.error}</p>}
          {status.lake_results && status.lake_results.length > 0 && (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Lake</th>
                    <th>Result</th>
                    <th className="num">Species</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {status.lake_results.map((r) => (
                    <tr key={r.name}>
                      <td>{r.name}</td>
                      <td>{r.status}</td>
                      <td className="num">{r.species_written}</td>
                      <td className="muted">{r.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
