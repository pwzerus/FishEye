import type { ReportedSpecies } from "@/lib/api/types";
import { SpeciesHowTo } from "@/components/species/SpeciesHowTo";

function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

function ReportedItem({ s }: { s: ReportedSpecies }) {
  return (
    <li>
      <div className="species-row">
        <strong>{s.common_name}</strong>
        <span className="reported-badge">on record</span>
      </div>
      <p className="evidence">
        {plural(s.records, "record")}
        {s.last_year !== null ? ` · last recorded ${s.last_year}` : " · undated"}
      </p>
      <p className="evidence">{s.sources.map((src) => `${src.name} ${src.records}`).join(" · ")}</p>
      {s.weak && (
        <p className="weak-evidence">
          Weak evidence: a single{" "}
          {s.last_year !== null ? `record from ${s.last_year}` : "undated record"}.
        </p>
      )}
      {s.latest_record_url && (
        <a className="record-link" href={s.latest_record_url} target="_blank" rel="noreferrer">
          See the latest record on GBIF
        </a>
      )}
      <SpeciesHowTo commonName={s.common_name} />
    </li>
  );
}

/**
 * Fish that museums, wildlife surveys and iNaturalist users have recorded at
 * a lake (GBIF). Kept visually and verbally apart from the official species
 * list: a record says a fish was found here, at some point, by someone.
 *
 * On an unverified lake this is all FishMate knows about its fish. On a
 * verified lake it only lists species the official survey doesn't mention.
 */
export function ReportedSpeciesList({
  reported,
  isOsm,
}: {
  reported: ReportedSpecies[];
  isOsm: boolean;
}) {
  const items = isOsm ? reported : reported.filter((s) => !s.also_confirmed);
  if (!isOsm && items.length === 0) return null;

  return (
    <section className="reported-species" aria-label="Fish on record">
      <h3>{isOsm ? "Fish on record (not verified)" : "Also on record (not in the official survey)"}</h3>
      {items.length > 0 ? (
        <>
          <p className="reported-intro">
            Recorded here by museum collections, wildlife surveys and iNaturalist users, via{" "}
            <a href="https://www.gbif.org" target="_blank" rel="noreferrer">
              GBIF
            </a>
            . A record means someone found the fish here, not that an official survey confirms
            it. Records near a lake can include its shoreline and the creeks that flow into it.
          </p>
          <ul className="species-list">
            {items.map((s) => (
              <ReportedItem key={s.common_name} s={s} />
            ))}
          </ul>
        </>
      ) : (
        <p className="muted">
          No fish records for this lake yet, and no official survey. FishMate never guesses
          which fish live somewhere.
        </p>
      )}
    </section>
  );
}
