"use client";

import dynamic from "next/dynamic";
import { useRef, useState } from "react";

import { ApiError, listWaterbodies } from "@/lib/api/client";
import type { WaterbodyListItem } from "@/lib/api/types";
import { WaterbodyPanel } from "@/components/waterbody/WaterbodyPanel";
import type { Viewport } from "./LakeMap";
import { LocationSearchBar, type LocatedPoint } from "./LocationSearchBar";
import { MapLegend } from "./MapLegend";

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

// Below this zoom only verified lakes are loaded. A statewide view holds
// thousands of OpenStreetMap lakes; loading a capped, arbitrary subset of
// them would look like the full picture when it isn't, so the map asks the
// user to zoom in instead.
export const MIN_ZOOM_FOR_ALL_LAKES = 8;
// Per-request cap. A dense metro view (with ponds included) can exceed it;
// the backend returns verified lakes first, and the map says the view is
// partial rather than silently dropping the rest.
const VIEWPORT_LIMIT = 2000;

export function MapView({ waterbodies: initialWaterbodies }: { waterbodies: WaterbodyListItem[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [waterbodies, setWaterbodies] = useState(initialWaterbodies);
  const [focusPoint, setFocusPoint] = useState<LocatedPoint | null>(null);
  const [zoom, setZoom] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [truncated, setTruncated] = useState(false);
  // Where the overview map was last looking, so "← All lakes" returns there
  // instead of resetting to the whole of Texas.
  const [lastView, setLastView] = useState<{ center: [number, number]; zoom: number } | null>(
    null,
  );
  // Pans can overlap: only the newest request's answer is shown.
  const latestRequest = useRef(0);

  function handleViewportChange({ bbox, zoom: newZoom, center }: Viewport) {
    const requestId = ++latestRequest.current;
    setZoom(newZoom);
    setLastView({ center, zoom: newZoom });
    setLoading(true);
    listWaterbodies({
      bbox,
      tier: newZoom < MIN_ZOOM_FOR_ALL_LAKES ? "verified" : undefined,
      limit: VIEWPORT_LIMIT,
    })
      .then((lakes) => {
        if (requestId !== latestRequest.current) return;
        setWaterbodies(lakes);
        setTruncated(lakes.length >= VIEWPORT_LIMIT);
      })
      .catch((e: unknown) => {
        // Keep what's on screen rather than blanking the map over a
        // transient error.
        console.error("viewport lake query failed:", e instanceof ApiError ? e.message : e);
      })
      .finally(() => {
        if (requestId === latestRequest.current) setLoading(false);
      });
  }

  function handleLocate(point: LocatedPoint) {
    setSelectedId(null);
    // Flying there fires moveend, which loads that area's lakes through
    // handleViewportChange like any other pan.
    setFocusPoint(point);
  }

  const zoomedOut = zoom !== null && zoom < MIN_ZOOM_FOR_ALL_LAKES;
  const showEmpty = focusPoint !== null && !loading && !zoomedOut && waterbodies.length === 0;

  return (
    <div className="map-view">
      <div className="map-container">
        {selectedId === null ? (
          <>
            <LocationSearchBar onLocate={handleLocate} />
            <div className="map-status-stack">
              {loading && <div className="map-status-chip">Loading lakes…</div>}
              {!loading && !zoomedOut && truncated && (
                <div className="map-status-chip">
                  Showing the first {VIEWPORT_LIMIT} lakes and ponds here. Zoom in to see the rest.
                </div>
              )}
              {!loading && zoomedOut && (
                <div className="map-status-chip">
                  Showing verified lakes only. Zoom in to see every mapped lake.
                </div>
              )}
              {showEmpty && (
                // Honest, not apologetic: the statewide layer covers Texas
                // only for now (docs/adr/0010-statewide-osm-layer.md).
                <div className="no-nearby-lakes-banner">
                  No lakes on file near {focusPoint.label} yet. FishMate covers Texas for now.
                </div>
              )}
            </div>
            <LakeMap
              waterbodies={waterbodies}
              onSelect={setSelectedId}
              onViewportChange={handleViewportChange}
              focusPoint={focusPoint}
              initialView={lastView}
            />
            <MapLegend />
          </>
        ) : (
          <>
            {/* Drill-down, not an overlay: clicking a lake replaces the
                statewide map with that lake's own zoomed-in view — this
                button is the only way back. */}
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
