"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { PinForm } from "@/components/community/PinForm";
import { useToast } from "@/components/ui/Toast";
import { ApiError, listWaterbodies } from "@/lib/api/client";
import { listPins } from "@/lib/api/session";
import type { PinDetail, PinSummary, WaterbodyListItem } from "@/lib/api/types";
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
const PIN_LIMIT = 300;

type Point = { latitude: number; longitude: number };

function parseAt(raw: string | null): LocatedPoint | null {
  if (!raw) return null;
  const [lat, lng] = raw.split(",").map(Number);
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
  return { latitude: lat, longitude: lng, label: "the pin" };
}

export function MapView({ waterbodies: initialWaterbodies }: { waterbodies: WaterbodyListItem[] }) {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { user, loading: authLoading } = useAuth();

  // Deep links: ?lake=<id> opens a lake, ?at=<lat>,<lng> centres on a
  // point, ?addPin=1 starts placing a pin.
  const lakeParam = Number(params.get("lake"));
  const [selectedId, setSelectedId] = useState<number | null>(
    Number.isInteger(lakeParam) && lakeParam > 0 ? lakeParam : null,
  );
  const [waterbodies, setWaterbodies] = useState(initialWaterbodies);
  const [focusPoint, setFocusPoint] = useState<LocatedPoint | null>(() => parseAt(params.get("at")));
  const [zoom, setZoom] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [truncated, setTruncated] = useState(false);
  // Where the overview map was last looking, so "← All lakes" returns there
  // instead of resetting to the whole of Texas.
  const [lastView, setLastView] = useState<{ center: [number, number]; zoom: number } | null>(null);
  // Pans can overlap: only the newest request's answer is shown.
  const latestRequest = useRef(0);

  const [showPins, setShowPins] = useState(true);
  const [pins, setPins] = useState<PinSummary[]>([]);
  const lastBbox = useRef<string | null>(null);
  const latestPins = useRef(0);
  const [placing, setPlacing] = useState(params.get("addPin") === "1");
  const [draft, setDraft] = useState<Point | null>(null);
  const [created, setCreated] = useState<PinDetail | null>(null);

  const loadPins = useCallback(
    (bbox: string | null) => {
      if (!bbox) return;
      const id = ++latestPins.current;
      listPins({ bbox, limit: PIN_LIMIT })
        .then((p) => id === latestPins.current && setPins(p))
        .catch(() => undefined); // the lake map works without them
    },
    [],
  );

  // Signing in or out changes which pins you may see (your private ones).
  useEffect(() => {
    if (!authLoading && showPins) loadPins(lastBbox.current);
  }, [user, authLoading, showPins, loadPins]);

  // ?addPin=1 without an account: sign in first, then come back to place it.
  useEffect(() => {
    if (placing && !authLoading && !user) {
      router.replace(`/login?next=${encodeURIComponent("/map?addPin=1")}`);
    }
  }, [placing, authLoading, user, router]);

  // First open, no deep link and no lake already selected: ask the browser
  // for the person's location and centre there. Silent on denial/failure —
  // this is a courtesy attempt, not a request the person made, so it falls
  // back to the statewide overview without an error banner. A ?lake= or
  // ?at= link, or picking a lake before this resolves, means the person
  // already told us where they want to look, so it's skipped.
  const triedAutoLocate = useRef(false);
  useEffect(() => {
    if (triedAutoLocate.current) return;
    if (focusPoint !== null || selectedId !== null) {
      triedAutoLocate.current = true;
      return;
    }
    if (typeof navigator === "undefined" || !("geolocation" in navigator)) return;
    triedAutoLocate.current = true;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setFocusPoint({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          label: "your location",
        });
      },
      () => undefined, // denied or unavailable: stay on the statewide view
      { enableHighAccuracy: false, timeout: 10_000 },
    );
    // Runs once, before the person can have interacted with the map.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleViewportChange({ bbox, zoom: newZoom, center }: Viewport) {
    const requestId = ++latestRequest.current;
    setZoom(newZoom);
    setLastView({ center, zoom: newZoom });
    setLoading(true);
    lastBbox.current = bbox;
    if (showPins) loadPins(bbox);
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

  function startPlacing() {
    if (!user) {
      router.push(`/login?next=${encodeURIComponent("/map?addPin=1")}`);
      return;
    }
    setCreated(null);
    setDraft(null);
    setShowPins(true);
    setPlacing(true);
  }

  function stopPlacing() {
    setPlacing(false);
    setDraft(null);
    if (params.get("addPin")) router.replace("/map", { scroll: false });
  }

  function handleCreated(pin: PinDetail) {
    setPins((all) => [pin, ...all.filter((p) => p.id !== pin.id)]);
    setCreated(pin);
    setPlacing(false);
    setDraft(null);
    toast(pin.visibility === "private" ? "Saved to your private pins" : "Pinned! It's live on the map.");
    if (params.get("addPin")) router.replace("/map", { scroll: false });
  }

  const zoomedOut = zoom !== null && zoom < MIN_ZOOM_FOR_ALL_LAKES;
  const showEmpty = focusPoint !== null && !loading && !zoomedOut && waterbodies.length === 0 && !placing;

  let panel: React.ReactNode;
  if (placing && draft) {
    panel = <PinForm key="form" point={draft} onCreated={handleCreated} onCancel={stopPlacing} />;
  } else if (placing) {
    panel = (
      <div className="place-hint reveal">
        <div className="place-hint-icon" aria-hidden="true">
          <span className="catch-marker is-draft">
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path d="M3 12c3-5 9-6 13-3l5-3v12l-5-3c-4 3-10 2-13-3z" fill="currentColor" />
            </svg>
          </span>
        </div>
        <h2>Tap the map where you fished</h2>
        <p className="muted">Zoom in for accuracy. You can drag the pin afterwards to fine-tune it.</p>
        <button type="button" className="btn btn-ghost btn-sm" onClick={stopPlacing}>
          Cancel
        </button>
      </div>
    );
  } else if (created) {
    panel = (
      <div className="place-hint reveal">
        <h2>{created.visibility === "private" ? "Saved, just for you" : "Your pin is live"}</h2>
        <p className="muted">
          {created.title}
          {created.lake ? ` · near ${created.lake.name}` : ""}
        </p>
        <div className="form-actions">
          <Link href={`/community/${created.id}`} className="btn btn-primary btn-sm">
            View pin
          </Link>
          <button type="button" className="btn btn-ghost btn-sm" onClick={startPlacing}>
            Add another
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setCreated(null)}>
            Close
          </button>
        </div>
      </div>
    );
  } else {
    panel = <WaterbodyPanel waterbodyId={selectedId} />;
  }

  return (
    <div className="map-view">
      <div className="map-container">
        {selectedId === null ? (
          <>
            {!placing && <LocationSearchBar onLocate={handleLocate} />}
            <div className="map-status-stack">
              {placing && (
                <div className="map-status-chip chip-placing">
                  {draft ? "Drag the pin to adjust, then fill in the form." : "Tap the map to drop your pin."}
                </div>
              )}
              {loading && <div className="map-status-chip">Loading lakes…</div>}
              {!loading && !placing && zoom === null && (
                <div className="map-status-chip">
                  Search a city, lake, or ZIP code, or allow location access, to see fishing spots
                  near you.
                </div>
              )}
              {!loading && !zoomedOut && truncated && (
                <div className="map-status-chip">
                  Showing the first {VIEWPORT_LIMIT} lakes and ponds here. Zoom in to see the rest.
                </div>
              )}
              {!loading && zoomedOut && !placing && (
                <div className="map-status-chip">
                  Showing verified lakes only. Zoom in to see every mapped lake.
                </div>
              )}
              {showEmpty && (
                // Honest, not apologetic: the statewide layer covers Texas
                // only for now (docs/adr/0010-statewide-osm-layer.md).
                <div className="no-nearby-lakes-banner">
                  No lakes on file near {focusPoint?.label} yet. FishEye covers Texas for now.
                </div>
              )}
            </div>
            <LakeMap
              waterbodies={waterbodies}
              onSelect={placing ? () => undefined : setSelectedId}
              onViewportChange={handleViewportChange}
              focusPoint={focusPoint}
              initialView={lastView}
              pins={showPins ? pins : []}
              placing={placing}
              draft={draft}
              onPlace={(latitude, longitude) => setDraft({ latitude, longitude })}
            />
            <div className="map-fabs">
              <button
                type="button"
                className={showPins ? "map-toggle active" : "map-toggle"}
                aria-pressed={showPins}
                onClick={() => {
                  const next = !showPins;
                  setShowPins(next);
                  if (next) loadPins(lastBbox.current);
                }}
              >
                <span className="legend-catch" aria-hidden="true" /> Community pins
              </button>
              {!placing && (
                <button type="button" className="btn btn-primary btn-sm map-add" onClick={startPlacing}>
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden="true">
                    <path d="M12 5v14M5 12h14" strokeLinecap="round" />
                  </svg>
                  Add a pin
                </button>
              )}
            </div>
            <MapLegend showPins={showPins} />
          </>
        ) : (
          <>
            {/* Drill-down, not an overlay: clicking a lake replaces the
                statewide map with that lake's own zoomed-in view — this
                button is the only way back. */}
            <button type="button" className="back-to-map-button" onClick={() => setSelectedId(null)}>
              ← All lakes
            </button>
            <LakeDetailMap key={selectedId} waterbodyId={selectedId} />
          </>
        )}
      </div>
      <aside className="side-panel">{panel}</aside>
    </div>
  );
}
