import type { Metadata } from "next";
import Link from "@/components/LocaleLink";

import { GearPhoto } from "@/components/gear/GearPhoto";
import { IdentifyGear } from "@/components/gear/IdentifyGear";
import { PageTransition } from "@/components/motion/Transition";
import { LinkedText } from "@/components/terms/TermText";
import { localGearCategory, localGearName } from "@/i18n/names";
import { getLocale, getT, pageAlternates } from "@/i18n/server";
import type { Locale } from "@/i18n/config";
import { listGear } from "@/lib/api/client";
import type { Gear, GearItem } from "@/lib/api/types";
import { sized } from "@/lib/photoSizes";

// From the API at request time, like /fish: a build has no API to ask.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = (await getT()).gearPage;
  return { title: `${t.title} · FishEye`, description: t.lede, alternates: await pageAlternates("/gear") };
}

function Card({ item, locale, t, publicDomain }: {
  item: GearItem;
  locale: Locale;
  t: Awaited<ReturnType<typeof getT>>["gearPage"];
  publicDomain: string;
}) {
  const local = localGearName(item.id, locale);
  // "How to use it" opens the card that shows how (a reel's casting steps,
  // not the card listing the reels); a thing whose card only says what it
  // is gets "more about it" instead (2026-11-25).
  const linked = item.how_to ?? item.topic ?? null;
  return (
    <article id={item.id} className="gear-card">
      {item.photo ? <GearPhoto photo={item.photo} alt={local ?? item.name} publicDomain={publicDomain} /> : <div className="gear-photo gear-no-photo">{t.noPhoto}</div>}
      <div className="gear-card-body">
        <h3>
          {local ?? item.name}
          {local && <span className="name-en" lang="en">{item.name}</span>}
        </h3>
        {/* Terms underlined (components/terms/TermText.tsx), not the topic the card links below. */}
        <p lang={item.text_lang ?? "en"}><LinkedText text={item.what} skipTopic={linked} /></p>
        <p className="gear-tip" lang={item.text_lang ?? "en"}><strong>{t.tip}</strong> <LinkedText text={item.tip} skipTopic={linked} earlier={[item.what]} /></p>
        {linked && <Link className="gear-more" href={`/handbook#${linked}`}>{item.how_to ? t.learnMore : t.moreAbout}</Link>}
      </div>
    </article>
  );
}

/**
 * Gear guide: every piece of gear the guides mention, with a real photo,
 * what it's for, and a short first-trip list on top
 * (backend app/knowledge/gear.py). FishEye sells nothing and names no brands.
 */
export default async function GearPage() {
  const all = await getT();
  const t = all.gearPage;
  const locale = await getLocale();
  let gear: Gear | null = null;
  try {
    gear = await listGear(locale);
  } catch (e) {
    console.error("gear page", e);
    gear = null;
  }

  return (
    <PageTransition>
      <main className="page-scroll gear-page">
        <header className="page-intro">
          <p className="eyebrow">FishEye</p>
          <h1>{t.title}</h1>
          <p className="lede">{t.lede}</p>
          {locale !== "en" && gear?.items.some((i) => !i.text_lang) && <p className="hint">{all.fish.englishContent}</p>}
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
                        <img {...sized(i.photo.url, i.photo.width, "(max-width: 760px) 45vw, 180px")} alt="" width={i.photo.width} height={i.photo.height} loading="lazy" />
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
                    {items.map((i) => <Card key={i.id} item={i} locale={locale} t={t} publicDomain={all.fish.publicDomain} />)}
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
