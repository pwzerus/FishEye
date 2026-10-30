import Link from "next/link";
import { ActionIcon } from "@/components/ui/ActionIcon";
import { FishArt } from "@/components/fish/FishArt";
import { LegalLinks } from "@/components/legal/LegalPage";
import { PageTransition } from "@/components/motion/Transition";
import { listJurisdictions, listSpeciesGuides, listWaterbodies, getWaterbody } from "@/lib/api/client";
import type { SpeciesGuide, WaterbodyDetail } from "@/lib/api/types";
import { waterFor } from "@/lib/fishArt";
import { FishNameParts } from "@/components/fish/FishName";
import { getLocale } from "@/i18n/server";
import { MESSAGES } from "@/i18n/messages";
import { localFishName, localStateName } from "@/i18n/names";

export const dynamic = "force-dynamic";

const FEEDBACK_EMAIL = "feedback.fisheyefishing@gmail.com";

function WaterIllustration() {
  return <svg className="field-map" viewBox="0 0 640 510" fill="none" aria-hidden="true">
    <defs>
      <pattern id="map-grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" stroke="#c7d6bd" strokeWidth=".6" /></pattern>
      <linearGradient id="lake-fill" x1="180" y1="100" x2="430" y2="460" gradientUnits="userSpaceOnUse"><stop stopColor="#a5cfce"/><stop offset="1" stopColor="#6baeb1"/></linearGradient>
    </defs>
    <path fill="#e7ecdf" d="M0 0h640v510H0z"/><path fill="url(#map-grid)" d="M0 0h640v510H0z"/>
    <g stroke="#c5d4bb" strokeWidth="1.2">
      <path d="M-30 170C110 0 305 8 411 61S600 120 680 15"/><path d="M-30 186C110 16 305 24 411 77S600 136 680 31"/><path d="M-30 202C110 32 305 40 411 93S600 152 680 47"/>
      <path d="M-50 435C50 311 114 351 170 448S400 590 590 410S714 326 720 410"/><path d="M-50 451C50 327 114 367 170 464S400 606 590 426S714 342 720 426"/>
      <path d="M-50 467C50 343 114 383 170 480S400 622 590 442S714 358 720 442"/>
    </g>
    <path d="M30 -20C146 108 76 200 178 261S449 199 493 308S580 438 665 430" stroke="#fffdf4" strokeWidth="13"/>
    <path d="M30 -20C146 108 76 200 178 261S449 199 493 308S580 438 665 430" stroke="#d4cbb4" strokeWidth="1.5" strokeDasharray="6 5"/>
    <path d="M309 71C350 61 360 107 348 145C337 178 397 143 415 167C437 197 391 226 409 251C433 282 469 255 484 284C501 322 445 340 422 326C401 314 395 358 369 382C339 406 287 390 287 359C288 328 333 312 312 286C290 261 232 309 216 280C194 245 247 224 250 203C253 179 191 181 195 149C199 117 252 142 267 119C280 100 285 76 309 71Z" fill="url(#lake-fill)" stroke="#5c9d9d" strokeWidth="2"/>
    <path d="M294 147C281 192 303 212 334 235S376 277 353 334" stroke="#b8d9d5" strokeWidth="1.5" strokeDasharray="4 6"/>
    <g fill="#c3d1b9"><circle cx="110" cy="329" r="24"/><circle cx="134" cy="347" r="18"/><circle cx="505" cy="125" r="28"/><circle cx="535" cy="143" r="19"/></g>
    <g transform="translate(292 217)"><circle r="29" fill="#165d50" fillOpacity=".12"/><circle r="19" fill="#165d50"/><path d="M-10 0C-4-8 4-8 9-3l7-4V7L9 3C4 8-4 8-10 0Z" fill="white"/></g>
    <g transform="translate(417 279)"><circle r="12" fill="white"/><circle r="6" fill="#165d50"/></g>
    <g transform="translate(248 183)"><circle r="12" fill="white"/><circle r="6" fill="#165d50"/></g>
    <text x="570" y="57" fill="#42634d" fontSize="13" fontFamily="sans-serif">N</text><path d="m575 68-6 17 6-4 6 4-6-17Z" fill="#42634d"/>
  </svg>;
}

/** The lake on the front page: a different one each day, moving between the
 * states FishEye has official lake data for, so the page isn't always the
 * same Texas reservoir (the first verified lake by name, before). Only
 * lakes with confirmed public access. */
async function featuredLake(): Promise<{ lake: WaterbodyDetail; stateName: string; stateCode: string } | null> {
  const states = (await listJurisdictions()).filter((j) => j.covered);
  const day = Math.floor(Date.now() / 86_400_000);
  for (let i = 0; i < states.length; i++) {
    const state = states[(day + i) % states.length];
    const open = (await listWaterbodies({ stateCode: state.code, tier: "verified", limit: 60 })).filter(
      (item) => item.public_access_status === "open",
    );
    // A lake or reservoir makes a better first look than a pond.
    const bigger = open.filter((item) => item.water_type !== "pond" && !/\bpond\b/i.test(item.name));
    const pick = bigger.length ? bigger : open;
    if (pick.length) return { lake: await getWaterbody(pick[day % pick.length].id), stateName: state.name, stateCode: state.code };
  }
  return null;
}

export default async function FieldHome() {
  const locale = await getLocale();
  const t = MESSAGES[locale].home;
  let guides: SpeciesGuide[] = [];
  let featured: { lake: WaterbodyDetail; stateName: string; stateCode: string } | null = null;
  const results = await Promise.allSettled([listSpeciesGuides(), featuredLake()]);
  if (results[0].status === "fulfilled") guides = results[0].value;
  if (results[1].status === "fulfilled") featured = results[1].value;
  const lake = featured?.lake ?? null;
  const starters = guides.filter((g) => g.difficulty === "beginner").slice(0, 4);

  return <PageTransition><main className="home field-home home-refined">
    <section className="field-hero">
      <div className="field-hero-copy">
        <p className="field-kicker"><span /> {t.kicker}</p>
        <h1>{t.title1}<br/><em>{t.title2}</em></h1>
        <p className="field-lede">{t.lede}</p>
        <div className="hero-actions"><Link href="/map" className="btn btn-primary"><ActionIcon name="pin"/> {t.findWater} <ActionIcon name="arrow"/></Link><Link href="/start" className="field-secondary">{t.firstTime}</Link></div>
        <p className="field-assurance">{t.assurance}</p>
      </div>
      <div className="field-product">
        <div className="field-product-top"><ActionIcon name="map"/> {t.nextDay}</div>
        <div className="field-map-wrap"><WaterIllustration /><span className="field-map-note">{t.illustration}</span>
          <Link href={lake ? `/map?lake=${lake.id}` : "/map"} className="field-lake-card"><span className="field-lake-icon"><ActionIcon name="fish"/></span><span><span className="field-small-label">{t.exploreLake}</span><strong>{lake?.name ?? t.placeToStart}</strong><span className="field-lake-meta">{lake && featured ? t.lakeMeta(localStateName(featured.stateCode, featured.stateName, locale), lake.access_points.filter((a) => a.public_status === "confirmed_public").length, lake.species.length) : t.lakeMetaNone}</span></span><span className="field-card-arrow"><ActionIcon name="arrow"/></span></Link>
        </div>
      </div>
    </section>
    <section className="home-actions" aria-label={t.actions}>
      {([
        { icon: "map", title: t.actionMap, text: t.actionMapText, href: "/map" },
        { icon: "fish", title: t.actionFish, text: t.actionFishText, href: "/fish" },
        { icon: "ask", title: t.actionAsk, text: t.actionAskText, href: "/ask" },
      ] as const).map((action) => <Link key={action.href} href={action.href} className="home-action"><span className="home-action-icon"><ActionIcon name={action.icon}/></span><span><h2>{action.title}</h2><p>{action.text}</p></span><ActionIcon name="arrow"/></Link>)}
    </section>
    {starters.length > 0 && <section className="field-starters"><div className="field-section-heading"><h2>{t.firstFish}</h2><Link href="/fish" className="field-secondary">{t.allFish}</Link></div><div className="field-fish-row">{starters.map((g) => <Link key={g.slug} href={`/fish/${g.slug}`} className="field-fish"><div style={{ background: `linear-gradient(140deg, ${waterFor(g.slug)[0]}, ${waterFor(g.slug)[1]})` }}><FishArt slug={g.slug} uid={`field-${g.slug}`} /></div><h3><FishNameParts local={localFishName(g.slug, locale)} english={g.common_name} /> <span aria-hidden="true">↗</span></h3><span className="field-small-label">{t.beginner}</span></Link>)}</div></section>}
    <section className="home-feedback" aria-labelledby="home-feedback-title">
      <div>
        <h2 id="home-feedback-title">{t.feedbackTitle}</h2>
        <p>{t.feedbackText}</p>
      </div>
      <a className="btn btn-primary" href={`mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent(t.feedbackSubject)}`}>{t.feedbackSend}</a>
    </section>
    <footer className="field-footer"><span>{t.footer}</span><LegalLinks /><details className="home-sources"><summary>{t.sourcesTitle}</summary><p>{t.sources}</p></details></footer>
  </main></PageTransition>;
}
