import type { Metadata } from "next";

import { getLocale, getT } from "@/i18n/server";
import Link from "next/link";

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
  return { title: `${t.pages.fish} · FishEye`, description: t.pages.fishDescription, alternates: { canonical: "/fish" } };
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
        <section className="page-intro">
          <p className="eyebrow reveal" style={{ "--i": 0 } as React.CSSProperties}>
            {t.eyebrow}
          </p>
          <h1 className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
            {t.title}
          </h1>
          <p className="lede reveal" style={{ "--i": 2 } as React.CSSProperties}>
            {t.lede}
          </p>
          <div className="guide-shortcuts"><a href="#fish-species">{t.toSpecies}</a><Link href="/handbook">{t.handbook}</Link><Link href="/gear">{t.gearLink}</Link><Link href="/questions">{t.questionsLink}</Link><Link href="/identify">{t.photoId}</Link></div>
          <StatePicker />
        </section>

        {backendError ? (
          <div className="backend-error">{backendError}</div>
        ) : (
          <div id="fish-species"><FishGrid guides={guides} photos={photos} /></div>
        )}

        <HandbookRedirect />
      </main>
    </PageTransition>
  );
}
