import type { Metadata } from "next";

import { FishGrid } from "@/components/fish/FishGrid";
import { Handbook } from "@/components/fish/Handbook";
import { PageTransition } from "@/components/motion/Transition";
import { BaitRules } from "@/components/rules/RegionGate";
import { StatePicker } from "@/components/ui/StatePicker";
import { listHandbook, listSpeciesGuides, listSpeciesPhotos } from "@/lib/api/client";
import type { HandbookTopic, SpeciesGuide, SpeciesPhotos } from "@/lib/api/types";

// Render on each request, not once during `next build`. A build made
// without the API running (a Docker image, CI) would otherwise bake in the
// "could not reach the backend" fallback, and the first visitor after every
// deploy would get it. The API calls themselves still cache for 30 seconds
// (lib/api/client.ts), so this costs the backend almost nothing.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Fish guide · FishEye",
  description:
    "How to catch freshwater fish: what they eat, where they live, baits and why they work, tackle, knots, and cleaning your catch.",
};

export default async function FishGuidePage() {
  let guides: SpeciesGuide[] = [];
  let photos: SpeciesPhotos = {};
  let handbook: HandbookTopic[] = [];
  let backendError: string | null = null;
  try {
    [guides, photos, handbook] = await Promise.all([
      listSpeciesGuides(),
      listSpeciesPhotos(),
      listHandbook().catch(() => []),
    ]);
  } catch {
    backendError = "Could not reach the backend API. Is it running? See backend/README.md.";
  }

  const baitRules = guides.find((g) => g.legal_notes.length > 0)?.legal_notes ?? [];

  return (
    <PageTransition>
      <main className="page-scroll fish-index">
        <section className="page-intro">
          <p className="eyebrow reveal" style={{ "--i": 0 } as React.CSSProperties}>
            Fish guide
          </p>
          <h1 className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
            Meet the fish
          </h1>
          <p className="lede reveal" style={{ "--i": 2 } as React.CSSProperties}>
            {guides.length > 0 ? `${guides.length} freshwater fish` : "Freshwater fish"}, most of them
            found across the U.S.: what each one eats, where it lives, which bait works and why, and
            rod-and-reel setups from a first cane pole up, plus a handbook for everything else. Every
            setup names its source, mostly state wildlife agencies. How to catch a fish is the same
            everywhere; the rules are a state&apos;s, and so far FishEye has written Texas&apos;s,
            Georgia&apos;s and California&apos;s.
          </p>
          <StatePicker />
        </section>

        {backendError ? (
          <div className="backend-error">{backendError}</div>
        ) : (
          <FishGrid guides={guides} photos={photos} />
        )}

        {!backendError && <Handbook topics={handbook} />}

        {baitRules.length > 0 && (
          <div className="rules-stack reveal" style={{ "--i": 6 } as React.CSSProperties}>
            <BaitRules texasRules={baitRules} texasUrl={guides[0]?.limits_url ?? ""} suffix=", for every fish" />
          </div>
        )}
      </main>
    </PageTransition>
  );
}
