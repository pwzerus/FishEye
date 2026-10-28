import type { AgencyProfile, AgencyRatingLevel } from "@/lib/api/types";

const AGENCY_NAMES: Record<string, string> = {
  tpwd: "Texas Parks & Wildlife",
  ga_wrd: "Georgia WRD",
  cdfw: "CDFW",
};

// What the main link opens. TPWD has a page per lake; Georgia WRD has a
// fishing forecast for its larger reservoirs and a statewide map otherwise;
// CDFW, its planting schedule for a stocked lake, its lake record otherwise.
function pageLinkText(profile: AgencyProfile): string {
  if (profile.agency === "cdfw") {
    return profile.page_url.includes("FishPlants") ? "CDFW planting schedule" : "CDFW lake record";
  }
  if (profile.agency !== "ga_wrd") return "Lake page";
  return profile.page_url.includes("storymaps.arcgis.com") ? "WRD fishing forecast" : "WRD fishing map";
}

function accessLinkText(profile: AgencyProfile): string {
  if (profile.agency === "ga_wrd") return "WRD fishing map";
  if (profile.agency === "cdfw") return "CDFW fishing guide";
  return "Access, fees and parks";
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
  const agency = AGENCY_NAMES[profile.agency] ?? profile.agency.toUpperCase();
  const placedAt = profile.placement === "sites" ? "access sites" : "boat ramps";
  const facts = [
    profile.surface_acres ? `${profile.surface_acres.toLocaleString("en-US")} acres` : null,
    profile.max_depth_ft ? `up to ${profile.max_depth_ft} ft deep` : null,
    profile.impounded ? `impounded ${profile.impounded}` : null,
  ].filter(Boolean);

  return (
    <section className="agency-profile" aria-label={`${agency} on this lake`}>
      <h3>From {agency}</h3>
      {profile.location && <p className="agency-location">{profile.location}</p>}
      {facts.length > 0 && <p className="agency-facts">{facts.join(" · ")}</p>}

      {profile.ratings.length > 0 && (
        <>
          <p className="agency-subhead">Fishing quality, rated by {agency}</p>
          <ul className="agency-ratings">
            {profile.ratings.map((r) => (
              <li key={r.label}>
                <span className="agency-rating-label">{r.label}</span>
                <span
                  className={`agency-rating agency-rating-${r.rating.toLowerCase()}`}
                  aria-label={`${r.rating}, ${LEVELS.indexOf(r.rating) + 1} of 4`}
                >
                  {r.rating}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {profile.predominant_species.length > 0 && (
        <p className="agency-species">
          <span className="agency-subhead">
            {profile.agency === "ga_wrd" ? "Fish WRD lists at its access sites: " : "Predominant fish: "}
          </span>
          {profile.predominant_species.join("; ")}
        </p>
      )}

      {(profile.placement === "ramps" || profile.placement === "sites") && (
        <p className="agency-note">
          Shown on the map at {agency}&apos;s {placedAt}: this lake has no outline on
          OpenStreetMap, so its marker is near the shore, not the middle.
        </p>
      )}

      <p className="source-line agency-links">
        <a href={profile.page_url} target="_blank" rel="noreferrer">
          {pageLinkText(profile)}
        </a>
        {profile.survey_report_url && (
          <>
            {" · "}
            <a href={profile.survey_report_url} target="_blank" rel="noreferrer">
              {profile.survey_year ? `${profile.survey_year} survey report` : "Survey report"}
            </a>
          </>
        )}
        {profile.access_page_url && (
          <>
            {" · "}
            <a href={profile.access_page_url} target="_blank" rel="noreferrer">
              {accessLinkText(profile)}
            </a>
          </>
        )}
      </p>
      {credit && <p className="data-credit">{credit}</p>}
    </section>
  );
}
