import type { Metadata } from "next";

import { SiteHeader } from "@/components/SiteHeader";
import { DifficultyTag, SpeciesGuideBody } from "@/components/species/SpeciesGuideBody";
import { listSpeciesGuides } from "@/lib/api/client";
import type { SpeciesGuide } from "@/lib/api/types";

export const metadata: Metadata = {
  title: "Fish guide · FishMate",
  description: "How to catch Texas freshwater fish: what they eat, where to look, baits and tackle setups.",
};

export default async function FishGuidePage() {
  let guides: SpeciesGuide[] = [];
  let backendError: string | null = null;
  try {
    guides = await listSpeciesGuides();
  } catch {
    backendError = "Could not reach the backend API. Is it running? See backend/README.md.";
  }

  const sport = guides.filter((g) => g.role === "sport");
  const forage = guides.filter((g) => g.role === "forage");

  return (
    <main className="page page-scroll">
      <SiteHeader current="fish" />
      {backendError ? (
        <div className="backend-error">{backendError}</div>
      ) : (
        <div className="fish-guide">
          <section className="fish-guide-intro">
            <h1>How to catch them</h1>
            <p>
              What each fish eats, where to look for it, which bait to use, and a few rod and
              reel setups that work, from a first cane pole to heavier gear. Every setup lists
              the source it came from, mostly Texas Parks and Wildlife and other state
              fisheries agencies.
            </p>
            <nav className="fish-guide-jump" aria-label="Jump to a fish">
              {sport.map((g) => (
                <a key={g.slug} href={`#${g.slug}`}>
                  {g.common_name}
                </a>
              ))}
              {forage.length > 0 && <span className="fish-guide-jump-divider">Bait fish:</span>}
              {forage.map((g) => (
                <a key={g.slug} href={`#${g.slug}`}>
                  {g.common_name}
                </a>
              ))}
            </nav>
          </section>

          {guides.map((g) => (
            <article key={g.slug} id={g.slug} className="fish-guide-card">
              <header className="fish-guide-card-header">
                <div>
                  <h2>{g.common_name}</h2>
                  <p className="fish-guide-sci">{g.scientific_name}</p>
                </div>
                <DifficultyTag guide={g} />
              </header>
              <SpeciesGuideBody guide={g} />
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
