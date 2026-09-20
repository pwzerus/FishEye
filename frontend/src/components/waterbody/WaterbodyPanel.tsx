"use client";

import { useEffect, useState } from "react";

import { ApiError, getWaterbody } from "@/lib/api/client";
import type { WaterbodyDetail } from "@/lib/api/types";

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const color =
    confidence === "confirmed" ? "#15803d" : confidence === "likely" ? "#a16207" : "#6b7280";
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 600,
        color: "white",
        background: color,
        borderRadius: 4,
        padding: "2px 6px",
        textTransform: "uppercase",
      }}
    >
      {confidence}
    </span>
  );
}

export function WaterbodyPanel({ waterbodyId }: { waterbodyId: number | null }) {
  const [detail, setDetail] = useState<WaterbodyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Deliberately no separate `loading` state: react-hooks/set-state-in-effect
  // flags setState called synchronously in an effect body (only calls inside
  // an async callback are fine), so "loading" is derived instead of stored —
  // true whenever we have a selected lake whose data hasn't arrived yet.
  const loading = waterbodyId !== null && detail?.id !== waterbodyId && error === null;

  useEffect(() => {
    if (waterbodyId === null) return;
    let cancelled = false;
    getWaterbody(waterbodyId)
      .then((d) => {
        if (cancelled) return;
        setDetail(d);
        setError(null);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : "Could not load lake details.");
      });
    return () => {
      cancelled = true;
    };
  }, [waterbodyId]);

  if (waterbodyId === null) {
    return (
      <div className="panel-empty">
        <p>Click a lake marker to see access points, confirmed species, and sources.</p>
      </div>
    );
  }

  if (loading) return <div className="panel-empty">Loading…</div>;
  if (error) return <div className="panel-empty panel-error">{error}</div>;
  if (!detail) return null;

  return (
    <div className="panel">
      <h2>
        {detail.name}
        {detail.field_tested && <span className="field-tested-tag">field-tested</span>}
      </h2>
      <p className="access-summary">{detail.access_summary}</p>
      <p className="source-line">
        Source:{" "}
        <a href={detail.source_url} target="_blank" rel="noreferrer">
          {new URL(detail.source_url).hostname}
        </a>{" "}
        · updated {new Date(detail.source_updated_at).toLocaleDateString()}
      </p>

      <h3>Confirmed public access points</h3>
      <ul className="access-list">
        {detail.access_points.map((ap) => (
          <li key={ap.id}>
            <strong>{ap.name}</strong> — {ap.access_type}
            {ap.parking ? ", parking available" : ""}
            <span className="public-status">{ap.public_status.replace("_", " ")}</span>
          </li>
        ))}
        {detail.access_points.length === 0 && <li className="muted">No access points on file yet.</li>}
      </ul>

      <h3>Species</h3>
      <ul className="species-list">
        {detail.species.map((s) => (
          <li key={s.common_name}>
            <div className="species-row">
              <strong>{s.common_name}</strong>
              <ConfidenceBadge confidence={s.confidence} />
            </div>
            <p className="evidence">{s.evidence}</p>
          </li>
        ))}
        {detail.species.length === 0 && (
          <li className="muted">No confirmed species on file yet — never assumed from a statewide list.</li>
        )}
      </ul>
    </div>
  );
}
