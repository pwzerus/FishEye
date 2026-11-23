import type { Metadata } from "next";

import { getLocale, getT, pageAlternates } from "@/i18n/server";
import Link from "@/components/LocaleLink";

import { FishGrid } from "@/components/fish/FishGrid";
import { HandbookRedirect } from "@/components/fish/HandbookRedirect";
import { PageTransition } from "@/components/motion/Transition";
import { StatePicker } from "@/components/ui/StatePicker";
import { listSpeciesGuides, listSpeciesPhotos } from "@/lib/api/client";
import type { SpeciesGuide, SpeciesPhotos } from "@/lib/api/types";

// Render on each request, not once during `next build`. A build made
// without the API running (a Docker image, CI) would otherwise bake in the
// "could not reach the backend" fallback, and the first visitor after every
// deploy would get it. The API calls themselves still cache for 30 seconds
// (lib/api/client.ts), so this costs the backend almost nothing.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.fish} · FishEye`, description: t.pages.fishDescription, alternates: await pageAlternates("/fish") };
}

function CameraIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
      <circle cx="12" cy="13" r="3.5" />
    </svg>
  );
}

export default async function FishGuidePage() {
  const t = (await getT()).fish;
  let guides: SpeciesGuide[] = [];
  let photos: SpeciesPhotos = {};
  let backendError: string | null = null;
  try {
    [guides, photos] = await Promise.all([listSpeciesGuides(await getLocale()), listSpeciesPhotos()]);
  } catch {
    backendError = t.loadError;
  }

  return (
    <PageTransition>
      <main className="page-scroll fish-index">
        {/* Short on a phone (2026-11-17, the owner: too many words before
            the first fish). No eyebrow: the nav already says where you are;
            no links to the handbook or down to the list, both a tap away. */}
        <section className="page-intro fish-intro">
          <h1 className="reveal" style={{ "--i": 0 } as React.CSSProperties}>
            {t.title}
          </h1>
          <p className="lede reveal" style={{ "--i": 1 } as React.CSSProperties}>
            {t.lede}
          </p>
          <div className="guide-shortcuts reveal" style={{ "--i": 2 } as React.CSSProperties}>
            <Link href="/identify" className="is-main">
              <CameraIcon />
              {t.photoId}
            </Link>
            <Link href="/gear">{t.gearLink}</Link>
            <Link href="/questions">{t.questionsLink}</Link>
          </div>
        </section>

        {backendError ? (
          <div className="backend-error">{backendError}</div>
        ) : (
          <div id="fish-species"><FishGrid guides={guides} photos={photos} tools={<StatePicker />} /></div>
        )}

        <HandbookRedirect />
      </main>
    </PageTransition>
  );
}
