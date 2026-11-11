import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";

import { PageTransition } from "@/components/motion/Transition";
import { RulesStatePicker } from "@/components/rules/RulesStatePicker";
import { localStateName, localTopicTitle } from "@/i18n/names";
import { getLocale, getT } from "@/i18n/server";
import { listHandbook, listJurisdictions } from "@/lib/api/client";
import type { GuideSource, HandbookTopic, Jurisdiction } from "@/lib/api/types";
import { stateSlug } from "@/lib/stateSlug";

// From the API at request time, like /fish: a build has no API to ask.
export const dynamic = "force-dynamic";

async function find(
  slug: string,
  locale: string,
): Promise<{ state: Jurisdiction | null; alias: Jurisdiction | null; topics: HandbookTopic[]; failed: boolean }> {
  try {
    const [states, handbook] = await Promise.all([listJurisdictions(locale), listHandbook(locale).catch(() => [])]);
    const state = states.find((j) => stateSlug(j.name) === slug) ?? null;
    // "/rules/tx": a state's code is what people type; it leads to the page.
    const alias = state ? null : (states.find((j) => j.code.toLowerCase() === slug.toLowerCase()) ?? null);
    return { state, alias, topics: state ? handbook.filter((h) => h.region === state.code) : [], failed: false };
  } catch {
    return { state: null, alias: null, topics: [], failed: true };
  }
}

export async function generateMetadata({ params }: PageProps<"/rules/[state]">): Promise<Metadata> {
  const t = (await getT()).rulesPage;
  const locale = await getLocale();
  const { state } = await find((await params).state, locale);
  if (!state) return { title: `${t.indexTitle} · FishEye` };
  const name = localStateName(state.code, state.name, locale);
  return { title: `${t.title(name)} · FishEye`, description: t.lede(name) };
}

function Sources({ sources }: { sources: GuideSource[] }) {
  if (sources.length === 0) return null;
  return (
    <p className="muted small">
      {sources.map((s, i) => (
        <span key={s.url}>
          {i > 0 && " · "}
          <a href={s.url} target="_blank" rel="noreferrer" lang="en">
            {s.label}
          </a>
        </span>
      ))}
    </p>
  );
}

/**
 * One state's fishing rules in one place: who needs a license, where the
 * official limits are, what may go on the hook, and the state's own
 * handbook topics. FishEye never states a limit (they change and vary by
 * lake): it links the agency's page, which is the rule.
 */
export default async function StateRulesPage({ params }: PageProps<"/rules/[state]">) {
  const all = await getT();
  const t = all.rulesPage;
  const locale = await getLocale();
  const { state, alias, topics, failed } = await find((await params).state, locale);
  if (failed) {
    return (
      <main className="page-scroll rules-page">
        <div className="backend-error">{t.loadError}</div>
      </main>
    );
  }
  if (!state && alias) permanentRedirect(`/rules/${stateSlug(alias.name)}`);
  if (!state) notFound();
  const name = localStateName(state.code, state.name, locale);
  const agency = state.agency ?? t.agencyFallback(name);
  const license = topics.find((h) => h.id === state.license_topic) ?? null;
  const others = topics.filter((h) => h.id !== state.license_topic);

  return (
    <PageTransition>
      <main className="page-scroll rules-page">
        <header className="page-intro">
          <p className="eyebrow">
            <Link href="/rules">{t.indexTitle}</Link>
          </p>
          <h1>{t.title(name)}</h1>
          <p className="lede">{t.lede(name)}</p>
          <RulesStatePicker code={state.code} />
        </header>

        <section className="rules-card">
          <h2>{t.licenseHeading}</h2>
          {license ? (
            <>
              {license.body.map((line) => (
                <p key={line} lang={license.body_lang ?? "en"}>
                  {line}
                </p>
              ))}
              <Sources sources={license.sources} />
            </>
          ) : (
            <p>{t.licenseFromAgency(agency)}</p>
          )}
          {state.license_url && (
            <p>
              <a className="btn btn-primary btn-sm" href={state.license_url} target="_blank" rel="noreferrer">
                {t.buyLicense(state.agency_short ?? agency)}
              </a>
            </p>
          )}
        </section>

        <section className="rules-card">
          <h2>{t.limitsHeading}</h2>
          <p>{t.limitsText}</p>
          {state.limits_url ? (
            <p>
              <a href={state.limits_url} target="_blank" rel="noreferrer">
                {t.limitsLink(state.agency_short ?? agency)}
              </a>
            </p>
          ) : (
            <p className="muted">{t.limitsAsk(agency)}</p>
          )}
        </section>

        {state.bait_rules.length > 0 && (
          <section className="rules-card">
            <h2>{t.baitHeading}</h2>
            <ul lang={state.bait_rules_lang ?? "en"}>
              {state.bait_rules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
            <Sources sources={state.bait_rules_sources} />
          </section>
        )}

        {others.length > 0 && (
          <section className="rules-card">
            <h2>{t.moreHeading(name)}</h2>
            {others.map((h) => (
              <details key={h.id} className="rules-topic">
                <summary>{localTopicTitle(h.id, locale) ?? h.title}</summary>
                {h.body.map((line) => (
                  <p key={line} lang={h.body_lang ?? "en"}>
                    {line}
                  </p>
                ))}
                <Sources sources={h.sources} />
              </details>
            ))}
          </section>
        )}

        {!state.covered && <p className="muted">{t.notWritten(name)}</p>}

        <section className="rules-card rules-next">
          <h2>{t.nextHeading}</h2>
          <ul>
            {state.first_trip_topic && (
              <li>
                <Link href={`/handbook#${state.first_trip_topic}`}>{t.firstTrip(name)}</Link>
              </li>
            )}
            <li>
              <Link href="/start">{t.startHere}</Link>
            </li>
            <li>
              <Link href="/fish">{t.learnFish}</Link>
            </li>
            <li>
              <Link href="/map">{t.findWater(name)}</Link>
            </li>
          </ul>
        </section>
        <p className="muted small">{t.disclaimer}</p>
      </main>
    </PageTransition>
  );
}
