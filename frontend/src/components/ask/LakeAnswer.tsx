"use client";

import Link from "next/link";

import { useLocale, useT } from "@/i18n/client";
import { localFishName, localStateName } from "@/i18n/names";
import type { AskLake, AskLakes } from "@/lib/api/types";
import { useJurisdictions } from "@/lib/jurisdiction";

/** What the lake data says to a question (backend services/rag/lake_facts.py):
 * a lake it named, or lakes to go to. "No record" is never "not there", and
 * the evidence behind each fish is on the lake's page. */
export function LakeAnswer({ lakes }: { lakes: AskLakes }) {
  const t = useT().lakeAnswer;
  const locale = useLocale();
  const states = useJurisdictions();
  const stateName = (code: string) => localStateName(code, states?.find((j) => j.code === code)?.name ?? code, locale);

  if (lakes.kind === "lake") {
    const lake = lakes.lakes[0];
    if (!lake) return null;
    return (
      <div className="lake-answer">
        <LakeCard lake={lake} stateName={stateName} />
        {lakes.same_name.length > 0 && (
          <p className="muted small">
            {t.sameName}{" "}
            {lakes.same_name.map((o, i) => (
              <span key={o.id}>
                {i > 0 && ", "}
                <Link href={`/map?lake=${o.id}`} className="text-link">
                  {o.name}
                </Link>{" "}
                ({[o.county, o.state_code].filter(Boolean).join(", ")})
              </span>
            ))}
          </p>
        )}
      </div>
    );
  }

  const where = lakes.place ? t.near(lakes.place) : lakes.state ? t.inState(stateName(lakes.state)) : "";
  const fish = lakes.fish_slugs
    .map((slug, i) => localFishName(slug, locale) ?? lakes.fish[i])
    .filter(Boolean)
    .join(t.or);
  if (lakes.lakes.length === 0) {
    return <p className="lake-answer muted small">{t.listNone(fish, where)}</p>;
  }
  return (
    <div className="lake-answer">
      <p className="lake-answer-title">{fish ? t.listTitle(fish, where) : t.listTitleNoFish(where)}</p>
      <ul className="lake-answer-list">
        {lakes.lakes.map((lake) => (
          <li key={lake.id}>
            <Link href={`/map?lake=${lake.id}`} className="text-link">
              {lake.name}
            </Link>{" "}
            <span className="muted small">
              {[lake.county, stateName(lake.state_code)].filter(Boolean).join(", ")}
              {lake.access_points > 0 && ` · ${t.accessPoints(lake.access_points)}`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function LakeCard({ lake, stateName }: { lake: AskLake; stateName: (code: string) => string }) {
  const t = useT().lakeAnswer;
  const locale = useLocale();
  return (
    <>
      <p className="lake-answer-title">
        <Link href={`/map?lake=${lake.id}`} className="text-link">
          {lake.name}
        </Link>{" "}
        <span className="muted small">{[lake.county, stateName(lake.state_code)].filter(Boolean).join(", ")}</span>
      </p>
      {lake.public_access_status === "closed" && <p className="small">{t.closed}</p>}
      {lake.public_access_status === "likely_private" && <p className="small">{t.likelyPrivate}</p>}
      {lake.asked.map((a) => (
        <p key={a.slug} className="lake-answer-asked">
          {t.asked(localFishName(a.slug, locale) ?? a.name, a.status)}
        </p>
      ))}
      {lake.species.length > 0 ? (
        <>
          <p className="bait-tip-label">{t.onRecord}</p>
          <p className="lake-answer-fish">
            {lake.species.map((f) =>
              f.slug ? (
                <Link key={f.name} href={`/fish/${f.slug}`} className="chip chip-sm">
                  {localFishName(f.slug, locale) ?? f.name}
                </Link>
              ) : (
                <span key={f.name} className="chip chip-sm" lang="en">
                  {f.name}
                </span>
              ),
            )}
          </p>
        </>
      ) : (
        <p className="muted small">{t.noFish}</p>
      )}
      {lake.reported.length > 0 && (
        <p className="muted small">
          {t.reported} <span lang="en">{lake.reported.join(", ")}</span>
        </p>
      )}
      <p className="muted small">
        {[
          lake.access_points > 0 ? t.accessPoints(lake.access_points) : null,
          lake.fish_attractors > 0 ? t.attractors(lake.fish_attractors) : null,
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <p className="lake-answer-links">
        <Link href={`/map?lake=${lake.id}`}>{t.openLake}</Link>
        {lake.agency_url && (
          <a href={lake.agency_url} target="_blank" rel="noopener noreferrer">
            {t.agencyPage}
          </a>
        )}
      </p>
      {lake.credit && (
        <p className="muted small" lang="en">
          {lake.credit}
        </p>
      )}
    </>
  );
}
