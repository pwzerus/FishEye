import type { Metadata } from "next";

import { getLocale, getT } from "@/i18n/server";
import { MESSAGES } from "@/i18n/messages";
import { localFishName } from "@/i18n/names";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AskChat } from "@/components/ask/AskChat";
import { FishArt } from "@/components/fish/FishArt";
import { Tag } from "@/components/fish/FishGrid";
import { FishNameParts } from "@/components/fish/FishName";
import { GuideSummary } from "@/components/fish/GuideSummary";
import { HeroPhoto } from "@/components/fish/PhotoCard";
import { SectionTabs, type SectionLink } from "@/components/fish/SectionTabs";
import { PageTransition, VT } from "@/components/motion/Transition";
import { BaitRules, LimitsNote, LiveBaitWarning } from "@/components/rules/RegionGate";
import { DietTypeTag } from "@/components/species/SpeciesGuideBody";
import { groupSetups } from "@/components/species/setups";
import type { Messages } from "@/i18n/messages";
import { ApiError, getSpeciesGuide, listSpeciesGuides, listSpeciesPhotos } from "@/lib/api/client";
import { waterFor } from "@/lib/fishArt";
import type { GuideSource, SpeciesGuide, TackleSetup } from "@/lib/api/types";

/**
 * Pre-render every fish page. Besides being faster, it's what makes the
 * thumbnail-to-hero morph play: a prefetched page renders in the same
 * commit as the navigation, while a page that suspends into its loading
 * skeleton first has no element to morph into (see the Next.js view
 * transitions guide). If the backend is down at build time the list is
 * empty and pages simply render on demand.
 */
export async function generateStaticParams() {
  try {
    return (await listSpeciesGuides()).map((g) => ({ slug: g.slug }));
  } catch {
    return [];
  }
}

export async function generateMetadata(props: PageProps<"/fish/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  try {
    const g = await getSpeciesGuide(slug);
    // Not the guide's summary: several open with a Texas fact ("Texas's most
    // sought-after freshwater fish"), which reads wrong in search results
    // everywhere else. The summary stays on the page, where it is in context.
    const locale = await getLocale();
    const name = localFishName(g.slug, locale) ?? g.common_name;
    return {
      title: `${name} · FishEye`,
      description: MESSAGES[locale].pages.fishGuideDescription(name, g.scientific_name),
    };
  } catch {
    return { title: `${(await getT()).pages.fish} · FishEye` };
  }
}

function Sources({ sources, t }: { sources: GuideSource[]; t: Messages["fish"] }) {
  return (
    <p className="source-note">
      {t.source}{" "}
      {sources.map((s, i) => (
        <span key={s.url}>
          {i > 0 && " · "}
          <a href={s.url} target="_blank" rel="noreferrer">
            {s.label}
          </a>
          {s.kind === "guide" && <span className="muted">{t.guideSite}</span>}
        </span>
      ))}
    </p>
  );
}

function SetupCard({ setup, index, t }: { setup: TackleSetup; index: number; t: Messages["fish"] }) {
  return (
    <article id={`setup-${index}`} className="setup-card">
      <header>
        <span className="setup-num">{index}</span>
        <div lang="en">
          <h3>{setup.name}</h3>
          <p className="muted">{setup.use_when}</p>
        </div>
      </header>
      <dl className="setup-specs">
        <div>
          <dt>{t.rod}</dt>
          <dd lang="en">{setup.rod}</dd>
        </div>
        <div>
          <dt>{t.reel}</dt>
          <dd lang="en">{setup.reel}</dd>
        </div>
        <div>
          <dt>{t.line}</dt>
          <dd lang="en">{setup.line}</dd>
        </div>
        <div className="wide">
          <dt>{t.hookRig}</dt>
          <dd lang="en">{setup.terminal}</dd>
        </div>
      </dl>
      <Sources sources={setup.sources} t={t} />
    </article>
  );
}

function ListBlock({ id, title, items }: { id: string; title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <section id={id} className="guide-block">
      <h2>{title}</h2>
      <ul className="nice-list" lang="en">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function sectionLinks(g: SpeciesGuide, t: Messages["fish"]): SectionLink[] {
  const links: SectionLink[] = [{ id: "overview", label: t.tabOverview }];
  if (g.identification.length) links.push({ id: "identification", label: t.tabIdentify });
  if (g.habitat.length || g.habits.length) links.push({ id: "habitat", label: t.tabHabitat });
  if (g.where_and_when.length) links.push({ id: "where_and_when", label: t.tabWhere });
  if (g.live_baits.length || g.lures.length) links.push({ id: "bait", label: t.tabBait });
  if (g.how_to_get.length) links.push({ id: "how_to_get", label: t.tabGet });
  if (g.bait_for.length) links.push({ id: "bait_for", label: t.tabBaitFor });
  if (g.setups.length) links.push({ id: "setups", label: t.tabSetups });
  if (g.tips.length) links.push({ id: "tips", label: t.tabTips });
  if (g.eating.length) links.push({ id: "eating", label: t.tabEating });
  links.push({ id: "ask", label: t.tabAsk });
  return links;
}

export default async function FishPage(props: PageProps<"/fish/[slug]">) {
  const { slug } = await props.params;
  const locale = await getLocale();
  const t = MESSAGES[locale].fish;
  let guide: SpeciesGuide;
  try {
    guide = await getSpeciesGuide(slug);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    return (
      <main className="page-scroll">
        <div className="backend-error">{t.backendDown}</div>
      </main>
    );
  }
  const [all, photos] = await Promise.all([listSpeciesGuides().catch(() => [guide]), listSpeciesPhotos()]);
  const idx = all.findIndex((g) => g.slug === guide.slug);
  const prev = idx > 0 ? all[idx - 1] : null;
  const next = idx >= 0 && idx < all.length - 1 ? all[idx + 1] : null;
  const [wa, wb] = waterFor(guide.slug);
  const photo = photos[guide.slug] ?? null;
  const isForage = guide.role === "forage";
  const name = (g: SpeciesGuide) => localFishName(g.slug, locale) ?? g.common_name;

  return (
    <PageTransition>
      <main className="page-scroll fish-detail">
        <Link href="/fish" className="back-link" transitionTypes={["nav-back"]}>
          <span aria-hidden="true">←</span> {t.allFish}
        </Link>

        <section id="overview" className="fish-hero" style={{ "--wa": wa, "--wb": wb } as React.CSSProperties}>
          <div className="fish-hero-art">
            <VT name={`fish-art-${guide.slug}`} share="morph" default="none">
              <div className="morph-box">
                <FishArt slug={guide.slug} uid={`hero-${guide.slug}`} className="swimming" title={t.illustration(name(guide))} />
              </div>
            </VT>
            <HeroPhoto photo={photo} name={name(guide)} />
          </div>
          <div className="fish-hero-copy">
            <div className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
              <Tag guide={guide} />
            </div>
            <h1 className="reveal" style={{ "--i": 2 } as React.CSSProperties}>
              <FishNameParts local={localFishName(guide.slug, locale)} english={guide.common_name} />
            </h1>
            <p className="sci reveal" style={{ "--i": 3 } as React.CSSProperties}>
              {guide.scientific_name}
            </p>
            <p className="lede reveal" lang="en" style={{ "--i": 4 } as React.CSSProperties}>
              <GuideSummary guide={guide} />
            </p>
            <div id="diet" className="fact reveal" style={{ "--i": 5 } as React.CSSProperties}>
              <span className="fact-label">
                {t.whatItEats} <DietTypeTag guide={guide} />
              </span>
              <span lang="en">{guide.diet}</span>
            </div>
          </div>
        </section>


        <SectionTabs links={sectionLinks(guide, t)} />
        {locale !== "en" && <p className="hint guide-english-note">{t.englishContent}</p>}

        <div className="guide-columns">
          <div className="guide-main">
            <ListBlock id="identification" title={t.recognise} items={guide.identification} />
            <ListBlock id="habitat" title={t.habitat} items={guide.habitat} />
            <ListBlock id="habits" title={t.habits} items={guide.habits} />
            <ListBlock id="where_and_when" title={t.whereWhen} items={guide.where_and_when} />

            {(guide.live_baits.length > 0 || guide.lures.length > 0) && (
              <section id="bait" className="guide-block">
                <h2>{t.baitLures}</h2>
                <div className="bait-grid">
                  {guide.live_baits.length > 0 && (
                    <div id="live_baits" className="bait-card">
                      <h3>{t.liveBait}</h3>
                      <LiveBaitWarning />
                      <ul className="nice-list" lang="en">
                        {guide.live_baits.map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {guide.lures.length > 0 && (
                    <div id="lures" className="bait-card">
                      <h3>{t.lures}</h3>
                      <ul className="nice-list" lang="en">
                        {guide.lures.map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            )}

            <ListBlock id="why_these_baits" title={t.whyBaits} items={guide.why_these_baits} />
            <ListBlock id="how_to_get" title={t.howToGet} items={guide.how_to_get} />
            <ListBlock id="bait_for" title={t.baitFor} items={guide.bait_for} />

            {guide.setups.length > 0 &&
              (() => {
                const { lure, bait } = groupSetups(guide.setups);
                return (
                  <section id="setups" className="guide-block">
                    <h2>{t.setups}</h2>
                    <p className="muted">{t.setupsNote}</p>
                    {lure.length > 0 && (
                      <div className="setup-group">
                        <h3>{t.lureFishing}</h3>
                        <div className="setup-list">
                          {lure.map((s, i) => (
                            <SetupCard key={s.name} setup={s} index={i + 1} t={t} />
                          ))}
                        </div>
                      </div>
                    )}
                    {bait.length > 0 && (
                      <div className="setup-group">
                        <h3>{t.baitFishing}</h3>
                        <div className="setup-list">
                          {bait.map((s, i) => (
                            <SetupCard key={s.name} setup={s} index={i + 1} t={t} />
                          ))}
                        </div>
                      </div>
                    )}
                  </section>
                );
              })()}

            <ListBlock id="tips" title={t.tips} items={guide.tips} />
            <ListBlock id="eating" title={t.eating} items={guide.eating} />
            {guide.eating.length > 0 && (
              <p className="muted">
                {t.cleaningIn}<Link href="/fish#care">{t.handbookLink}</Link>{t.cleaningEnd}
              </p>
            )}

            {isForage && guide.legal_notes.length > 0 && (
              <BaitRules texasRules={guide.legal_notes} texasUrl={guide.limits_url} className="guide-block rules-card" />
            )}

            {!(isForage && guide.legal_notes.length > 0) && (
              <LimitsNote className="limits-note" texasUrl={guide.limits_url} />
            )}

            <section id="sources" className="guide-block">
              <h2>{t.sources}</h2>
              <ul className="source-list">
                {guide.sources.map((s) => (
                  <li key={s.url}>
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.label}
                    </a>
                    {s.kind === "guide" && <span className="muted">{t.guideSite}</span>}
                  </li>
                ))}
              </ul>
            </section>
          </div>

          <aside id="ask" className="guide-aside">
            <AskChat
              compact
              speciesSlug={guide.slug}
              speciesName={guide.common_name}
              suggestions={isForage ? t.suggestForage : t.suggestSport}
            />
          </aside>
        </div>

        <nav className="prev-next" aria-label={t.moreFish}>
          {prev ? (
            <Link href={`/fish/${prev.slug}`} className="pn-card" transitionTypes={["nav-back"]}>
              <span className="pn-dir">{t.previous}</span>
              <span className="pn-name">{name(prev)}</span>
            </Link>
          ) : (
            <span />
          )}
          {next && (
            <Link href={`/fish/${next.slug}`} className="pn-card pn-next" transitionTypes={["nav-forward"]}>
              <span className="pn-dir">{t.next}</span>
              <span className="pn-name">{name(next)}</span>
            </Link>
          )}
        </nav>
      </main>
    </PageTransition>
  );
}
