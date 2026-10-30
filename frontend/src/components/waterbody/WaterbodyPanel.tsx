"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ContentSkeleton } from "@/components/ui/ContentSkeleton";

import { useLocaleTag, useT } from "@/i18n/client";
import type { Messages } from "@/i18n/messages";
import { fishSlug } from "@/i18n/names";
import { ApiError, getWaterbody } from "@/lib/api/client";
import { listPins } from "@/lib/api/session";
import type { AccessPoint, FishAttractor, PinSummary, SpeciesSummary, WaterbodyDetail } from "@/lib/api/types";
import { CATCHES_AVAILABLE } from "@/lib/features";
import { FishName } from "@/components/fish/FishName";
import { SpeciesHowTo } from "@/components/species/SpeciesHowTo";
import { AgencyProfileCard } from "./AgencyProfileCard";
import { LakeReportDialog } from "./LakeReportDialog";
import { LakeRulesRow } from "./LakeRulesRow";
import { NearbyShops } from "./NearbyShops";
import { ReportedSpeciesList } from "./ReportedSpeciesList";
import { WeatherRecommendations } from "./WeatherRecommendations";

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const t = useT().lake;
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
      {t.confidence[confidence] ?? confidence}
    </span>
  );
}

const ATTRACTOR_SOURCES: Record<string, string> = { ga_wrd: "Georgia WRD" };

/** Fish attractors the state agency sank in this lake: fixed places fish
 * gather, drawn on the lake map. Says who placed them and when, because an
 * old brush pile may have broken down. */
function AttractorNote({ attractors }: { attractors: FishAttractor[] }) {
  const t = useT().lake;
  if (attractors.length === 0) return null;
  const years = attractors.map((a) => a.placed_year).filter((y): y is number => y !== null);
  const span =
    years.length === 0
      ? ""
      : Math.min(...years) === Math.max(...years)
        ? t.attractorYear(years[0])
        : t.attractorYears(Math.min(...years), Math.max(...years));
  const by = ATTRACTOR_SOURCES[attractors[0].source] ?? t.stateAgency;
  return (
    <>
      <h3>{t.attractors}</h3>
      <p className="attractor-note">{t.attractorNote(attractors.length, by, span)}</p>
    </>
  );
}

/** Why a fish is on the list: each official fact, in FishEye's own words,
 * with a link to the source (data-sourcing rule 3). Written in English. */
function SpeciesEvidence({ species }: { species: SpeciesSummary }) {
  const t = useT().lake;
  const items = species.evidence_items ?? [];
  return (
    <details className="lake-evidence">
      <summary>{t.whyListed}</summary>
      {items.length > 0 ? (
        <ul className="evidence-list" lang="en">
          {items.map((e, i) => (
            <li key={`${i}-${e.kind}-${e.source_url}`}>
              {e.evidence}{" "}
              <a href={e.source_url} target="_blank" rel="noreferrer">{t.sourceLink}</a>
            </li>
          ))}
        </ul>
      ) : (
        <p className="evidence" lang="en">
          {species.evidence}{" "}
          <a href={species.source_url} target="_blank" rel="noreferrer">{t.sourceLink}</a>
        </p>
      )}
    </details>
  );
}

/** PAD-US says the lake lies in land the public may enter. A fact about the
 * land around it, not a confirmed entrance. */
function publicLandSentence(t: Messages["lake"], detail: WaterbodyDetail): string | null {
  if (!detail.public_land) return null;
  const where = detail.public_land_name ? t.inPlace(detail.public_land_name) : t.onPublicLand;
  const by = detail.public_land_manager && detail.public_land_manager !== "Unknown" ? ` (${detail.public_land_manager})` : "";
  return detail.public_land === "open" ? t.publicLandOpen(where, by) : t.publicLandLimited(where, by);
}

// A big reservoir can have fifty official ramps; the panel shows a few and
// lets the rest be opened.
const ACCESS_SHOWN_AT_FIRST = 5;

// An unnamed OpenStreetMap point is named for its kind by the import
// ("Boat ramp (OpenStreetMap)", osm_waterbody_import.py): shown as its kind,
// once, in the reader's words, not as that name followed by the kind again.
const GENERIC_ACCESS_NAME = /^(Boat ramp|Fishing pier|Fishing spot) \(OpenStreetMap\)$/;

function AccessPointList({ points, emptyText }: { points: AccessPoint[]; emptyText: string }) {
  const all = useT();
  const t = all.lake;
  const kindOf = (ap: AccessPoint) => all.map.accessTypes[ap.access_type] ?? ap.access_type.replace("_", " ");
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? points : points.slice(0, ACCESS_SHOWN_AT_FIRST);
  const hidden = points.length - shown.length;
  return (
    <ul className="access-list">
      {shown.map((ap) => (
        <li key={ap.id}>
          {GENERIC_ACCESS_NAME.test(ap.name) ? (
            <strong>{t.osmPoint(kindOf(ap))}</strong>
          ) : (
            <>
              <strong>{ap.name}</strong> — {kindOf(ap)}
            </>
          )}
          {ap.parking ? all.map.parking : ""}
          {ap.public_status === "osm_reported" ? (
            <span className="public-status public-status-unverified">{t.reportedNotVerified}</span>
          ) : (
            <span className="public-status">{t.statuses[ap.public_status] ?? ap.public_status.replace("_", " ")}</span>
          )}
          <div><a className="lake-navigate" href={`https://www.google.com/maps/dir/?api=1&destination=${ap.latitude},${ap.longitude}`} target="_blank" rel="noreferrer">{t.directionsToEntrance}</a></div>
        </li>
      ))}
      {hidden > 0 && (
        <li>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowAll(true)}>
            {t.showAll(points.length)}
          </button>
        </li>
      )}
      {points.length === 0 && <li className="muted">{emptyText}</li>}
    </ul>
  );
}

/** "5 catches shared here →": the anglers' catches on this lake (backend
 * ADR 0040), on the catches page. Nothing while there are none. */
function LakeCatches({ lakeId }: { lakeId: number }) {
  const t = useT().lake;
  const [pins, setPins] = useState<PinSummary[] | null>(null);
  useEffect(() => {
    let cancelled = false;
    listPins({ lake: String(lakeId), limit: 100 })
      .then((p) => !cancelled && setPins(p))
      .catch(() => !cancelled && setPins([]));
    return () => {
      cancelled = true;
    };
  }, [lakeId]);
  const first = pins?.find((p) => p.state_code && p.county_geoid);
  if (!pins || pins.length === 0 || !first) return null;
  const q = new URLSearchParams({ state: first.state_code!, county: first.county_geoid!, lake: String(lakeId) });
  return (
    <Link href={`/community?${q}`} className="lake-catches">
      <span className="legend-catch" aria-hidden="true" /> {t.catchesHere(pins.length)}
    </Link>
  );
}

export function WaterbodyPanel({
  waterbodyId,
  onExplore,
  onMissingLake,
  onShareHere,
}: {
  waterbodyId: number | null;
  onExplore?: (point: { latitude: number; longitude: number; label: string }) => void;
  // "Missing a lake?": tell FishEye about one that isn't on the map.
  onMissingLake?: () => void;
  // "Share a catch here": place a catch on this lake.
  onShareHere?: (lake: WaterbodyDetail) => void;
}) {
  const all = useT();
  const t = all.lake;
  const tag = useLocaleTag();
  const [detail, setDetail] = useState<WaterbodyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failedId, setFailedId] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [tab, setTab] = useState<"access" | "fish" | "sources">("access");
  const [reporting, setReporting] = useState(false);
  const [reported, setReported] = useState<number | null>(null);

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
        setError(e instanceof ApiError ? e.message : t.loadError);
        setFailedId(waterbodyId);
      });
    return () => {
      cancelled = true;
    };
  }, [waterbodyId, attempt, t.loadError]);

  if (waterbodyId === null) {
    return (
      <div className="panel-empty">
        <div className="map-welcome">
          <p className="field-kicker">{t.welcomeKicker}</p>
          <h2>{t.welcomeTitle}</h2>
          <p>{t.welcomeText}</p>
          {onExplore && <div className="quick-places" aria-label={t.exploreCity}>{[
            { label: 'Austin', latitude: 30.2672, longitude: -97.7431 },
            { label: 'Atlanta', latitude: 33.749, longitude: -84.388 },
            { label: 'Sacramento', latitude: 38.5816, longitude: -121.4944 },
          ].map((place) => <button type="button" key={place.label} onClick={() => onExplore(place)}>{place.label} ↗</button>)}</div>}
          <div className="map-how"><span>{t.how1}</span><span>{t.how2}</span><span>{t.how3}</span></div>
          <Link href="/start" className="field-secondary">{t.firstTime}</Link>
          {onMissingLake && (
            <p className="map-missing">
              <button type="button" className="link-btn" onClick={onMissingLake}>
                {t.missingLake}
              </button>
            </p>
          )}
        </div>
      </div>
    );
  }

  if (loading) return <ContentSkeleton label={t.loading} />;
  if (error && failedId === waterbodyId) return <div className="panel-empty panel-error" role="alert"><p>{error}</p><button type="button" className="btn btn-ghost btn-sm" onClick={() => { setError(null); setAttempt((value) => value + 1); }}>{all.common.tryAgain}</button></div>;
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
  const byOsm = detail.source_url.includes("openstreetmap.org");
  const mappedBy = byOsm ? "OpenStreetMap" : t.cdfwMap;
  const onPublicLand = publicLandSentence(t, detail);
  const confirmedEntrances = detail.access_points.filter((a) => a.public_status === "confirmed_public").length;
  // An unverified lake with no official fish shows the outside records' count.
  const speciesOnRecordOnly = isOsm && detail.species.length === 0;
  const speciesCount = speciesOnRecordOnly ? (detail.reported_species?.length ?? 0) : detail.species.length;
  const tabs = [["access", t.tabAccess], ["fish", t.tabFish], ["sources", t.tabSources]] as const;

  return (
    <div className="panel">
      <h2>
        {detail.name}
        {detail.field_tested && <span className="field-tested-tag">{t.fieldTested}</span>}
        {isClosed && <span className="closed-tag">{t.closedTag}</span>}
        {isOsm && <span className="unverified-tag">{t.unverifiedTag}</span>}
        {isLikelyPrivate && <span className="private-tag">{t.privateTag}</span>}
      </h2>

      {isOsm && (
        // One line to act on; where the data comes from, a tap away.
        <div className="unverified-banner">
          {onPublicLand
            ? <>{onPublicLand} {detail.public_land === "open" ? t.parkHere : t.checkRules}</>
            : <>{t.notChecked}</>}
          <details className="data-note"><summary>{t.aboutData}</summary><p>{t.aboutOsm(mappedBy)} {byOsm ? t.osmIs : t.cdfwMaps} {t.aboutTail}</p></details>
        </div>
      )}

      {isLikelyPrivate && <div className="private-warning">{t.privateWarning}</div>}

      {isOsm && isPond && !isLikelyPrivate && detail.public_land !== "open" && detail.access_points.length === 0 && (
        // Ponds with no reported entrance get their own, louder warning: in
        // Texas many are on ranches, in gated neighborhoods or on golf
        // courses, and unlike a reservoir there's rarely an official access
        // page to check. A pond with an entrance listed gets only the short
        // banner above.
        <div className="pond-warning">{t.pondWarning}</div>
      )}

      {isClosed && (
        // Deliberately shown above everything else and never suppressed:
        // PRD §12 says never present unconfirmed/closed access as public,
        // so a lake TPWD's own source says is closed must say so loudly,
        // not just quietly have an empty access-points list (which also
        // happens to be what "no data yet" looks like — a very different
        // situation this banner exists to avoid conflating).
        <div className="closed-banner">{t.closedBanner}</div>
      )}

      {/* An OSM lake's summary repeats the banner above, so it's skipped. */}
      {/* Counts worth reading; a row of zeros says nothing the banner doesn't. */}
      {(confirmedEntrances > 0 || speciesCount > 0) && (
        <div className="lake-facts">
          {confirmedEntrances > 0 && <span>{t.confirmedEntrances(confirmedEntrances)}</span>}
          {speciesCount > 0 && <span>{t.speciesListed(speciesCount, speciesOnRecordOnly)}</span>}
        </div>
      )}
      {!isClosed && <LakeRulesRow stateCode={detail.state_code} />}
      {!isClosed && <WeatherRecommendations key={`weather-${detail.id}`} waterbodyId={detail.id} latitude={detail.latitude} longitude={detail.longitude} />}
      {CATCHES_AVAILABLE && <LakeCatches key={`catches-${detail.id}`} lakeId={detail.id} />}

      <div className="lake-tabs" role="tablist" aria-label={t.tabs}>
        {tabs.map(([id, label]) => <button key={id} id={`lake-tab-${id}`} role="tab" tabIndex={tab === id ? 0 : -1} aria-selected={tab === id} aria-controls={`lake-panel-${id}`} onClick={() => setTab(id)} onKeyDown={(event) => {
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
      {!isOsm && <p className="access-summary" lang="en">{detail.access_summary}</p>}
      <p className="source-line">
        {t.source}{" "}
        <a href={detail.source_url} target="_blank" rel="noreferrer">
          {new URL(detail.source_url).hostname}
        </a>{" "}
        · {isOsm ? t.imported : t.updated}{" "}
        {new Date(detail.source_updated_at).toLocaleDateString(tag, { month: "short", day: "numeric", year: "numeric" })}
      </p>
      {detail.official_name && <p className="source-line">{t.officialName(detail.official_name)}</p>}
      {byOsm && <p className="data-credit">{t.osmCredit}</p>}

      {detail.agency_profile && <AgencyProfileCard profile={detail.agency_profile} credit={detail.data_credit ?? null} />}
      {!detail.agency_profile && detail.data_credit && <p className="data-credit" lang="en">{detail.data_credit}</p>}
      {(detail.sources?.length ?? 0) > 0 && (
        <>
          <h3>{t.dataSources}</h3>
          <ul className="dataset-sources" lang="en">
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
      <h3>{isOsm ? t.entrancesOsm : allConfirmed ? t.entrancesConfirmed : t.entrances}</h3>
      <AccessPointList
        // Keyed by lake, so "show all" doesn't carry over to the next lake.
        // The prefix matters: a sibling below is keyed by the lake too, and
        // two siblings may not share a key.
        key={`access-${detail.id}`}
        points={detail.access_points}
        emptyText={isOsm ? t.noEntrancesOsm : t.noEntrances}
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
          <h3>{isOsm ? t.fishOfficial : t.species}</h3>
          <ul className="species-list">
            {detail.species.map((s) => (
              <li key={s.common_name}>
                <div className="species-row">
                  <strong>
                    <FishName slug={fishSlug(s.common_name)} english={s.common_name} />
                  </strong>
                  <ConfidenceBadge confidence={s.confidence} />
                </div>
                <SpeciesEvidence species={s} />
                <SpeciesHowTo commonName={s.common_name} />
              </li>
            ))}
            {detail.species.length === 0 && <li className="muted">{t.noSpecies}</li>}
          </ul>
        </>
      )}
      <ReportedSpeciesList reported={detail.reported_species ?? []} isOsm={isOsm} />
      </section>

      {/* Corrections go to a person, who checks a source (ADR 0039). */}
      <p className="lake-report-line">
        {onShareHere && !isClosed && (
          <button type="button" className="link-btn" onClick={() => onShareHere(detail)}>
            {t.shareHere}
          </button>
        )}
        {reported === detail.id ? (
          <span role="status">{t.reportThanks}</span>
        ) : (
          <button type="button" className="link-btn" onClick={() => setReporting(true)}>
            {t.somethingWrong}
          </button>
        )}
      </p>
      <LakeReportDialog
        key={`report-${detail.id}`}
        target={{ kind: "problem", lakeId: detail.id, lakeName: detail.name }}
        open={reporting}
        onClose={() => setReporting(false)}
        onSent={() => setReported(detail.id)}
      />
    </div>
  );
}
