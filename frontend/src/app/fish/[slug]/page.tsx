import type { Metadata } from "next";

import { getLocale, getT } from "@/i18n/server";
import { MESSAGES } from "@/i18n/messages";
import { localFishName, localGearName } from "@/i18n/names";
import Link from "next/link";
import { notFound } from "next/navigation";

import { BaitText } from "@/components/baits/BaitTip";

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
import { ApiError, getSpeciesGuide, listGear, listSpeciesGuides, listSpeciesPhotos } from "@/lib/api/client";
import { waterFor } from "@/lib/fishArt";
import type { SpeciesGuide, TackleSetup } from "@/lib/api/types";

// Render on each request, like the other pages: the root layout reads the
// language cookie, so this one can't be pre-rendered either. It used to list
// the guides in generateStaticParams, and a build made without the API running
// (a Docker image, CI) then got an empty list, left the route static, and every
// fish page answered 500 when that cookie was read.
export const dynamic = "force-dynamic";

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

/** `index` is the number shown, counted within its group; `anchor` is the
 * setup's place in the whole guide, which is what Ask's citations link to
 * (`#setup-2` is the guide's second setup, whichever group it is in). */
function SetupCard({ setup, index, anchor, t, lang }: { setup: TackleSetup; index: number; anchor?: string; t: Messages["fish"]; lang: string }) {
  return (
    <article id={anchor} className="setup-card">
      <header>
        <span className="setup-num">{index}</span>
        <div lang={lang}>
          <h3>{setup.name}</h3>
          <p className="muted">{setup.use_when}</p>
        </div>
      </header>
      <dl className="setup-specs">
        <div>
          <dt>{t.rod}</dt>
          <dd lang={lang}>{setup.rod}</dd>
        </div>
        <div>
          <dt>{t.reel}</dt>
          <dd lang={lang}>{setup.reel}</dd>
        </div>
        <div>
          <dt>{t.line}</dt>
          <dd lang={lang}>{setup.line}</dd>
        </div>
        <div className="wide">
          <dt>{t.hookRig}</dt>
          <dd lang={lang}>{setup.terminal}</dd>
        </div>
      </dl>
    </article>
  );
}

/** `baitsFor`: the baits named are tappable (components/baits/BaitTip.tsx). */
function ListBlock({ id, title, items, baitsFor, lang }: { id: string; title: string; items: string[]; baitsFor?: string; lang: string }) {
  if (items.length === 0) return null;
  return (
    <section id={id} className="guide-block">
      <h2>{title}</h2>
      <ul className="nice-list" lang={lang}>
        {items.map((item) => (
          <li key={item}>{baitsFor ? <BaitText text={item} fish={baitsFor} /> : item}</li>
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
    guide = await getSpeciesGuide(slug, locale);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    return (
      <main className="page-scroll">
        <div className="backend-error">{t.backendDown}</div>
      </main>
    );
  }
  const [all, photos, gear] = await Promise.all([
    listSpeciesGuides(locale).catch(() => [guide]),
    listSpeciesPhotos(),
    // First-kit things first: the strip reads as a shopping list.
    listGear()
      .then((g) => g.items.filter((i) => i.fish.includes(slug) && i.photo).sort((a, b) => Number(b.first_kit) - Number(a.first_kit)))
      .catch(() => []),
  ]);
  const idx = all.findIndex((g) => g.slug === guide.slug);
  const prev = idx > 0 ? all[idx - 1] : null;
  const next = idx >= 0 && idx < all.length - 1 ? all[idx + 1] : null;
  const [wa, wb] = waterFor(guide.slug);
  const photo = photos[guide.slug] ?? null;
  const isForage = guide.role === "forage";
  const lang = guide.text_lang ?? "en";
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
            <p className="lede reveal" lang={lang} style={{ "--i": 4 } as React.CSSProperties}>
              <GuideSummary guide={guide} />
            </p>
            <div id="diet" className="fact reveal" style={{ "--i": 5 } as React.CSSProperties}>
              <span className="fact-label">
                {t.whatItEats} <DietTypeTag guide={guide} />
              </span>
              <span lang={lang}>{guide.diet}</span>
            </div>
          </div>
        </section>


        <SectionTabs links={sectionLinks(guide, t)} />
        {locale !== "en" && !guide.text_lang && <p className="hint guide-english-note">{t.englishContent}</p>}

        <div className="guide-columns">
          <div className="guide-main">
            <ListBlock id="identification" title={t.recognise} items={guide.identification} lang={lang} />
            <ListBlock id="habitat" title={t.habitat} items={guide.habitat} lang={lang} />
            <ListBlock id="habits" title={t.habits} items={guide.habits} lang={lang} />
            <ListBlock id="where_and_when" title={t.whereWhen} items={guide.where_and_when} lang={lang} />

            {(guide.live_baits.length > 0 || guide.lures.length > 0) && (
              <section id="bait" className="guide-block">
                <h2>{t.baitLures}</h2>
                <div className="bait-grid">
                  {guide.live_baits.length > 0 && (
                    <div id="live_baits" className="bait-card">
                      <h3>{t.liveBait}</h3>
                      <LiveBaitWarning />
                      <ul className="nice-list" lang={lang}>
                        {guide.live_baits.map((b) => (
                          <li key={b}>
                            <BaitText text={b} fish={slug} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {guide.lures.length > 0 && (
                    <div id="lures" className="bait-card">
                      <h3>{t.lures}</h3>
                      <ul className="nice-list" lang={lang}>
                        {guide.lures.map((b) => (
                          <li key={b}>
                            <BaitText text={b} fish={slug} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            )}

            {gear.length > 0 && (
              <section id="gear" className="guide-block">
                <h2>{t.gearForFish}</h2>
                <div className="handbook-gear fish-gear">
                  {gear.slice(0, 8).map((i) => (
                    <Link key={i.id} href={`/gear#${i.id}`} className="handbook-gear-item">
                      {/* Credit is on /gear, under the full-size photo. */}
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={i.photo!.url} alt="" width={i.photo!.width} height={i.photo!.height} loading="lazy" />
                      <span>{localGearName(i.id, locale) ?? i.name}</span>
                    </Link>
                  ))}
                </div>
                <p className="muted small">
                  <Link href="/gear">{t.gearAll}</Link>
                </p>
              </section>
            )}

            <ListBlock id="why_these_baits" title={t.whyBaits} items={guide.why_these_baits} baitsFor={slug} lang={lang} />
            <ListBlock id="how_to_get" title={t.howToGet} items={guide.how_to_get} lang={lang} />
            <ListBlock id="bait_for" title={t.baitFor} items={guide.bait_for} lang={lang} />

            {guide.setups.length > 0 &&
              (() => {
                const { lure, bait } = groupSetups(guide.setups);
                // A setup for either method is in both groups; only its first
                // card carries the anchor, so no id is used twice.
                const anchored = new Set<TackleSetup>();
                const anchorFor = (s: TackleSetup) => {
                  if (anchored.has(s)) return undefined;
                  anchored.add(s);
                  return `setup-${guide.setups.indexOf(s) + 1}`;
                };
                return (
                  <section id="setups" className="guide-block">
                    <h2>{t.setups}</h2>
                    <p className="muted">{t.setupsNote}</p>
                    {lure.length > 0 && (
                      <div className="setup-group">
                        <h3>{t.lureFishing}</h3>
                        <div className="setup-list">
                          {lure.map((s, i) => (
                            <SetupCard key={s.name} setup={s} index={i + 1} anchor={anchorFor(s)} t={t} lang={lang} />
                          ))}
                        </div>
                      </div>
                    )}
                    {bait.length > 0 && (
                      <div className="setup-group">
                        <h3>{t.baitFishing}</h3>
                        <div className="setup-list">
                          {bait.map((s, i) => (
                            <SetupCard key={s.name} setup={s} index={i + 1} anchor={anchorFor(s)} t={t} lang={lang} />
                          ))}
                        </div>
                      </div>
                    )}
                  </section>
                );
              })()}

            <ListBlock id="tips" title={t.tips} items={guide.tips} lang={lang} />
            <ListBlock id="eating" title={t.eating} items={guide.eating} lang={lang} />
            {guide.eating.length > 0 && (
              <p className="muted">
                {t.cleaningIn}<Link href="/handbook#care">{t.handbookLink}</Link>{t.cleaningEnd}
              </p>
            )}

            {isForage && guide.legal_notes.length > 0 && (
              <BaitRules texasRules={guide.legal_notes} texasUrl={guide.limits_url} className="guide-block rules-card" />
            )}

            {!(isForage && guide.legal_notes.length > 0) && (
              <LimitsNote className="limits-note" texasUrl={guide.limits_url} />
            )}

            <p className="sources-link">
              <Link href={`/sources#fish-${guide.slug}`}>{t.sources}</Link>
            </p>
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
