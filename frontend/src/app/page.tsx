import { SiteHeader } from "@/components/SiteHeader";
import { MapView } from "@/components/map/MapView";
import { listWaterbodies } from "@/lib/api/client";

export default async function Home() {
  let waterbodies: Awaited<ReturnType<typeof listWaterbodies>> = [];
  let backendError: string | null = null;

  try {
    // Only the verified lakes up front: the map then loads whatever is in
    // view, including the statewide OpenStreetMap layer, as it moves (see
    // MapView.tsx). Server-rendering thousands of OSM lakes into the first
    // page load would be slow and mostly off-screen.
    waterbodies = await listWaterbodies({ stateCode: "TX", tier: "verified" });
  } catch {
    // Backend not reachable (not running yet, wrong URL, etc). This is a
    // real state the demo has to survive gracefully — day-4 branch adds
    // proper retry/fallback; for now, degrade to a clear message instead
    // of a Next.js error page.
    backendError =
      "Could not reach the backend API. Is it running? See backend/README.md.";
  }

  return (
    <main className="page">
      <SiteHeader
        current="map"
        tagline="Pick a lake to see confirmed public access, species, and sources."
      />

      {backendError ? (
        <div className="backend-error">{backendError}</div>
      ) : (
        <MapView waterbodies={waterbodies} />
      )}
    </main>
  );
}
