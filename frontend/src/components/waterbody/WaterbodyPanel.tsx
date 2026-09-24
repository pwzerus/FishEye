"use client";

import { useEffect, useState } from "react";

import { ApiError, getWaterbody } from "@/lib/api/client";
import type { WaterbodyDetail } from "@/lib/api/types";
import { SpeciesHowTo } from "@/components/species/SpeciesHowTo";
import { AdvisorPanel } from "./AdvisorPanel";
import { WeatherRecommendations } from "./WeatherRecommendations";

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
  // Shared by the recommendations panel (which owns the <select>) and the
  // advisor panel below it, so both are always talking about the same fish.
  const [targetSpecies, setTargetSpecies] = useState<string>("");

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

  const isClosed = detail.public_access_status === "closed";
  // A lake from the statewide OpenStreetMap layer: the app knows it exists,
  // nothing more. See backend/app/models/waterbody.py (data_tier).
  const isOsm = detail.data_tier === "osm";
  const isPond = detail.water_type === "pond";

  return (
    <div className="panel">
      <h2>
        {detail.name}
        {detail.field_tested && <span className="field-tested-tag">field-tested</span>}
        {isClosed && <span className="closed-tag">closed to the public</span>}
        {isOsm && <span className="unverified-tag">unverified</span>}
      </h2>

      {isOsm && (
        <div className="unverified-banner">
          This lake comes from OpenStreetMap, a community-edited map. FishMate hasn&apos;t
          verified its fish or public access. Any entrances below are what OpenStreetMap
          reports: confirm they&apos;re open to the public before you go.
        </div>
      )}

      {isOsm && isPond && (
        // Ponds get their own, louder warning: in Texas many are on ranches,
        // in gated neighborhoods or on golf courses, and unlike a reservoir
        // there's rarely an official access page to check.
        <div className="pond-warning">
          Many ponds are on private land (ranches, neighborhoods, golf courses). Only fish
          here if it&apos;s in a public park or you have permission.
        </div>
      )}

      {isClosed && (
        // Deliberately shown above everything else and never suppressed:
        // PRD §12 says never present unconfirmed/closed access as public,
        // so a lake TPWD's own source says is closed must say so loudly,
        // not just quietly have an empty access-points list (which also
        // happens to be what "no data yet" looks like — a very different
        // situation this banner exists to avoid conflating).
        <div className="closed-banner">
          This lake is currently closed to public access, per its official
          source. No public access points are shown, and weather-based
          recommendations are not scored for it below.
        </div>
      )}

      {/* An OSM lake's summary repeats the banner above, so it's skipped. */}
      {!isOsm && <p className="access-summary">{detail.access_summary}</p>}
      <p className="source-line">
        Source:{" "}
        <a href={detail.source_url} target="_blank" rel="noreferrer">
          {new URL(detail.source_url).hostname}
        </a>{" "}
        · {isOsm ? "imported" : "updated"}{" "}
        {new Date(detail.source_updated_at).toLocaleDateString()}
      </p>

      <h3>{isOsm ? "Entrances reported on OpenStreetMap" : "Confirmed public access points"}</h3>
      <ul className="access-list">
        {detail.access_points.map((ap) => (
          <li key={ap.id}>
            <strong>{ap.name}</strong> — {ap.access_type.replace("_", " ")}
            {ap.parking ? ", parking available" : ""}
            {ap.public_status === "osm_reported" ? (
              <span className="public-status public-status-unverified">
                reported, not verified
              </span>
            ) : (
              <span className="public-status">{ap.public_status.replace("_", " ")}</span>
            )}
          </li>
        ))}
        {detail.access_points.length === 0 && (
          <li className="muted">
            {isOsm
              ? "OpenStreetMap doesn't list a public boat ramp or fishing pier here."
              : "No access points on file yet."}
          </li>
        )}
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
            <SpeciesHowTo commonName={s.common_name} />
          </li>
        ))}
        {detail.species.length === 0 && (
          <li className="muted">
            {isOsm
              ? "Fish species not verified for this lake. FishMate only lists species from official surveys, never guesses."
              : "No confirmed species on file yet — never assumed from a statewide list."}
          </li>
        )}
      </ul>

      {!isClosed && (
        <>
          <WeatherRecommendations
            waterbodyId={detail.id}
            latitude={detail.latitude}
            longitude={detail.longitude}
            species={detail.species}
            targetSpecies={targetSpecies}
            onTargetSpeciesChange={setTargetSpecies}
          />
          {/* Below the ranking, not above it: the scored candidates are the
              product, and the written explanation is commentary on them.
              Not offered for unverified lakes: there is no ranking or
              species evidence for it to explain. */}
          {!isOsm && <AdvisorPanel waterbodyId={detail.id} targetSpecies={targetSpecies} />}
        </>
      )}
    </div>
  );
}
