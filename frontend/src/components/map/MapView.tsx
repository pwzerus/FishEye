"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import type { WaterbodyListItem } from "@/lib/api/types";
import { WaterbodyPanel } from "@/components/waterbody/WaterbodyPanel";

// Leaflet touches `window` at import time, which breaks server-side
// rendering. next/dynamic with ssr:false has to be called from a client
// component (App Router forbids it from a server component directly) —
// this file is that boundary.
const LakeMap = dynamic(() => import("./LakeMap"), {
  ssr: false,
  loading: () => <div className="map-loading">Loading map…</div>,
});
const LakeDetailMap = dynamic(() => import("./LakeDetailMap"), {
  ssr: false,
  loading: () => <div className="map-loading">Loading lake map…</div>,
});

export function MapView({ waterbodies }: { waterbodies: WaterbodyListItem[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);

  return (
    <div className="map-view">
      <div className="map-container">
        {selectedId === null ? (
          <LakeMap waterbodies={waterbodies} onSelect={setSelectedId} />
        ) : (
          <>
            {/* Drill-down, not an overlay: clicking a lake replaces the
                statewide map with that lake's own zoomed-in view (per
                the request that recommendations and, later, the AI
                Advisor and community pins need a map scoped to one lake,
                not the whole state) — this button is the only way back. */}
            <button
              type="button"
              className="back-to-map-button"
              onClick={() => setSelectedId(null)}
            >
              ← All lakes
            </button>
            <LakeDetailMap key={selectedId} waterbodyId={selectedId} />
          </>
        )}
      </div>
      <aside className="side-panel">
        <WaterbodyPanel waterbodyId={selectedId} />
      </aside>
    </div>
  );
}
