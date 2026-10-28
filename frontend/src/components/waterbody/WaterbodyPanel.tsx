"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ContentSkeleton } from "@/components/ui/ContentSkeleton";

import { ApiError, getWaterbody } from "@/lib/api/client";
import type { AccessPoint, FishAttractor, SpeciesSummary, WaterbodyDetail } from "@/lib/api/types";
import { SpeciesHowTo } from "@/components/species/SpeciesHowTo";
import { AgencyProfileCard } from "./AgencyProfileCard";
import { NearbyShops } from "./NearbyShops";
import { ReportedSpeciesList } from "./ReportedSpeciesList";
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

const ATTRACTOR_SOURCES: Record<string, string> = { ga_wrd: "Georgia WRD" };

/** Fish attractors the state agency sank in this lake: fixed places fish
 * gather, drawn on the lake map. Says who placed them and when, because an
 * old brush pile may have broken down. */
function AttractorNote({ attractors }: { attractors: FishAttractor[] }) {
  if (attractors.length === 0) return null;
  const years = attractors.map((a) => a.placed_year).filter((y): y is number => y !== null);
  const span =
    years.length === 0
      ? ""
      : Math.min(...years) === Math.max(...years)
        ? `, placed in ${years[0]}`
        : `, placed ${Math.min(...years)}–${Math.max(...years)}`;
  const n = attractors.length;
  const by = ATTRACTOR_SOURCES[attractors[0].source] ?? "the state agency";
  return (
    <>
      <h3>Fish attractors</h3>
      <p className="attractor-note">
        {n} fish-holding structure{n === 1 ? '' : 's'} by {by}{span}. Teal dots on the map; older structures may have broken down.
      </p>
    </>
  );
}

/** Why a fish is on the list: each official fact, in FishEye's own words,
 * with a link to the source (data-sourcing rule 3). */
function SpeciesEvidence({ species }: { species: SpeciesSummary }) {
  const items = species.evidence_items ?? [];
  return (
    <details className="lake-evidence">
      <summary>Why this fish is listed</summary>
      {items.length > 0 ? (
        <ul className="evidence-list">
          {items.map((e, i) => (
            <li key={`${i}-${e.kind}-${e.source_url}`}>
              {e.evidence}{" "}
              <a href={e.source_url} target="_blank" rel="noreferrer">Source ↗</a>
            </li>
          ))}
        </ul>
      ) : (
        <p className="evidence">
          {species.evidence}{" "}
          <a href={species.source_url} target="_blank" rel="noreferrer">Source ↗</a>
        </p>
      )}
    </details>
  );
}

/** PAD-US says the lake lies in land the public may enter. A fact about the
 * land around it, not a confirmed entrance. */
function publicLandSentence(detail: WaterbodyDetail): string | null {
  if (!detail.public_land) return null;
  const where = detail.public_land_name ? `in ${detail.public_land_name}` : "on public land";
  const by = detail.public_land_manager && detail.public_land_manager !== "Unknown" ? ` (${detail.public_land_manager})` : "";
  return detail.public_land === "open"
    ? `It lies ${where}${by}, land open to the public (PAD-US).`
    : `It lies ${where}${by}, public land with limited access: permits, seasons or hours (PAD-US).`;
}

// A big reservoir can have fifty official ramps; the panel shows a few and
// lets the rest be opened.
const ACCESS_SHOWN_AT_FIRST = 5;

function AccessPointList({ points, emptyText }: { points: AccessPoint[]; emptyText: string }) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? points : points.slice(0, ACCESS_SHOWN_AT_FIRST);
  const hidden = points.length - shown.length;
  return (
    <ul className="access-list">
      {shown.map((ap) => (
        <li key={ap.id}>
          <strong>{ap.name}</strong> — {ap.access_type.replace("_", " ")}
          {ap.parking ? ", parking available" : ""}
          {ap.public_status === "osm_reported" ? (
            <span className="public-status public-status-unverified">reported, not verified</span>
          ) : (
            <span className="public-status">{ap.public_status.replace("_", " ")}</span>
          )}
          <div><a className="lake-navigate" href={`https://www.google.com/maps/dir/?api=1&destination=${ap.latitude},${ap.longitude}`} target="_blank" rel="noreferrer">Directions to this entrance ↗</a></div>
        </li>
      ))}
      {hidden > 0 && (
        <li>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowAll(true)}>
            Show all {points.length}
          </button>
        </li>
      )}
      {points.length === 0 && <li className="muted">{emptyText}</li>}
    </ul>
  );
}

export function WaterbodyPanel({ waterbodyId, onExplore }: { waterbodyId: number | null; onExplore?: (point: { latitude: number; longitude: number; label: string }) => void }) {
  const [detail, setDetail] = useState<WaterbodyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failedId, setFailedId] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [tab, setTab] = useState<"access" | "fish" | "sources">("access");

  // Deliberately no separate `loading` state: react-hooks/set-state-in-effect
  // flags setState called synchronously in an effect body (only calls inside
  // an async callback are fine), so "loading" is derived instead of stored —
  // true whenever we have a selected lake whose data hasn't arrived yet.
  const loading = waterbodyId !== null && detail?.id !== waterbodyId && !(error && failedId === waterbodyId);

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
        setFailedId(waterbodyId);
      });
    return () => {
      cancelled = true;
    };
  }, [waterbodyId, attempt]);

  if (waterbodyId === null) {
    return (
      <div className="panel-empty">
        <div className="map-welcome">
          <p className="field-kicker">FIND WATER</p>
          <h2>Where to?</h2>
          <p>Search a place or choose a highlighted state.</p>
          {onExplore && <div className="quick-places" aria-label="Explore a city">{[
            { label: 'Austin', latitude: 30.2672, longitude: -97.7431 },
            { label: 'Atlanta', latitude: 33.749, longitude: -84.388 },
            { label: 'Sacramento', latitude: 38.5816, longitude: -121.4944 },
          ].map((place) => <button type="button" key={place.label} onClick={() => onExplore(place)}>{place.label} ↗</button>)}</div>}
          <div className="map-how"><span>1 · Pick a lake</span><span>2 · Check entrances</span><span>3 · See your plan</span></div>
          <Link href="/fish" className="field-secondary">First time? Choose a fish →</Link>
        </div>
      </div>
    );
  }

  if (loading) return <ContentSkeleton label="Loading lake…" />;
  if (error && failedId === waterbodyId) return <div className="panel-empty panel-error" role="alert"><p>{error}</p><button type="button" className="btn btn-ghost btn-sm" onClick={() => { setError(null); setAttempt((value) => value + 1); }}>Try again</button></div>;
  if (!detail) return null;

  const isClosed = detail.public_access_status === "closed";
  // A lake from the statewide OpenStreetMap layer: the app knows it exists,
  // nothing more. See backend/app/models/waterbody.py (data_tier).
  const isOsm = detail.data_tier === "osm";
  const isPond = detail.water_type === "pond";
  // Its name points at private land (a club, an estate, a ranch): the OSM
  // import marks it so (backend docs/adr/0032).
  const isLikelyPrivate = detail.public_access_status === "likely_private";
  // A verified lake whose agency lists no boat ramp keeps OpenStreetMap's
  // entrances, each labelled "reported, not verified"; the heading mustn't
  // call them confirmed.
  const allConfirmed = detail.access_points.every((ap) => ap.public_status === "confirmed_public");
  // An unverified lake is mapped by OpenStreetMap, or in California only by
  // CDFW's lake layer (backend cdfw_import.py).
  const mappedBy = detail.source_url.includes("openstreetmap.org") ? "OpenStreetMap" : "CDFW's California Lakes map";
  const onPublicLand = publicLandSentence(detail);

  return (
    <div className="panel">
      <h2>
        {detail.name}
        {detail.field_tested && <span className="field-tested-tag">field-tested</span>}
        {isClosed && <span className="closed-tag">closed to the public</span>}
        {isOsm && <span className="unverified-tag">unverified</span>}
        {isLikelyPrivate && <span className="private-tag">probably private</span>}
      </h2>

      {isOsm && (
        <div className="unverified-banner">
          <strong>Unverified lake from {mappedBy}.</strong>{" "}
          {onPublicLand && detail.public_land === "open"
            ? <>{onPublicLand} Check local rules and where to park before you go.</>
            : onPublicLand
              ? <>{onPublicLand} Check the rules before you go.</>
              : <>Clearly private lakes are left out, but some may remain, so check access before you go.</>}
          <details className="data-note"><summary>About this data</summary><p>{mappedBy === "OpenStreetMap" ? "OpenStreetMap is a community-edited map." : "California's Department of Fish and Wildlife maps this lake."} FishEye hasn&apos;t verified this lake&apos;s entrances; any fish listed come from official sources.</p></details>
        </div>
      )}

      {isLikelyPrivate && (
        <div className="private-warning">
          Its name suggests private land. Confirm public access or get the owner&apos;s permission.
        </div>
      )}

      {isOsm && isPond && !isLikelyPrivate && detail.public_land !== "open" && detail.access_points.length === 0 && (
        // Ponds with no reported entrance get their own, louder warning: in
        // Texas many are on ranches, in gated neighborhoods or on golf
        // courses, and unlike a reservoir there's rarely an official access
        // page to check. A pond with an entrance listed gets only the short
        // banner above.
        <div className="pond-warning">
          Many ponds are on private land. Fish only in a public park or with permission.
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
          Closed to public access. No entrances or fishing plan are shown.
        </div>
      )}

      {/* An OSM lake's summary repeats the banner above, so it's skipped. */}
      <div className="lake-facts"><span>{detail.access_points.filter((a) => a.public_status === "confirmed_public").length} confirmed entrances</span><span>{isOsm && detail.species.length === 0 ? `${detail.reported_species?.length ?? 0} species reported` : `${detail.species.length} species listed`}</span></div>
      {!isClosed && <WeatherRecommendations key={`weather-${detail.id}`} waterbodyId={detail.id} latitude={detail.latitude} longitude={detail.longitude} />}

      <div className="lake-tabs" role="tablist" aria-label="Lake information">
        {([['access', 'Entrances'], ['fish', 'Fish'], ['sources', 'Sources']] as const).map(([id, label]) => <button key={id} id={`lake-tab-${id}`} role="tab" tabIndex={tab === id ? 0 : -1} aria-selected={tab === id} aria-controls={`lake-panel-${id}`} onClick={() => setTab(id)} onKeyDown={(event) => {
          const keys = ['access', 'fish', 'sources'] as const;
          if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
          event.preventDefault();
          const index = keys.indexOf(tab);
          const next = keys[event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (index + (event.key === 'ArrowRight' ? 1 : 2)) % 3];
          setTab(next);
          document.getElementById(`lake-tab-${next}`)?.focus();
        }}>{label}</button>)}
      </div>
      <section id="lake-panel-sources" role="tabpanel" aria-labelledby="lake-tab-sources" hidden={tab !== "sources"}>
      {!isOsm && <p className="access-summary">{detail.access_summary}</p>}
      <p className="source-line">
        Source:{" "}
        <a href={detail.source_url} target="_blank" rel="noreferrer">
          {new URL(detail.source_url).hostname}
        </a>{" "}
        · {isOsm ? "imported" : "updated"}{" "}
        {new Date(detail.source_updated_at).toLocaleDateString()}
      </p>
      {detail.official_name && <p className="source-line">Official name: {detail.official_name}</p>}
      {detail.source_url.includes("openstreetmap.org") && (
        <p className="data-credit">Map data © OpenStreetMap contributors (ODbL)</p>
      )}

      {detail.agency_profile && <AgencyProfileCard profile={detail.agency_profile} credit={detail.data_credit ?? null} />}
      {!detail.agency_profile && detail.data_credit && <p className="data-credit">{detail.data_credit}</p>}
      {(detail.sources?.length ?? 0) > 0 && (
        <>
          <h3>Data sources</h3>
          <ul className="dataset-sources">
            {detail.sources!.map((src) => (
              <li key={src.url}>
                <a href={src.url} target="_blank" rel="noreferrer">{src.title}</a> · {src.publisher}
                {src.licence && <span className="dataset-licence"> · {src.licence}</span>}
                {src.citation && <div className="dataset-licence">{src.citation}</div>}
              </li>
            ))}
          </ul>
        </>
      )}
      </section>

      <section id="lake-panel-access" role="tabpanel" aria-labelledby="lake-tab-access" hidden={tab !== "access"}>
      <h3>
        {isOsm
          ? "Entrances reported on OpenStreetMap"
          : allConfirmed
            ? "Confirmed public access points"
            : "Public access points"}
      </h3>
      <AccessPointList
        // Keyed by lake, so "show all" doesn't carry over to the next lake.
        // The prefix matters: a sibling below is keyed by the lake too, and
        // two siblings may not share a key.
        key={`access-${detail.id}`}
        points={detail.access_points}
        emptyText={
          isOsm
            ? "OpenStreetMap doesn't list a public boat ramp or fishing pier here."
            : "No access points on file yet."
        }
      />

      {onPublicLand && !isOsm && <p className="public-land-note">{onPublicLand}</p>}
      {!isClosed && <AttractorNote attractors={detail.fish_attractors ?? []} />}
      {!isClosed && <NearbyShops key={`shops-${detail.id}`} latitude={detail.latitude} longitude={detail.longitude} />}
      </section>

      {/* A verified lake shows its official list, then any species on record
          that the survey doesn't mention. An unverified lake shows the fish
          an official source names there (a survey, a state record), if any,
          then the outside records. */}
      <section id="lake-panel-fish" role="tabpanel" aria-labelledby="lake-tab-fish" hidden={tab !== "fish"}>
      {(!isOsm || detail.species.length > 0) && (
        <>
          <h3>{isOsm ? "Fish named by official sources" : "Species"}</h3>
          <ul className="species-list">
            {detail.species.map((s) => (
              <li key={s.common_name}>
                <div className="species-row">
                  <strong>{s.common_name}</strong>
                  <ConfidenceBadge confidence={s.confidence} />
                </div>
                <SpeciesEvidence species={s} />
                <SpeciesHowTo commonName={s.common_name} />
              </li>
            ))}
            {detail.species.length === 0 && (
              <li className="muted">
                No confirmed species on file yet — never assumed from a statewide list.
              </li>
            )}
          </ul>
        </>
      )}
      <ReportedSpeciesList reported={detail.reported_species ?? []} isOsm={isOsm} />
      </section>
    </div>
  );
}
