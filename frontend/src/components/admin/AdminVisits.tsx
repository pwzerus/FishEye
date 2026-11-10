"use client";

import { useEffect, useState } from "react";

import { useToast } from "@/components/ui/Toast";
import { adminVisits } from "@/lib/api/session";
import type { VisitSummary } from "@/lib/api/types";
import { copyText, errText } from "./shared";

const RANGES = [7, 30, 90] as const;

/** Page views per day, per page and per source (backend services/visits.py).
 * Counts only: nothing here tells one visitor from another. A link tagged
 * ?ref=reddit shows as "ref:reddit". */
export function AdminVisitsTab() {
  const [days, setDays] = useState<number>(30);
  const [data, setData] = useState<VisitSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    adminVisits(days).then(setData).catch((e) => setError(errText(e)));
  }, [days]);

  const peak = Math.max(1, ...(data?.by_day.map((d) => d.count) ?? [1]));

  return (
    <section>
      <div className="row-actions" style={{ marginBottom: 12 }}>
        {RANGES.map((d) => (
          <button
            key={d}
            type="button"
            className={d === days ? "btn btn-primary btn-xs" : "btn btn-ghost btn-xs"}
            onClick={() => setDays(d)}
          >
            {d} days
          </button>
        ))}
        {data && (
          <button
            type="button"
            className="btn btn-ghost btn-xs"
            onClick={() => copyText(data.text).then((ok) => toast(ok ? "Copied." : "Couldn't copy."))}
          >
            Copy as text
          </button>
        )}
      </div>
      {error && <div className="backend-error">{error}</div>}
      {!data ? (
        <div className="sk" style={{ height: 160 }} />
      ) : (
        <>
          <p>
            <strong>{data.total}</strong> page views in the last {data.days} days.
          </p>
          {data.by_day.length > 0 && (
            <table className="data-table">
              <tbody>
                {data.by_day.map((d) => (
                  <tr key={d.key}>
                    <td className="muted small">{d.key}</td>
                    <td style={{ width: "70%" }}>
                      <div
                        aria-hidden="true"
                        style={{ height: 10, borderRadius: 4, background: "var(--brand)", width: `${(d.count / peak) * 100}%` }}
                      />
                    </td>
                    <td>{d.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <h3>Top pages</h3>
          <CountList rows={data.by_page} empty="No visits yet." />
          <h3>Where from</h3>
          <CountList rows={data.by_source.map((s) => ({ ...s, key: s.key || "Direct, or not known" }))} empty="No visits yet." />
        </>
      )}
    </section>
  );
}

function CountList({ rows, empty }: { rows: { key: string; count: number }[]; empty: string }) {
  if (rows.length === 0) return <p className="muted">{empty}</p>;
  return (
    <table className="data-table">
      <tbody>
        {rows.map((r) => (
          <tr key={r.key}>
            <td>{r.key}</td>
            <td>{r.count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
