"use client";

import { useLocaleTag, useT } from "@/i18n/client";
import type { Messages } from "@/i18n/messages";
import type { AgencyProfile, AgencyRatingLevel } from "@/lib/api/types";

const AGENCY_NAMES: Record<string, string> = {
  tpwd: "Texas Parks & Wildlife",
  ga_wrd: "Georgia WRD",
  cdfw: "CDFW",
};

// What the main link opens. TPWD has a page per lake; Georgia WRD has a
// fishing forecast for its larger reservoirs and a statewide map otherwise;
// CDFW, its planting schedule for a stocked lake, its lake record otherwise.
function pageLinkText(profile: AgencyProfile, t: Messages["lake"]): string {
  if (profile.agency === "cdfw") {
    return profile.page_url.includes("FishPlants") ? "CDFW planting schedule" : "CDFW lake record";
  }
  if (profile.agency !== "ga_wrd") return t.lakePage;
  return profile.page_url.includes("storymaps.arcgis.com") ? "WRD fishing forecast" : "WRD fishing map";
}

function accessLinkText(profile: AgencyProfile, t: Messages["lake"]): string {
  if (profile.agency === "ga_wrd") return "WRD fishing map";
  if (profile.agency === "cdfw") return "CDFW fishing guide";
  return t.accessPage;
}

const LEVELS: AgencyRatingLevel[] = ["Poor", "Fair", "Good", "Excellent"];

/**
 * The facts the state fisheries agency publishes about this lake: its
 * fishing ratings, the species it lists, the lake's size, and links to the
 * agency's lake page, latest survey report and access page. Facts only,
 * never the agency's sentences; labelled "Data: <agency>" (data-sourcing
 * rules 3 and 7). Nothing here is FishEye's opinion.
 */
export function AgencyProfileCard({ profile, credit = null }: { profile: AgencyProfile; credit?: string | null }) {
  const t = useT().lake;
  const tag = useLocaleTag();
  const agency = AGENCY_NAMES[profile.agency] ?? profile.agency.toUpperCase();
  const placedAt = profile.placement === "sites" ? t.accessSites : t.boatRamps;
  const facts = [
    profile.surface_acres ? t.acres(profile.surface_acres.toLocaleString(tag)) : null,
    profile.max_depth_ft ? t.deep(profile.max_depth_ft) : null,
    profile.impounded ? t.impounded(profile.impounded) : null,
  ].filter(Boolean);

  return (
    <section className="agency-profile" aria-label={t.onThisLake(agency)}>
      <h3>{t.from(agency)}</h3>
      {profile.location && <p className="agency-location" lang="en">{profile.location}</p>}
      {facts.length > 0 && <p className="agency-facts">{facts.join(" · ")}</p>}

      {profile.ratings.length > 0 && (
        <>
          <p className="agency-subhead">{t.qualityBy(agency)}</p>
          <ul className="agency-ratings">
            {profile.ratings.map((r) => (
              <li key={r.label}>
                <span className="agency-rating-label" lang="en">{r.label}</span>
                <span
                  className={`agency-rating agency-rating-${r.rating.toLowerCase()}`}
                  aria-label={t.ratingOf(t.ratings[r.rating] ?? r.rating, LEVELS.indexOf(r.rating) + 1)}
                >
                  {t.ratings[r.rating] ?? r.rating}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {profile.predominant_species.length > 0 && (
        <p className="agency-species">
          <span className="agency-subhead">
            {profile.agency === "ga_wrd" ? t.wrdLists : t.predominant}
          </span>
          {profile.predominant_species.join("; ")}
        </p>
      )}

      {(profile.placement === "ramps" || profile.placement === "sites") && (
        <p className="agency-note">{t.placedAtRamps(agency, placedAt)}</p>
      )}

      <p className="source-line agency-links">
        <a href={profile.page_url} target="_blank" rel="noreferrer">
          {pageLinkText(profile, t)}
        </a>
        {profile.survey_report_url && (
          <>
            {" · "}
            <a href={profile.survey_report_url} target="_blank" rel="noreferrer">
              {t.surveyReport(profile.survey_year ?? null)}
            </a>
          </>
        )}
        {profile.access_page_url && (
          <>
            {" · "}
            <a href={profile.access_page_url} target="_blank" rel="noreferrer">
              {accessLinkText(profile, t)}
            </a>
          </>
        )}
      </p>
      {credit && <p className="data-credit" lang="en">{credit}</p>}
    </section>
  );
}
