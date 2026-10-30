"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { PinForm, WaterLine, type DraftWater } from "@/components/community/PinForm";
import { useToast } from "@/components/ui/Toast";
import { useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import { useLocale } from "@/i18n/client";
import { CATCHES_AVAILABLE } from "@/lib/features";
import { ApiError, listShops, listStates, listWaterbodies } from "@/lib/api/client";
import { getPin, listPins, listWaterGroups, pinWhere, updatePin } from "@/lib/api/session";
import { rememberState, useSelectedState } from "@/lib/jurisdiction";
import type {
  LakeMatch,
  PinDetail,
  PinSummary,
  Shop,
  WaterGroup,
  WaterbodyDetail,
  WaterbodyListItem,
} from "@/lib/api/types";
import { LakeReportDialog } from "@/components/waterbody/LakeReportDialog";
import { WaterbodyPanel } from "@/components/waterbody/WaterbodyPanel";
import type L from "leaflet";

import type { Viewport } from "./LakeMap";
import { LocationSearchBar, type LocatedPoint } from "./LocationSearchBar";
import { MapLegend } from "./MapLegend";
import { type StateRegion, loadStates, regionOf, stateCodeAt } from "./usStates";
import {
  MIN_ZOOM_FOR_ALL_LAKES,
  MIN_PLACE_ZOOM,
  MIN_ZOOM_FOR_SHOPS,
  SEARCH_ZOOM,
  type MapMode,
  type MapViewState,
  asExploringView,
  lakeQueryFor,
  listStateNames,
} from "./zoomPolicy";

// Leaflet touches `window` at import time, which breaks server-side
// rendering. next/dynamic with ssr:false has to be called from a client
// component (App Router forbids it from a server component directly) —
// this file is that boundary.
function MapLoading({ lake = false }: { lake?: boolean }) {
  const t = useT().map;
  return <div className="map-loading">{lake ? t.loadingLakeMap : t.loadingMap}</div>;
}
const LakeMap = dynamic(() => import("./LakeMap"), {
  ssr: false,
  loading: () => <MapLoading />,
});
const LakeDetailMap = dynamic(() => import("./LakeDetailMap"), {
  ssr: false,
  loading: () => <MapLoading lake />,
});

// Per-request cap. A dense view (with ponds included) can exceed it — at
// national coverage a view a few degrees wide over Minnesota matches
// ~150,000 lakes. The backend returns verified lakes first and then the
// LARGEST of the rest, so what is dropped is the smallest ponds and never a
// lake this app knows something about; the map says the view is partial
// rather than silently dropping the rest.
const VIEWPORT_LIMIT = 2000;
// How long "Stay here" silences the zoom-out question.
const ZOOM_OUT_ASK_QUIET_MS = 15_000;
const PIN_LIMIT = 300;
// States off the opening view, offered as buttons on the national map.
const OFFSHORE_STATES = [["AK", "Alaska"], ["HI", "Hawaii"]] as const;
// How long the pin must sit still before the water under it is looked up.
const WATER_CHECK_MS = 250;

type Point = { latitude: number; longitude: number };

function parseAt(raw: string | null, label: string): LocatedPoint | null {
  if (!raw) return null;
  const [lat, lng] = raw.split(",").map(Number);
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
  return { latitude: lat, longitude: lng, label };
}

export function MapView({ waterbodies: initialWaterbodies }: { waterbodies: WaterbodyListItem[] }) {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { user, loading: authLoading } = useAuth();
  const all = useT();
  const t = all.map;
  const tc = all.catch;
  const locale = useLocale();
  // The state chosen here or elsewhere: a search for a lake name prefers its lakes.
  const rememberedState = useSelectedState();

  // Deep links: ?lake=<id> opens a lake, ?at=<lat>,<lng> centres on a
  // point, ?addPin=1 starts placing a pin.
  const lakeParam = Number(params.get("lake"));
  const [selectedId, setSelectedId] = useState<number | null>(
    Number.isInteger(lakeParam) && lakeParam > 0 ? lakeParam : null,
  );
  const [waterbodies, setWaterbodies] = useState(initialWaterbodies);
  const [focusPoint, setFocusPoint] = useState<LocatedPoint | null>(() => parseAt(params.get("at"), t.thePin));
  // Where "Use my location" last placed the person; stays marked after a
  // later search, as it's still where they are.
  const [you, setYou] = useState<{ latitude: number; longitude: number; accuracy: number } | null>(null);
  // National (whole country, states only) or exploring (zoomPolicy.ts). A
  // link to a lake or a point already says where to look, so it opens
  // exploring; everything else starts at the states map.
  const [mode, setModeState] = useState<MapMode>(() =>
    params.get("at") || params.get("lake") || params.get("move") ? "exploring" : "national",
  );
  // Read by the viewport handler, which runs off a debounce timer and could
  // otherwise act on the mode from an earlier render.
  const modeRef = useRef(mode);
  const setMode = useCallback((next: MapMode) => {
    modeRef.current = next;
    setModeState(next);
  }, []);
  // The one state being explored. The map shows only its lakes and can't be
  // zoomed or panned out of it (LakeMap's ViewLimits). `fit` frames the whole
  // state — set when it was just picked on the national map; a state worked
  // out from where the map already is (a search, a link, back from a lake)
  // is locked in place instead.
  const [region, setRegionState] = useState<{ state: StateRegion; fit: boolean } | null>(null);
  const regionRef = useRef<StateRegion | null>(null);
  const setRegion = useCallback((next: { state: StateRegion; fit: boolean } | null) => {
    regionRef.current = next?.state ?? null;
    setRegionState(next);
  }, []);
  // Where the single-lake map is looking; see leaveLake.
  const detailView = useRef<MapViewState | null>(null);
  const [zoom, setZoom] = useState<number | null>(null);
  // "Go back to the map of all states?" offered when someone tries to zoom out
  // past exploring mode's floor. After "Stay here" it stays quiet for a while,
  // so a person who keeps scrolling isn't asked again at once.
  const [askBack, setAskBack] = useState(false);
  const askQuietUntil = useRef(0);
  const askBackButton = useRef<HTMLButtonElement>(null);
  const [loading, setLoading] = useState(false);
  const [truncated, setTruncated] = useState(false);
  // Where the overview map was last looking, so "← All lakes" returns there
  // instead of resetting to the whole country.
  const [lastView, setLastView] = useState<{ center: [number, number]; zoom: number } | null>(null);
  // "Missing a lake?": where the map's middle was when it was asked.
  const [missingAt, setMissingAt] = useState<[number, number] | null>(null);
  // Pans can overlap: only the newest request's answer is shown.
  const latestRequest = useRef(0);
  // Which states have lakes on file: lights them on the national map and
  // names them when a search lands somewhere empty. null = not known (yet).
  const [coverage, setCoverage] = useState<{ codes: Set<string>; states: [string, string][] } | null>(null);
  const coverageRef = useRef<Set<string> | null>(null);
  coverageRef.current = coverage?.codes ?? null;

  // With Catches switched off (lib/features.ts) no pins are loaded or drawn.
  // Your own catches are drawn one by one; everyone else's as one bubble per
  // water (backend ADR 0040).
  const [showPins, setShowPins] = useState(CATCHES_AVAILABLE);
  const [pins, setPins] = useState<PinSummary[]>([]);
  const [groups, setGroups] = useState<WaterGroup[]>([]);
  const lastBbox = useRef<string | null>(null);
  const latestPins = useRef(0);
  // Bait and tackle shops (ShopLayer.tsx): shown unless switched off, from
  // the zoom where every lake shows, in the state being explored.
  const [showShops, setShowShops] = useState(true);
  const [shops, setShops] = useState<Shop[]>([]);
  const latestShops = useRef(0);
  const [placing, setPlacing] = useState(CATCHES_AVAILABLE && params.get("addPin") === "1");
  const [draft, setDraft] = useState<Point | null>(null);
  // The water under the draft pin (/api/pins/where), for the map's label and
  // the form: a catch has to be on named water.
  const [draftWater, setDraftWater] = useState<DraftWater>({ state: "unknown" });
  // A catch being moved (?move=<id>): placing, but saving a new spot for it.
  const [moving, setMoving] = useState<PinDetail | null>(null);
  const [savingMove, setSavingMove] = useState(false);
  const [locating, setLocating] = useState(false);
  const [created, setCreated] = useState<PinDetail | null>(null);
  const [sheet, setSheet] = useState<"peek" | "half" | "full">(selectedId !== null ? "half" : "peek");
  const workspace = useRef<HTMLDivElement>(null);
  // The panel: on a phone a sheet over the map's bottom (LakeDetailMap frames
  // a lake above it).
  const sheetPanel = useRef<HTMLElement>(null);
  const [sheetHeight, setSheetHeight] = useState<number | null>(null);
  const sheetGesture = useRef<{ y: number; height: number; mapHeight: number; time: number } | null>(null);

  function selectLake(id: number) {
    setSelectedId(id);
    setSheet("half");
  }

  const loadPins = useCallback(
    (bbox: string | null) => {
      if (!bbox || !CATCHES_AVAILABLE) return;
      const id = ++latestPins.current;
      // The lake map works without either.
      listWaterGroups(bbox)
        .then((g) => id === latestPins.current && setGroups(g))
        .catch(() => undefined);
      if (user) {
        listPins({ bbox, mine: true, limit: PIN_LIMIT })
          .then((p) => id === latestPins.current && setPins(p.filter((pin) => pin.status !== "removed")))
          .catch(() => undefined);
      } else {
        setPins([]);
      }
    },
    [user],
  );

  const loadShops = useCallback((bbox: string | null, atZoom: number | null) => {
    const id = ++latestShops.current;
    const state = regionRef.current;
    if (!bbox || !state || atZoom === null || atZoom < MIN_ZOOM_FOR_SHOPS) {
      setShops([]);
      return;
    }
    listShops(bbox, state.code)
      .then((s) => id === latestShops.current && setShops(s))
      .catch(() => undefined); // the lake map works without them
  }, []);

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

  // ?move=<id>: the catch's page sent its owner here to put it where it was.
  const moveParam = Number(params.get("move"));
  useEffect(() => {
    if (!CATCHES_AVAILABLE || !Number.isInteger(moveParam) || moveParam <= 0 || authLoading) return;
    if (!user) {
      router.replace(`/login?next=${encodeURIComponent(`/map?move=${moveParam}`)}`);
      return;
    }
    let cancelled = false;
    getPin(moveParam)
      .then((pin) => {
        if (cancelled || !pin.can_edit) return;
        const at = { latitude: pin.latitude, longitude: pin.longitude };
        setMoving(pin);
        setPlacing(true);
        setDraft(at);
        setFocusPoint({ ...at, label: pin.title, zoom: 15 });
        setSheet("half");
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [moveParam, user, authLoading, router]);

  // The water under the draft pin, once it stops moving.
  useEffect(() => {
    if (!draft) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      setDraftWater({ state: "checking" });
      pinWhere(draft.latitude, draft.longitude, true)
        .then((w) => {
          if (cancelled) return;
          setDraftWater(
            w.water
              ? { state: "on", name: w.water.name, kind: w.water.kind }
              : { state: "off", required: Boolean(w.water_required) },
          );
        })
        // The server checks again on save; don't hold the form up on this.
        .catch(() => !cancelled && setDraftWater({ state: "unknown" }));
    }, WATER_CHECK_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [draft]);

  // Location is requested only when the person chooses Use my location.

  useEffect(() => {
    listStates()
      .then((states) => {
        const covered = states.filter((s) => s.has_waterbodies);
        setCoverage({ codes: new Set(covered.map((s) => s.code)), states: covered.map((s) => [s.code, s.name]) });
      })
      // Unknown, not "none": the states layer then leaves every state open.
      .catch(() => undefined);
  }, []);

  function clearLakesAndPins() {
    // Bumping the counters drops any answer still in flight from a closer
    // view, which would otherwise land after this and repaint the map.
    ++latestRequest.current;
    ++latestPins.current;
    ++latestShops.current;
    lastBbox.current = null;
    setWaterbodies([]);
    setPins([]);
    setGroups([]);
    setShops([]);
    setTruncated(false);
    setLoading(false);
  }

  const openState = useCallback(
    (code: string) => {
      // The states file is already loaded: the national map drew it.
      loadStates()
        .then((file) => {
          const state = regionOf(file, code);
          if (!state) return;
          setRegion({ state, fit: true });
          setMode("exploring");
          // Ask, the handbook and the guides show this state's rules from now
          // on (lib/jurisdiction.ts); the picker on those pages can change it.
          rememberState(code);
        })
        .catch((e: unknown) => console.error("could not open state:", e));
    },
    [setMode, setRegion],
  );
  const enterState = useCallback((_bounds: L.LatLngBounds, code: string) => openState(code), [openState]);

  function backToStates() {
    setAskBack(false);
    setMode("national");
    setFocusPoint(null); // also clears the "no lakes near …" banner
    setRegion(null);
    setLastView(null);
    clearLakesAndPins();
  }

  /** Back from a single lake to the overview. `view` is where the lake map
   * was when the person zoomed out of it; the button passes nothing and
   * returns to where the overview last was — or, for a lake opened from a
   * link with no overview behind it, to where the lake map is. */
  function leaveLake(view?: MapViewState) {
    const target = view ?? lastView ?? detailView.current;
    setLastView(target ? asExploringView(target) : null);
    setMode("exploring");
    setSelectedId(null);
    setSheet("peek");
  }

  function offerBackToStates() {
    if (Date.now() < askQuietUntil.current) return;
    setAskBack(true);
  }

  function stayHere() {
    askQuietUntil.current = Date.now() + ZOOM_OUT_ASK_QUIET_MS;
    setAskBack(false);
  }

  // Moving focus into the prompt lets Enter accept and Escape decline.
  useEffect(() => {
    if (askBack) askBackButton.current?.focus();
  }, [askBack]);

  function handleViewportChange({ bbox, zoom: newZoom, center }: Viewport) {
    setZoom(newZoom);
    // The person moved the map themselves: the question no longer applies.
    setAskBack(false);
    const query = lakeQueryFor(modeRef.current, newZoom);
    if (query === null) {
      // National mode: the states layer is the way in, so no lakes and no
      // pins — not a single request.
      clearLakesAndPins();
      return;
    }
    // Only exploring views are remembered: "← All lakes" must never return
    // someone to the locked national map.
    setLastView({ center, zoom: newZoom });
    const requestId = ++latestRequest.current;
    lastBbox.current = bbox;
    if (showPins) loadPins(bbox);
    // With no state yet this clears them; the call below, once the state
    // under the map is known, loads that state's.
    if (showShops) loadShops(bbox, newZoom);

    const state = regionRef.current;
    if (!state) {
      // Lakes are only ever one state's. While placing a pin the map roams
      // free and shows none; otherwise (a search, a link, back from a lake)
      // the state is the one under the middle of the map, which then locks.
      setWaterbodies([]);
      setTruncated(false);
      if (placing) {
        setLoading(false);
        return;
      }
      setLoading(true);
      loadStates()
        .then((file) => {
          if (requestId !== latestRequest.current || regionRef.current) return;
          const code = stateCodeAt(file, center[0], center[1], coverageRef.current);
          const found = code ? regionOf(file, code) : null;
          if (!found) {
            setLoading(false);
            return;
          }
          setRegion({ state: found, fit: false });
          if (coverageRef.current?.has(found.code)) rememberState(found.code);
          handleViewportChange({ bbox, zoom: newZoom, center });
        })
        .catch(() => {
          if (requestId === latestRequest.current) setLoading(false);
        });
      return;
    }

    setLoading(true);
    listWaterbodies({ bbox, stateCode: state.code, ...query, limit: VIEWPORT_LIMIT })
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

  /** A lake the search found by name: straight to it. Back from it, the
   * overview opens where the lake map is and locks to that lake's state. */
  function openFoundLake(lake: LakeMatch) {
    setLastView(null);
    setRegion(null);
    setFocusPoint(null);
    setMode("exploring");
    selectLake(lake.id);
  }

  function handleLocate(point: LocatedPoint) {
    setSelectedId(null);
    // The place may be in another state: unlock, fly there, and lock to
    // whichever state the map lands in.
    setRegion(null);
    setMode("exploring");
    // Flying there fires moveend, which loads that area's lakes through
    // handleViewportChange like any other pan. Until then the last view's
    // zoom says nothing about this one: no "no lakes" banner mid-flight.
    setZoom(null);
    setFocusPoint(point);
    if (point.own) setYou({ latitude: point.latitude, longitude: point.longitude, accuracy: point.own.accuracy });
  }

  /** Drops the catch's pin where the phone is: at the water, the usual case. */
  function pinWhereIAm() {
    if (!navigator.geolocation) {
      toast(t.noGeolocation, "error");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        const point = { latitude: position.coords.latitude, longitude: position.coords.longitude };
        handleLocate({ ...point, label: t.yourLocation, own: { accuracy: position.coords.accuracy } });
        setDraft(point);
      },
      () => {
        setLocating(false);
        toast(t.noFix, "error");
      },
      { enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000 },
    );
  }

  function startPlacing() {
    if (!CATCHES_AVAILABLE) {
      toast(all.common.catchesSoon, "info");
      return;
    }
    if (!user) {
      router.push(`/login?next=${encodeURIComponent("/map?addPin=1")}`);
      return;
    }
    setCreated(null);
    setDraft(null);
    setMoving(null);
    setShowPins(true);
    // A pin needs a map you can zoom into; the national map is locked.
    setMode("exploring");
    setPlacing(true);
    setSheet("half");
  }

  /** "Share a catch here" on a lake: back on the map, close in on that lake
   * (the whole of a big one, within tapping distance of its shore), placing a
   * catch, so the pin goes where they fished on that water. */
  function shareAtLake(lake: WaterbodyDetail) {
    const [south, west, north, east] = lake.bounds ?? [0, 0, 0.004, 0.004];
    const span = Math.max(east - west, (north - south) * 1.3, 0.001);
    const zoom = Math.min(16, Math.max(MIN_PLACE_ZOOM, Math.round(Math.log2(1260 / span)) - 1));
    setLastView({ center: [lake.latitude, lake.longitude], zoom });
    setSelectedId(null);
    startPlacing();
  }

  function stopPlacing() {
    const wasMoving = moving;
    setPlacing(false);
    setDraft(null);
    setMoving(null);
    if (wasMoving) router.push(`/community/${wasMoving.id}`);
    else if (params.get("addPin")) router.replace("/map", { scroll: false });
  }

  async function saveMove() {
    if (!moving || !draft) return;
    setSavingMove(true);
    try {
      await updatePin(moving.id, { latitude: draft.latitude, longitude: draft.longitude });
      toast(tc.moved);
      router.push(`/community/${moving.id}`);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : tc.saveFailed, "error");
      setSavingMove(false);
    }
  }

  function handleCreated(pin: PinDetail) {
    setPins((all) => [pin, ...all.filter((p) => p.id !== pin.id)]);
    setCreated(pin);
    setPlacing(false);
    setDraft(null);
    toast(pin.visibility === "private" ? tc.savedPrivate : tc.sharedLive);
    if (params.get("addPin")) router.replace("/map", { scroll: false });
  }

  const national = mode === "national";
  const zoomedOut = !national && zoom !== null && zoom < MIN_ZOOM_FOR_ALL_LAKES;
  const showEmpty =
    !national && focusPoint !== null && zoom !== null && !loading && !zoomedOut && waterbodies.length === 0 && !placing;

  const offWater = draftWater.state === "off" && draftWater.required;
  const reportMissingHere = () => draft && setMissingAt([draft.latitude, draft.longitude]);

  let panel: React.ReactNode;
  if (placing && moving) {
    panel = (
      <div className="place-hint reveal">
        <h2>{tc.moveTitle}</h2>
        <p className="muted">{moving.title}</p>
        {draft ? <WaterLine water={draftWater} onMissingWater={reportMissingHere} /> : <p className="muted">{tc.moveHint}</p>}
        <div className="form-actions">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={saveMove}
            disabled={!draft || savingMove || offWater || draftWater.state === "checking"}
          >
            {savingMove ? all.common.saving : tc.moveSave}
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={stopPlacing}>
            {all.common.cancel}
          </button>
        </div>
      </div>
    );
  } else if (placing && draft) {
    panel = (
      <PinForm
        key="form"
        point={draft}
        water={draftWater}
        onCreated={handleCreated}
        onCancel={stopPlacing}
        onMove={(latitude, longitude) => {
          handleLocate({ latitude, longitude, label: t.photoSpot });
          setDraft({ latitude, longitude });
        }}
        onMissingWater={reportMissingHere}
      />
    );
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
        <h2>{tc.whereTitle}</h2>
        <p className="muted">{tc.whereHint}</p>
        <div className="form-actions">
          <button type="button" className="btn btn-primary btn-sm" onClick={pinWhereIAm} disabled={locating}>
            {locating ? tc.findingYou : tc.pinHere}
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={stopPlacing}>
            {all.common.cancel}
          </button>
        </div>
      </div>
    );
  } else if (created) {
    panel = (
      <div className="place-hint reveal">
        <h2>{created.visibility === "private" ? tc.createdPrivate : tc.createdLive}</h2>
        <p className="muted">
          {created.title}
          {created.water ? ` · ${created.water.name}` : created.lake ? ` · ${created.lake.name}` : ""}
        </p>
        <div className="form-actions">
          <Link href={`/community/${created.id}`} className="btn btn-primary btn-sm">
            {tc.viewCatch}
          </Link>
          <button type="button" className="btn btn-ghost btn-sm" onClick={startPlacing}>
            {tc.addAnother}
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setCreated(null)}>
            {all.common.close}
          </button>
        </div>
      </div>
    );
  } else {
    panel = (
      <WaterbodyPanel
        key={selectedId ?? "overview"}
        waterbodyId={selectedId}
        onExplore={handleLocate}
        // A lake that isn't on the map, placed at the map's middle (ADR 0039):
        // a link in the panel rather than one more button over the map.
        onMissingLake={lastView && !national ? () => setMissingAt(lastView.center) : undefined}
        onShareHere={CATCHES_AVAILABLE ? shareAtLake : undefined}
      />
    );
  }

  return (
    <div ref={workspace} className={selectedId !== null ? "map-view has-lake" : "map-view"} data-sheet={sheet}>
      <div className="map-container">
        {selectedId === null ? (
          <>
            {/* Also while placing a catch: finding the lake by name beats
                zooming in on it from the whole country. */}
            <LocationSearchBar
              onLocate={handleLocate}
              onLake={
                placing
                  ? (lake) => handleLocate({ latitude: lake.latitude, longitude: lake.longitude, label: lake.name, zoom: 15 })
                  : openFoundLake
              }
              stateCode={region?.state.code ?? rememberedState}
              near={lastView ? { latitude: lastView.center[0], longitude: lastView.center[1] } : null}
            />
            <div className="map-status-stack">
              {placing && (
                <div className={offWater ? "map-status-chip chip-placing is-off" : "map-status-chip chip-placing"}>
                  {draft
                    ? draftWater.state === "on"
                      ? tc.chipOn(draftWater.name)
                      : offWater
                        ? tc.chipOff
                        : draftWater.state === "checking"
                          ? tc.chipChecking
                          : tc.dragToAdjust
                    : zoom === null || zoom < MIN_PLACE_ZOOM
                      ? tc.chipZoom
                      : tc.chipTap}
                </div>
              )}
              {loading && <div className="map-status-chip">{t.loadingLakes}</div>}
              {!loading && !placing && national && <div className="map-status-chip">{t.pickState}</div>}
              {/* Alaska and Hawaii sit outside the opening view, and Hawaii's
                  islands are a few pixels wide at country scale. */}
              {!loading && !placing && national && (
                <div className="map-offshore" aria-label={t.offshore}>
                  {OFFSHORE_STATES.map(([code, name]) => (
                    <button
                      key={code}
                      type="button"
                      className="map-status-chip map-offshore-state"
                      onClick={() => openState(code)}
                    >
                      {localStateName(code, name, locale)} ↗
                    </button>
                  ))}
                </div>
              )}
              {!loading && !national && !zoomedOut && truncated && (
                <div className="map-status-chip">{t.shownLimit(VIEWPORT_LIMIT)}</div>
              )}
              {!loading && zoomedOut && !placing && (
                <div className="map-status-chip">{t.officialOnly(showShops)}</div>
              )}
              {showEmpty && (
                // Honest, not apologetic, and named from the data rather than
                // hardcoded, so it stays true as states are imported. Closer
                // than a search's framing (Use my location's street level) an
                // empty view says nothing about the area around it.
                <div className="no-nearby-lakes-banner">
                  {zoom !== null && zoom > SEARCH_ZOOM ? (
                    t.noLakesInView
                  ) : (
                    <>
                      {t.noLakesNear(focusPoint?.label ?? "")}
                      {coverage && coverage.states.length > 0 && coverage.states.length <= 4
                        ? t.coversOnly(
                            listStateNames(
                              coverage.states.map(([code, name]) => localStateName(code, name, locale)),
                              { sep: all.common.listSep, and: all.common.listAnd },
                            ),
                          )
                        : ""}
                    </>
                  )}
                </div>
              )}
            </div>
            <LakeMap
              waterbodies={waterbodies}
              onSelect={placing ? () => undefined : selectLake}
              onViewportChange={handleViewportChange}
              focusPoint={focusPoint}
              you={you}
              initialView={national ? null : lastView}
              pins={showPins ? pins : []}
              groups={showPins && !placing ? groups : []}
              shops={showShops ? shops : []}
              placing={placing}
              draft={draft}
              draftLabel={
                draftWater.state === "on" ? draftWater.name : offWater ? tc.chipOff.split(" · ")[0] : null
              }
              draftOff={offWater}
              onPlace={(latitude, longitude) => { setDraft({ latitude, longitude }); setSheet("full"); }}
              coveredStates={coverage?.codes ?? null}
              mode={mode}
              onEnterState={enterState}
              region={national ? null : (region?.state ?? null)}
              fitRegion={region?.fit ?? false}
              frozen={askBack && !national && !placing}
              onAllStates={backToStates}
              onZoomOutBlocked={offerBackToStates}
            />
            {askBack && !national && !placing && (
              <div
                className="zoom-out-prompt"
                role="dialog"
                aria-label={t.backQuestion}
                onKeyDown={(e) => {
                  if (e.key === "Escape") stayHere();
                }}
              >
                <p>
                  {region ? t.allOfState(localStateName(region.state.code, region.state.name, locale)) : t.asFarAsItGoes}{" "}
                  {t.goBackQuestion}
                </p>
                <div className="zoom-out-prompt-actions">
                  <button ref={askBackButton} type="button" className="btn btn-primary btn-sm" onClick={backToStates}>
                    {t.backToStates}
                  </button>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={stayHere}>
                    {t.stayHere}
                  </button>
                </div>
              </div>
            )}
            <div className="map-fabs">
              {CATCHES_AVAILABLE ? (
                <button
                  type="button"
                  className={showPins ? "map-toggle active" : "map-toggle"}
                  aria-pressed={showPins}
                  aria-label={t.catches}
                  onClick={() => {
                    const next = !showPins;
                    setShowPins(next);
                    if (next) loadPins(lastBbox.current);
                  }}
                >
                  <span className="legend-catch" aria-hidden="true" /> <span className="fab-label">{t.catches}</span>
                </button>
              ) : (
                <button
                  type="button"
                  className="map-toggle is-unavailable"
                  aria-disabled="true"
                  aria-label={t.catchesUnavailable}
                  title={all.common.catchesSoon}
                  onClick={() => toast(all.common.catchesSoon, "info")}
                >
                  <span className="legend-catch" aria-hidden="true" /> <span className="fab-label">{t.catches}</span>
                  <span className="fab-unavailable">{all.common.unavailable}</span>
                </button>
              )}
              <button
                type="button"
                className={showShops ? "map-toggle active" : "map-toggle"}
                aria-pressed={showShops}
                aria-label={t.shopsToggleLabel}
                onClick={() => {
                  const next = !showShops;
                  setShowShops(next);
                  if (next) loadShops(lastBbox.current, zoom);
                }}
              >
                <span className="legend-shop" aria-hidden="true" /> <span className="fab-label">{t.shopsToggle}</span>
              </button>
              {!placing && (
                <button
                  type="button"
                  className={CATCHES_AVAILABLE ? "btn btn-primary btn-sm map-add" : "btn btn-primary btn-sm map-add is-unavailable"}
                  onClick={startPlacing}
                  aria-label={CATCHES_AVAILABLE ? t.shareCatchLabel : t.shareCatchUnavailable}
                  aria-disabled={CATCHES_AVAILABLE ? undefined : "true"}
                  title={CATCHES_AVAILABLE ? undefined : all.common.catchesSoon}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden="true">
                    <path d="M12 5v14M5 12h14" strokeLinecap="round" />
                  </svg>
                  <span className="fab-label">{t.shareCatch}</span>
                  {!CATCHES_AVAILABLE && <span className="fab-unavailable">{all.common.unavailable}</span>}
                </button>
              )}
            </div>
            <MapLegend showPins={showPins && (pins.length > 0 || groups.length > 0)} showShops={showShops && shops.length > 0} />
            {missingAt && (
              <LakeReportDialog
                target={{ kind: "missing", point: { latitude: missingAt[0], longitude: missingAt[1] } }}
                open
                onClose={() => setMissingAt(null)}
                onSent={() => toast(t.missingThanks)}
              />
            )}
          </>
        ) : (
          <>
            {/* Drill-down, not an overlay: clicking a lake replaces the
                overview with that lake's own zoomed-in view. Two ways back:
                this button, or zooming out of the lake. */}
            <button
              type="button"
              className="back-to-map-button"
              title={t.orZoomOut}
              onClick={() => leaveLake()}
            >
              {t.allLakes}
            </button>
            <LakeDetailMap
              key={selectedId}
              waterbodyId={selectedId}
              fromZoom={lastView?.zoom}
              cover={sheetPanel}
              onExit={leaveLake}
              onViewChange={(v) => {
                detailView.current = v;
              }}
            />
          </>
        )}
      </div>
      <aside ref={sheetPanel} className="side-panel" style={sheetHeight === null ? undefined : { height: sheetHeight, transition: 'none' }}>
        <div className="sheet-controls"
          onPointerDown={(e) => {
            if ((e.target as HTMLElement).closest("button") || !workspace.current) return;
            sheetGesture.current = { y: e.clientY, height: e.currentTarget.parentElement!.getBoundingClientRect().height, mapHeight: workspace.current.clientHeight, time: performance.now() };
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerMove={(e) => {
            const gesture = sheetGesture.current;
            if (gesture) setSheetHeight(Math.max(95, Math.min(gesture.mapHeight * .86, gesture.height + gesture.y - e.clientY)));
          }}
          onPointerUp={(e) => {
            const gesture = sheetGesture.current;
            if (!gesture) return;
            const delta = gesture.y - e.clientY;
            const levels = ['peek', 'half', 'full'] as const;
            const heights = [95, gesture.mapHeight * .45, gesture.mapHeight * .86];
            const endHeight = gesture.height + delta;
            const velocity = Math.abs(delta) / Math.max(1, performance.now() - gesture.time);
            const next = velocity > .45 && Math.abs(delta) > 25
              ? Math.max(0, Math.min(2, levels.indexOf(sheet) + (delta > 0 ? 1 : -1)))
              : heights.reduce((best, value, index) => Math.abs(value - endHeight) < Math.abs(heights[best] - endHeight) ? index : best, 0);
            setSheet(levels[next]); setSheetHeight(null); sheetGesture.current = null;
          }}
          onPointerCancel={() => { sheetGesture.current = null; setSheetHeight(null); }}>
          <span className="sheet-handle" aria-hidden="true" />
          <div className="sheet-toolbar"><span className="sheet-caption">{placing ? t.sheetCatch : selectedId ? t.sheetLake : t.sheetExplore}</span><div className="sheet-actions">
            {([['peek', t.sheetMap], ['half', t.sheetPlan], ['full', t.sheetFull]] as const).map(([value, label]) => <button key={value} type="button" aria-pressed={sheet === value} onClick={() => { setSheet(value); setSheetHeight(null); }}>{label}</button>)}
          </div></div>
        </div>
        <div className="sheet-content">{panel}</div>
      </aside>
    </div>
  );
}
