import type { Metadata } from "next";
import { Suspense } from "react";

import { MapView } from "@/components/map/MapView";
import { PageTransition } from "@/components/motion/Transition";
import { listWaterbodies } from "@/lib/api/client";

export const metadata: Metadata = {
  title: "Map · FishMate",
  description: "Lakes and ponds near you, with confirmed public access, species and sources.",
};

export default async function MapPage() {
  let waterbodies: Awaited<ReturnType<typeof listWaterbodies>> = [];
  let backendError: string | null = null;

  try {
    // Only the verified lakes up front: the map then loads whatever is in
    // view, including the statewide OpenStreetMap layer, as it moves (see
    // MapView.tsx). Server-rendering thousands of OSM lakes into the first
    // page load would be slow and mostly off-screen.
    waterbodies = await listWaterbodies({ stateCode: "TX", tier: "verified" });
  } catch {
    // Backend not reachable (not running yet, wrong URL, etc): degrade to a
    // clear message instead of a Next.js error page.
    backendError = "Could not reach the backend API. Is it running? See backend/README.md.";
  }

  return (
    <PageTransition>
      <main className="page-map">
        {backendError ? (
          <div className="backend-error">{backendError}</div>
        ) : (
          // MapView reads ?lake=, ?at= and ?addPin= deep links.
          <Suspense fallback={<div className="map-skeleton"><div className="skeleton-shimmer" /></div>}>
            <MapView waterbodies={waterbodies} />
          </Suspense>
        )}
      </main>
    </PageTransition>
  );
}
