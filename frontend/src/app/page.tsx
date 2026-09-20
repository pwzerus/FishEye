import { MapView } from "@/components/map/MapView";
import { listWaterbodies } from "@/lib/api/client";

export default async function Home() {
  let waterbodies: Awaited<ReturnType<typeof listWaterbodies>> = [];
  let backendError: string | null = null;

  try {
    waterbodies = await listWaterbodies({ stateCode: "TX" });
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
      <header className="page-header">
        <h1>FishPilot AI</h1>
        <p>Pick a lake to see confirmed public access, species, and sources.</p>
      </header>

      {backendError ? (
        <div className="backend-error">{backendError}</div>
      ) : (
        <MapView waterbodies={waterbodies} />
      )}
    </main>
  );
}
