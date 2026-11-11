import type { Metadata } from "next";
import Link from "next/link";

import { PageTransition } from "@/components/motion/Transition";
import { LOCALE_TAGS } from "@/i18n/config";
import { localStateName } from "@/i18n/names";
import { getLocale, getT } from "@/i18n/server";
import { listJurisdictions } from "@/lib/api/client";
import type { Jurisdiction } from "@/lib/api/types";
import { stateSlug } from "@/lib/stateSlug";

// The state list comes from the API, which a build can't reach (see /fish).
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = (await getT()).rulesPage;
  return { title: `${t.indexTitle} · FishEye`, description: t.indexLede };
}

/** Every state, each linking to its own rules page (app/rules/[state]). */
export default async function RulesIndexPage() {
  const t = (await getT()).rulesPage;
  const locale = await getLocale();
  const states: Jurisdiction[] = await listJurisdictions().catch(() => []);
  const name = (j: Jurisdiction) => localStateName(j.code, j.name, locale);
  // The language's own order (zh-TW sorts by strokes, as Taiwan does).
  const sorted = [...states].sort((a, b) => name(a).localeCompare(name(b), LOCALE_TAGS[locale]));
  return (
    <PageTransition>
      <main className="page-scroll rules-page">
        <header className="page-intro">
          <p className="eyebrow">FishEye</p>
          <h1>{t.indexTitle}</h1>
          <p className="lede">{t.indexLede}</p>
        </header>
        {sorted.length === 0 ? (
          <div className="backend-error">{t.loadError}</div>
        ) : (
          <ul className="rules-states">
            {sorted.map((j) => (
              <li key={j.code}>
                <Link href={`/rules/${stateSlug(j.name)}`}>{name(j)}</Link>
                {j.covered && <span className="rules-written">{t.written}</span>}
              </li>
            ))}
          </ul>
        )}
      </main>
    </PageTransition>
  );
}
