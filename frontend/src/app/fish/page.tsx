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
    backendError = "We couldn't load the guides. Please refresh to try again.";
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
            Pick a fish for bait and gear. Open the handbook for knots, casting and the basics.
          </p>
          <div className="guide-shortcuts"><a href="#fish-species">Fish species ↓</a><a href="#handbook">Fishing basics ↓</a></div>
          <StatePicker />
        </section>

        {backendError ? (
          <div className="backend-error">{backendError}</div>
        ) : (
          <div id="fish-species"><FishGrid guides={guides} photos={photos} /></div>
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
