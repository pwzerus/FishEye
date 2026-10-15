import type { AgencyProfile, AgencyRatingLevel } from "@/lib/api/types";

const AGENCY_NAMES: Record<string, string> = {
  tpwd: "Texas Parks & Wildlife",
};

const LEVELS: AgencyRatingLevel[] = ["Poor", "Fair", "Good", "Excellent"];

/**
 * What the state fisheries agency says about this lake, in its own words:
 * its fishing ratings, the species it lists, the lake's size, and links to
 * the agency's lake page, latest survey report and access page. Nothing
 * here is FishEye's opinion, so it is labelled with the agency's name.
 */
export function AgencyProfileCard({ profile }: { profile: AgencyProfile }) {
  const agency = AGENCY_NAMES[profile.agency] ?? profile.agency.toUpperCase();
  const facts = [
    profile.surface_acres ? `${profile.surface_acres.toLocaleString("en-US")} acres` : null,
    profile.max_depth_ft ? `up to ${profile.max_depth_ft} ft deep` : null,
    profile.impounded ? `impounded ${profile.impounded}` : null,
  ].filter(Boolean);

  return (
    <section className="agency-profile" aria-label={`${agency} on this lake`}>
      <h3>What {agency} says</h3>
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
          <span className="agency-subhead">Predominant fish: </span>
          {profile.predominant_species.join("; ")}
        </p>
      )}

      {profile.placement === "ramps" && (
        <p className="agency-note">
          Shown on the map at {agency}&apos;s boat ramps: this lake has no outline on
          OpenStreetMap, so its marker is near the shore, not the middle.
        </p>
      )}

      <p className="source-line agency-links">
        <a href={profile.page_url} target="_blank" rel="noreferrer">
          Lake page
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
              Access, fees and parks
            </a>
          </>
        )}
      </p>
    </section>
  );
}
