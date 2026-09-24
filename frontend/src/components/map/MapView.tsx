"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { ApiError, listWaterbodies } from "@/lib/api/client";
import type { WaterbodyListItem } from "@/lib/api/types";
import { WaterbodyPanel } from "@/components/waterbody/WaterbodyPanel";
import { LocationSearchBar, type LocatedPoint } from "./LocationSearchBar";

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

// "Nearby" for someone deciding where to drive to fish — wide enough to
// catch a metro area's lakes, narrow enough that a search doesn't return
// something three states over.
const NEARBY_RADIUS_KM = 80;

export function MapView({ waterbodies: initialWaterbodies }: { waterbodies: WaterbodyListItem[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [waterbodies, setWaterbodies] = useState(initialWaterbodies);
  const [focusPoint, setFocusPoint] = useState<LocatedPoint | null>(null);
  const [searchState, setSearchState] = useState<"idle" | "loading" | "empty">("idle");

  function handleLocate(point: LocatedPoint) {
    setSelectedId(null); // a fresh search returns to the statewide-style view
    setFocusPoint(point);
    setSearchState("loading");
    listWaterbodies({ lat: point.latitude, lng: point.longitude, radiusKm: NEARBY_RADIUS_KM })
      .then((nearby) => {
        setWaterbodies(nearby);
        setSearchState(nearby.length === 0 ? "empty" : "idle");
      })
      .catch((e: unknown) => {
        // Keep whatever was already on screen rather than blanking the map
        // over a transient fetch error.
        setSearchState("idle");
        console.error("nearby-waterbody search failed:", e instanceof ApiError ? e.message : e);
      });
  }

  return (
    <div className="map-view">
      <div className="map-container">
        {selectedId === null ? (
          <>
            {/* Only shown on the multi-lake view — searching a new location
                already returns here (handleLocate resets selectedId), so
                there's no case where this needs to coexist with the
                "← All lakes" button below. */}
            <LocationSearchBar onLocate={handleLocate} />
            {searchState === "loading" && (
              <div className="nearby-search-status">Searching nearby lakes…</div>
            )}
            {searchState === "empty" && (
              // Honest, not apologetic: this app only knows about a handful
              // of hand-verified lakes today (see docs/adr/0009-geocoding.md)
              // — saying so plainly beats a map that just looks broken.
              <div className="no-nearby-lakes-banner">
                No fishing spots on file near {focusPoint?.label ?? "this location"} yet. This
                demo currently covers a handful of hand-verified Texas lakes — check back as
                coverage grows.
              </div>
            )}
            <LakeMap waterbodies={waterbodies} onSelect={setSelectedId} focusPoint={focusPoint} />
          </>
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
