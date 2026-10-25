import Link from "next/link";
import { ActionIcon } from "@/components/ui/ActionIcon";
import { FishArt } from "@/components/fish/FishArt";
import { PageTransition } from "@/components/motion/Transition";
import { listSpeciesGuides, listWaterbodies, getWaterbody } from "@/lib/api/client";
import type { SpeciesGuide, WaterbodyDetail } from "@/lib/api/types";
import { waterFor } from "@/lib/fishArt";

export const dynamic = "force-dynamic";

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

export default async function FieldHome() {
  let guides: SpeciesGuide[] = [];
  let lake: WaterbodyDetail | null = null;
  const results = await Promise.allSettled([
    listSpeciesGuides(),
    listWaterbodies({ stateCode: "TX", tier: "verified", limit: 5 }).then(async (lakes) => {
      const open = lakes.find((item) => item.public_access_status === "open");
      return open ? getWaterbody(open.id) : null;
    }),
  ]);
  if (results[0].status === "fulfilled") guides = results[0].value;
  if (results[1].status === "fulfilled") lake = results[1].value;
  const starters = guides.filter((g) => g.difficulty === "beginner").slice(0, 4);

  return <PageTransition><main className="home field-home home-refined">
    <section className="field-hero">
      <div className="field-hero-copy">
        <p className="field-kicker"><span /> YOUR FIRST CAST STARTS HERE</p>
        <h1>Find your water.<br/><em>Make a day of it.</em></h1>
        <p className="field-lede">Nearby lakes. The right bait. A simple plan.</p>
        <div className="hero-actions"><Link href="/map" className="btn btn-primary"><ActionIcon name="pin"/> Find nearby water <ActionIcon name="arrow"/></Link><Link href="/fish" className="field-secondary">Choose a fish →</Link></div>
        <p className="field-assurance">Free to explore · No account needed</p>
      </div>
      <div className="field-product">
        <div className="field-product-top"><ActionIcon name="map"/> Your next fishing day</div>
        <div className="field-map-wrap"><WaterIllustration /><span className="field-map-note">Illustration · open the map for real locations</span>
          <Link href={lake ? `/map?lake=${lake.id}` : "/map"} className="field-lake-card"><span className="field-lake-icon"><ActionIcon name="fish"/></span><span><span className="field-small-label">EXPLORE A LAKE</span><strong>{lake?.name ?? "Find a place to start"}</strong><span className="field-lake-meta">{lake ? `${lake.access_points.filter((a) => a.public_status === "confirmed_public").length} public entrances · ${lake.species.length} fish species` : "Lakes & public entrances"}</span></span><span className="field-card-arrow"><ActionIcon name="arrow"/></span></Link>
        </div>
      </div>
    </section>
    <section className="home-actions" aria-label="What would you like to do?">
      {([
        { icon: "map", title: "Find water", text: "Lakes & public entrances", href: "/map" },
        { icon: "fish", title: "Learn a fish", text: "Bait, gear & how to fish", href: "/fish" },
        { icon: "ask", title: "Ask a question", text: "Answers with sources", href: "/ask" },
      ] as const).map((action) => <Link key={action.href} href={action.href} className="home-action"><span className="home-action-icon"><ActionIcon name={action.icon}/></span><span><h2>{action.title}</h2><p>{action.text}</p></span><ActionIcon name="arrow"/></Link>)}
    </section>
    {starters.length > 0 && <section className="field-starters"><div className="field-section-heading"><h2>Good first fish</h2><Link href="/fish" className="field-secondary">All fish →</Link></div><div className="field-fish-row">{starters.map((g) => <Link key={g.slug} href={`/fish/${g.slug}`} className="field-fish"><div style={{ background: `linear-gradient(140deg, ${waterFor(g.slug)[0]}, ${waterFor(g.slug)[1]})` }}><FishArt slug={g.slug} uid={`field-${g.slug}`} /></div><h3>{g.common_name} <span aria-hidden="true">↗</span></h3><span className="field-small-label">BEGINNER FRIENDLY</span></Link>)}</div></section>}
    <footer className="field-footer"><span>FishEye · Get outside.</span><details className="home-sources"><summary>Where our information comes from</summary><p>State wildlife agencies, OpenStreetMap, GBIF and the National Weather Service. Map reports are labelled separately from verified information. Always check local rules.</p></details></footer>
  </main></PageTransition>;
}
