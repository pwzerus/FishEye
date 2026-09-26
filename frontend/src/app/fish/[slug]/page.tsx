import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AskChat } from "@/components/ask/AskChat";
import { FishArt } from "@/components/fish/FishArt";
import { Tag } from "@/components/fish/FishGrid";
import { HeroPhoto } from "@/components/fish/PhotoCard";
import { SectionTabs, type SectionLink } from "@/components/fish/SectionTabs";
import { PageTransition, VT } from "@/components/motion/Transition";
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
    return { title: `${g.common_name} · FishMate`, description: g.summary };
  } catch {
    return { title: "Fish guide · FishMate" };
  }
}

function Sources({ sources }: { sources: GuideSource[] }) {
  return (
    <p className="source-note">
      Source:{" "}
      {sources.map((s, i) => (
        <span key={s.url}>
          {i > 0 && " · "}
          <a href={s.url} target="_blank" rel="noreferrer">
            {s.label}
          </a>
          {s.kind === "guide" && <span className="muted"> (fishing guide site)</span>}
        </span>
      ))}
    </p>
  );
}

function SetupCard({ setup, index }: { setup: TackleSetup; index: number }) {
  return (
    <article id={`setup-${index}`} className="setup-card">
      <header>
        <span className="setup-num">{index}</span>
        <div>
          <h3>{setup.name}</h3>
          <p className="muted">{setup.use_when}</p>
        </div>
      </header>
      <dl className="setup-specs">
        <div>
          <dt>Rod</dt>
          <dd>{setup.rod}</dd>
        </div>
        <div>
          <dt>Reel</dt>
          <dd>{setup.reel}</dd>
        </div>
        <div>
          <dt>Line</dt>
          <dd>{setup.line}</dd>
        </div>
        <div className="wide">
          <dt>Hook &amp; rig</dt>
          <dd>{setup.terminal}</dd>
        </div>
      </dl>
      <Sources sources={setup.sources} />
    </article>
  );
}

function ListBlock({ id, title, items }: { id: string; title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <section id={id} className="guide-block">
      <h2>{title}</h2>
      <ul className="nice-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function sectionLinks(g: SpeciesGuide): SectionLink[] {
  const links: SectionLink[] = [{ id: "overview", label: "Overview" }];
  if (g.identification.length) links.push({ id: "identification", label: "Identify" });
  if (g.where_and_when.length) links.push({ id: "where_and_when", label: "Where & when" });
  if (g.live_baits.length || g.lures.length) links.push({ id: "bait", label: "Bait & lures" });
  if (g.how_to_get.length) links.push({ id: "how_to_get", label: "Get it" });
  if (g.bait_for.length) links.push({ id: "bait_for", label: "Bait for" });
  if (g.setups.length) links.push({ id: "setups", label: "Rod & reel" });
  if (g.tips.length) links.push({ id: "tips", label: "Tips" });
  links.push({ id: "ask", label: "Ask" });
  return links;
}

const SUGGESTIONS: Record<string, string[]> = {
  forage: ["How do I get it for bait?", "What is it good bait for?", "How do I recognise it?"],
  sport: ["What bait should I use?", "Where do I find it?", "What's the easiest setup?"],
};

export default async function FishPage(props: PageProps<"/fish/[slug]">) {
  const { slug } = await props.params;
  let guide: SpeciesGuide;
  try {
    guide = await getSpeciesGuide(slug);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    return (
      <main className="page-scroll">
        <div className="backend-error">Could not reach the backend API. Is it running? See backend/README.md.</div>
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

  return (
    <PageTransition>
      <main className="page-scroll fish-detail">
        <Link href="/fish" className="back-link" transitionTypes={["nav-back"]}>
          <span aria-hidden="true">←</span> All fish
        </Link>

        <section id="overview" className="fish-hero" style={{ "--wa": wa, "--wb": wb } as React.CSSProperties}>
          <div className="fish-hero-art">
            <VT name={`fish-art-${guide.slug}`} share="morph" default="none">
              <div className="morph-box">
                <FishArt slug={guide.slug} uid={`hero-${guide.slug}`} className="swimming" title={`Illustration of a ${guide.common_name}`} />
              </div>
            </VT>
            <HeroPhoto photo={photo} name={guide.common_name} />
          </div>
          <div className="fish-hero-copy">
            <div className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
              <Tag guide={guide} />
            </div>
            <h1 className="reveal" style={{ "--i": 2 } as React.CSSProperties}>
              {guide.common_name}
            </h1>
            <p className="sci reveal" style={{ "--i": 3 } as React.CSSProperties}>
              {guide.scientific_name}
            </p>
            <p className="lede reveal" style={{ "--i": 4 } as React.CSSProperties}>
              {guide.summary}
            </p>
            <div id="diet" className="fact reveal" style={{ "--i": 5 } as React.CSSProperties}>
              <span className="fact-label">What it eats</span>
              <span>{guide.diet}</span>
            </div>
          </div>
        </section>


        <SectionTabs links={sectionLinks(guide)} />

        <div className="guide-columns">
          <div className="guide-main">
            <ListBlock id="identification" title="How to recognise it" items={guide.identification} />
            <ListBlock id="where_and_when" title="Where and when" items={guide.where_and_when} />

            {(guide.live_baits.length > 0 || guide.lures.length > 0) && (
              <section id="bait" className="guide-block">
                <h2>Bait and lures</h2>
                <div className="bait-grid">
                  {guide.live_baits.length > 0 && (
                    <div id="live_baits" className="bait-card">
                      <h3>Live and natural bait</h3>
                      <ul className="nice-list">
                        {guide.live_baits.map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {guide.lures.length > 0 && (
                    <div id="lures" className="bait-card">
                      <h3>Lures</h3>
                      <ul className="nice-list">
                        {guide.lures.map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            )}

            <ListBlock id="how_to_get" title="How to get it for bait" items={guide.how_to_get} />
            <ListBlock id="bait_for" title="Use it as bait for" items={guide.bait_for} />

            {guide.setups.length > 0 && (
              <section id="setups" className="guide-block">
                <h2>Rod and reel setups</h2>
                <div className="setup-list">
                  {guide.setups.map((s, i) => (
                    <SetupCard key={s.name} setup={s} index={i + 1} />
                  ))}
                </div>
              </section>
            )}

            <ListBlock id="tips" title="Tips" items={guide.tips} />

            {isForage && guide.legal_notes.length > 0 && (
              <section id="bait_rules" className="guide-block rules-card">
                <h2>Bait rules</h2>
                <ul className="nice-list">
                  {guide.legal_notes.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              </section>
            )}

            <p className="limits-note">
              Size and bag limits vary by species and lake.{" "}
              <a href={guide.limits_url} target="_blank" rel="noreferrer">
                Check TPWD&apos;s current limits
              </a>{" "}
              before you keep a fish.
            </p>

            <section id="sources" className="guide-block">
              <h2>Sources</h2>
              <ul className="source-list">
                {guide.sources.map((s) => (
                  <li key={s.url}>
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.label}
                    </a>
                    {s.kind === "guide" && <span className="muted"> (fishing guide site)</span>}
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
              suggestions={SUGGESTIONS[isForage ? "forage" : "sport"]}
            />
          </aside>
        </div>

        <nav className="prev-next" aria-label="More fish">
          {prev ? (
            <Link href={`/fish/${prev.slug}`} className="pn-card" transitionTypes={["nav-back"]}>
              <span className="pn-dir">← Previous</span>
              <span className="pn-name">{prev.common_name}</span>
            </Link>
          ) : (
            <span />
          )}
          {next && (
            <Link href={`/fish/${next.slug}`} className="pn-card pn-next" transitionTypes={["nav-forward"]}>
              <span className="pn-dir">Next →</span>
              <span className="pn-name">{next.common_name}</span>
            </Link>
          )}
        </nav>
      </main>
    </PageTransition>
  );
}
