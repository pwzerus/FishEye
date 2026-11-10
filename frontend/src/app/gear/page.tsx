import type { Metadata } from "next";
import Link from "next/link";

import { GearPhoto } from "@/components/gear/GearPhoto";
import { IdentifyGear } from "@/components/gear/IdentifyGear";
import { PageTransition } from "@/components/motion/Transition";
import { localFishName, localGearCategory, localGearName } from "@/i18n/names";
import { getLocale, getT } from "@/i18n/server";
import type { Locale } from "@/i18n/config";
import { listGear, listSpeciesGuides } from "@/lib/api/client";
import type { Gear, GearItem, SpeciesGuide } from "@/lib/api/types";

// From the API at request time, like /fish: a build has no API to ask.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = (await getT()).gearPage;
  return { title: `${t.title} · FishEye`, description: t.lede };
}

function Card({ item, locale, fishName, t }: {
  item: GearItem;
  locale: Locale;
  fishName: (slug: string) => string;
  t: Awaited<ReturnType<typeof getT>>["gearPage"];
}) {
  const local = localGearName(item.id, locale);
  return (
    <article id={item.id} className="gear-card">
      {item.photo ? <GearPhoto photo={item.photo} alt={local ?? item.name} /> : <div className="gear-photo gear-no-photo">{t.noPhoto}</div>}
      <div className="gear-card-body">
        <h3>
          {local ?? item.name}
          {local && <span className="name-en" lang="en">{item.name}</span>}
        </h3>
        <p lang="en">{item.what}</p>
        <p className="gear-tip" lang="en"><strong>{t.tip}</strong> {item.tip}</p>
        {item.fish.length > 0 && (
          <p className="gear-fish">
            {t.goodFor}{" "}
            {item.fish.slice(0, 6).map((slug, i) => (
              <span key={slug}>
                {i > 0 && ", "}
                <Link href={`/fish/${slug}`}>{fishName(slug)}</Link>
              </span>
            ))}
            {item.fish.length > 6 && "…"}
          </p>
        )}
        {item.topic && <Link className="gear-more" href={`/fish#${item.topic}`}>{t.learnMore}</Link>}
      </div>
    </article>
  );
}

/**
 * What to buy: every piece of gear the guides mention, with a real photo,
 * what it's for and which fish it suits, and a short first-trip list on top
 * (backend app/knowledge/gear.py). FishEye sells nothing and names no brands.
 */
export default async function GearPage() {
  const all = await getT();
  const t = all.gearPage;
  const locale = await getLocale();
  let gear: Gear | null = null;
  let guides: SpeciesGuide[] = [];
  try {
    [gear, guides] = await Promise.all([listGear(), listSpeciesGuides().catch(() => [])]);
  } catch (e) {
    console.error("gear page", e);
    gear = null;
  }
  const english = new Map(guides.map((g) => [g.slug, g.common_name]));
  const fishName = (slug: string) => localFishName(slug, locale) ?? english.get(slug) ?? slug;

  return (
    <PageTransition>
      <main className="page-scroll gear-page">
        <header className="page-intro">
          <p className="eyebrow">FishEye</p>
          <h1>{t.title}</h1>
          <p className="lede">{t.lede}</p>
          {locale !== "en" && <p className="hint">{all.fish.englishContent}</p>}
        </header>
        {!gear ? (
          <div className="backend-error">{t.loadError}</div>
        ) : (
          <>
            {gear.camera && <IdentifyGear items={gear.items} />}
            <section className="gear-kit" aria-labelledby="gear-kit-title">
              <h2 id="gear-kit-title">{t.kitTitle}</h2>
              <p className="muted">{t.kitLede}</p>
              <ul className="gear-kit-list">
                {gear.items.filter((i) => i.first_kit).map((i) => (
                  <li key={i.id}>
                    <a href={`#${i.id}`}>
                      {i.photo && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={i.photo.url} alt="" width={i.photo.width} height={i.photo.height} loading="lazy" />
                      )}
                      <span>{localGearName(i.id, locale) ?? i.name}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </section>
            <nav className="chip-row gear-nav" aria-label={t.sections}>
              {gear.categories.map((c) => (
                <a key={c.id} className="chip" href={`#gear-${c.id}`}>{localGearCategory(c.id, locale) ?? c.label}</a>
              ))}
            </nav>
            {gear.categories.map((c) => {
              const items = gear.items.filter((i) => i.category === c.id);
              if (items.length === 0) return null;
              return (
                <section key={c.id} id={`gear-${c.id}`} className="gear-section">
                  <h2>{localGearCategory(c.id, locale) ?? c.label}</h2>
                  <div className="gear-grid">
                    {items.map((i) => <Card key={i.id} item={i} locale={locale} fishName={fishName} t={t} />)}
                  </div>
                </section>
              );
            })}
            <p className="muted small">{t.credits}</p>
          </>
        )}
      </main>
    </PageTransition>
  );
}
