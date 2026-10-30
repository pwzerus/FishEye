"use client";

import type { ReportedSpecies } from "@/lib/api/types";
import { FishName } from "@/components/fish/FishName";
import { SpeciesHowTo } from "@/components/species/SpeciesHowTo";
import { useT } from "@/i18n/client";
import { fishSlug } from "@/i18n/names";

function ReportedItem({ s }: { s: ReportedSpecies }) {
  const t = useT().lake;
  return (
    <li>
      <div className="species-row">
        <strong>
          <FishName slug={fishSlug(s.common_name)} english={s.common_name} />
        </strong>
        <span className="reported-badge">{t.onRecord}</span>
      </div>
      <p className="evidence">
        {t.records(s.records)}
        {s.last_year !== null ? t.lastRecorded(s.last_year) : t.undated}
      </p>
      <p className="evidence">{s.sources.map((src) => `${src.name} ${src.records}`).join(" · ")}</p>
      {s.weak && (
        <p className="weak-evidence">
          {t.weakEvidence(s.last_year !== null ? t.recordFrom(s.last_year) : t.undatedRecord)}
        </p>
      )}
      {s.latest_record_url && (
        <a className="record-link" href={s.latest_record_url} target="_blank" rel="noreferrer">
          {t.latestOnGbif}
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
 * On an unverified lake this is all FishEye knows about its fish. On a
 * verified lake it only lists species the official survey doesn't mention.
 */
export function ReportedSpeciesList({
  reported,
  isOsm,
}: {
  reported: ReportedSpecies[];
  isOsm: boolean;
}) {
  const t = useT().lake;
  const items = isOsm ? reported : reported.filter((s) => !s.also_confirmed);
  if (!isOsm && items.length === 0) return null;

  return (
    <section className="reported-species" aria-label={t.fishOnRecord}>
      <h3>{isOsm ? t.onRecordOsm : t.onRecordAlso}</h3>
      {items.length > 0 ? (
        <>
          <p className="reported-intro">
            {t.recordsIntro}{" "}
            <a href="https://www.gbif.org" target="_blank" rel="noreferrer">
              GBIF ↗
            </a>
          </p>
          <ul className="species-list">
            {items.map((s) => (
              <ReportedItem key={s.common_name} s={s} />
            ))}
          </ul>
        </>
      ) : (
        <p className="muted">{t.noRecords}</p>
      )}
    </section>
  );
}
