import type { Metadata } from "next";
import { Suspense } from "react";

import { MapView } from "@/components/map/MapView";
import { PageTransition } from "@/components/motion/Transition";
import { listWaterbodies } from "@/lib/api/client";

// Render on each request, not once during `next build`. A build made
// without the API running (a Docker image, CI) would otherwise bake in the
// "could not reach the backend" fallback, and the first visitor after every
// deploy would get it. The API calls themselves still cache for 30 seconds
// (lib/api/client.ts), so this costs the backend almost nothing.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Map · FishEye",
  description: "Lakes and ponds near you, with confirmed public access, species and sources.",
};

export default async function MapPage() {
  let backendError: string | null = null;

  try {
    // Just a reachability check — not real data. Showing a state-wide list
    // of "verified" lakes before the person has said where they are (via
    // geolocation, search, or panning the map themselves) doesn't mean
    // anything to them; it's a handful of specific reservoirs, not "what's
    // near you". MapView starts empty and loads whatever's actually in
    // view once there is a view to speak of (see its ViewportWatcher).
    await listWaterbodies({ stateCode: "TX", tier: "verified", limit: 1 });
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
            <MapView waterbodies={[]} />
          </Suspense>
        )}
      </main>
    </PageTransition>
  );
}
