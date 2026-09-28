import type { Metadata } from "next";

import { FishGrid } from "@/components/fish/FishGrid";
import { PageTransition } from "@/components/motion/Transition";
import { listSpeciesGuides, listSpeciesPhotos } from "@/lib/api/client";
import type { SpeciesGuide, SpeciesPhotos } from "@/lib/api/types";

export const metadata: Metadata = {
  title: "Fish guide · FishEye",
  description: "How to catch Texas freshwater fish: what they eat, where to look, baits and tackle setups.",
};

export default async function FishGuidePage() {
  let guides: SpeciesGuide[] = [];
  let photos: SpeciesPhotos = {};
  let backendError: string | null = null;
  try {
    [guides, photos] = await Promise.all([listSpeciesGuides(), listSpeciesPhotos()]);
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
            Twelve Texas freshwater fish: what each one eats, where to look, which bait works, and
            rod-and-reel setups from a first cane pole up. Every setup names its source, mostly
            Texas Parks and Wildlife and other state agencies.
          </p>
        </section>

        {backendError ? (
          <div className="backend-error">{backendError}</div>
        ) : (
          <FishGrid guides={guides} photos={photos} />
        )}

        {baitRules.length > 0 && (
          <section id="bait_rules" className="rules-card reveal" style={{ "--i": 6 } as React.CSSProperties}>
            <h2>Texas bait rules, for every fish</h2>
            <ul>
              {baitRules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
            <p className="muted">
              Size and bag limits change and vary by lake.{" "}
              <a href={guides[0]?.limits_url} target="_blank" rel="noreferrer">
                Check TPWD&apos;s current limits
              </a>{" "}
              before you keep a fish.
            </p>
          </section>
        )}
      </main>
    </PageTransition>
  );
}
