import type { Metadata } from "next";
import Link from "next/link";

import { PageTransition } from "@/components/motion/Transition";
import { RevealFromHash } from "@/components/sources/RevealFromHash";
import { localCategory, localFishName, localStateName, localTopicTitle } from "@/i18n/names";
import { getLocale, getT } from "@/i18n/server";
import type { Messages } from "@/i18n/messages";
import { listHandbook, listJurisdictions, listQuestionSources, listSpeciesGuides, listSpeciesPhotos } from "@/lib/api/client";
import type { GuideSource, HandbookTopic, Jurisdiction, SpeciesGuide, SpeciesPhotos } from "@/lib/api/types";
import { DATA_SOURCES } from "@/lib/dataSources";

// Same reason as /fish: a build without the API running would bake in an empty page.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.sourcesPage.title} · FishEye`, description: t.sourcesPage.lede };
}

function Links({ sources, guideSite }: { sources: GuideSource[]; guideSite: string }) {
  return (
    <>
      {sources.map((s, i) => (
        <span key={s.url}>
          {i > 0 && " · "}
          <a href={s.url} target="_blank" rel="noreferrer" lang="en">
            {s.label}
          </a>
          {s.kind === "guide" && <span className="muted">{guideSite}</span>}
        </span>
      ))}
    </>
  );
}

function Group({ id, title, count, children }: { id: string; title: string; count?: string; children: React.ReactNode }) {
  return (
    <details id={id} className="sources-group" suppressHydrationWarning>
      <summary>
        <h2>{title}</h2>
        {count && <span>{count}</span>}
      </summary>
      <div className="sources-body">{children}</div>
    </details>
  );
}

/** Every page's sources in one place, by what they were used for: the pages
 * themselves carry one link to their part of this page, not a list of their
 * own (docs/adr/0043). All from the APIs those pages read, so a new guide or
 * topic is listed here without touching this file. */
export default async function SourcesPage() {
  const all = await getT();
  const locale = await getLocale();
  const t: Messages["sourcesPage"] = all.sourcesPage;
  const guideSite = all.fish.guideSite;

  const [guides, handbook, states, photos, questionSources]: [
    SpeciesGuide[], HandbookTopic[], Jurisdiction[], SpeciesPhotos, GuideSource[],
  ] = await Promise.all([
    listSpeciesGuides().catch(() => []),
    listHandbook().catch(() => []),
    listJurisdictions().catch(() => []),
    listSpeciesPhotos().catch(() => ({})),
    listQuestionSources().catch(() => []),
  ]);

  const general = handbook.filter((h) => h.region === "all");
  const categories = [...new Map(general.map((h) => [h.category, h.category_label])).entries()];
  const stateRows = states
    .map((j) => ({ j, topics: handbook.filter((h) => h.region === j.code) }))
    .filter(({ j, topics }) => topics.length > 0 || j.bait_rules_sources.length > 0);
  const credited = guides.filter((g) => photos[g.slug]);

  return (
    <PageTransition>
      <main className="page-scroll sources-page">
        <RevealFromHash />
        <header className="page-intro">
          <p className="eyebrow">FishEye</p>
          <h1>{t.title}</h1>
          <p className="lede">{t.lede}</p>
        </header>

        {guides.length === 0 && handbook.length === 0 && <div className="backend-error">{all.fish.loadError}</div>}

        <Group id="fish" title={t.fish} count={t.count(guides.length)}>
          {guides.map((g) => (
            <article key={g.slug} id={`fish-${g.slug}`} className="sources-entry">
              <h3>
                <Link href={`/fish/${g.slug}`}>{localFishName(g.slug, locale) ?? g.common_name}</Link>
              </h3>
              <dl>
                <div>
                  <dt>{t.guideText}</dt>
                  <dd><Links sources={g.sources} guideSite={guideSite} /></dd>
                </div>
                {g.setups.filter((s) => s.sources.length > 0).map((s) => (
                  <div key={s.name}>
                    <dt>{t.setup} <span lang="en">{s.name}</span></dt>
                    <dd><Links sources={s.sources} guideSite={guideSite} /></dd>
                  </div>
                ))}
              </dl>
            </article>
          ))}
        </Group>

        <Group id="handbook" title={t.handbook} count={t.count(general.length)}>
          {categories.map(([id, label]) => (
            <article key={id} id={`handbook-${id}`} className="sources-entry">
              <h3>{localCategory(id, locale) ?? label}</h3>
              <dl>
                {general.filter((h) => h.category === id).map((h) => (
                  <div key={h.id} id={`topic-${h.id}`}>
                    <dt><Link href={`/handbook#${h.id}`}>{localTopicTitle(h.id, locale) ?? h.title}</Link></dt>
                    <dd><Links sources={h.sources} guideSite={guideSite} /></dd>
                  </div>
                ))}
              </dl>
            </article>
          ))}
        </Group>

        <Group id="questions" title={t.questions} count={t.count(questionSources.length)}>
          <p className="muted">{t.questionsLede}</p>
          <p><Links sources={questionSources} guideSite={guideSite} /></p>
        </Group>

        <Group id="rules" title={t.rules} count={t.count(stateRows.length)}>
          <p className="muted">{t.rulesLede}</p>
          {stateRows.map(({ j, topics }) => (
            <article key={j.code} id={`rules-${j.code.toLowerCase()}`} className="sources-entry">
              <h3>{localStateName(j.code, j.name, locale)}</h3>
              <dl>
                {j.bait_rules_sources.length > 0 && (
                  <div>
                    <dt>{t.baitRules}</dt>
                    <dd><Links sources={j.bait_rules_sources} guideSite={guideSite} /></dd>
                  </div>
                )}
                {topics.map((h) => (
                  <div key={h.id}>
                    <dt><Link href={`/handbook#${h.id}`}>{localTopicTitle(h.id, locale) ?? h.title}</Link></dt>
                    <dd><Links sources={h.sources} guideSite={guideSite} /></dd>
                  </div>
                ))}
              </dl>
            </article>
          ))}
        </Group>

        <Group id="data" title={t.data}>
          <p className="muted">{t.dataLede}</p>
          <dl className="sources-entry">
            {DATA_SOURCES.map((d) => (
              <div key={d.id}>
                <dt>{t.dataUse[d.id]}</dt>
                <dd>
                  <a href={d.url} target="_blank" rel="noreferrer" lang="en">{d.label}</a>
                </dd>
              </div>
            ))}
          </dl>
        </Group>

        <Group id="photos" title={t.photos} count={t.count(credited.length)}>
          <p className="muted">{t.photosLede}</p>
          <dl className="sources-entry">
            {credited.map((g) => {
              const photo = photos[g.slug]!;
              return (
                <div key={g.slug}>
                  <dt><Link href={`/fish/${g.slug}`}>{localFishName(g.slug, locale) ?? g.common_name}</Link></dt>
                  <dd lang="en">
                    {photo.author} ·{" "}
                    {photo.license_url ? (
                      <a href={photo.license_url} target="_blank" rel="noreferrer">{photo.license}</a>
                    ) : (
                      photo.license
                    )}{" "}
                    · <a href={photo.file_page} target="_blank" rel="noreferrer">Wikimedia</a>
                  </dd>
                </div>
              );
            })}
          </dl>
        </Group>
      </main>
    </PageTransition>
  );
}
