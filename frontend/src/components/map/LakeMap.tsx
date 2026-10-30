"use client";

import "leaflet/dist/leaflet.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.Default.css";
import L from "leaflet";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Circle,
  MapContainer,
  Marker,
  Polygon,
  Popup,
  Tooltip,
  ZoomControl,
  useMap,
  useMapEvents,
} from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

import type { PinSummary, Shop, WaterGroup, WaterbodyListItem } from "@/lib/api/types";
import { MAP_MAX_ZOOM, MAP_MIN_ZOOM } from "@/lib/map/tiles";
import { BaseMap } from "./BaseMap";
import { waterIcon } from "./waterIcon";
import { useT } from "@/i18n/client";
import { DraftMarker, PinMarkers, PlaceOnClick, WaterGroupMarkers } from "./PinLayer";
import { ShopMarkers } from "./ShopLayer";
import { StatesLayer } from "./StatesLayer";
import { displayLongitude, type StateRegion } from "./usStates";
import { SEARCH_ZOOM, US_CENTER, US_ZOOM, type MapMode, locationZoom, zoomLimitsFor } from "./zoomPolicy";

const VIEWPORT_DEBOUNCE_MS = 300;
const YOU_COLOR = "#2563eb";
// Space kept around a state when the map frames it.
const STATE_PADDING = 24;

export interface Viewport {
  bbox: string; // "west,south,east,north"
  zoom: number;
  center: [number, number];
}

/**
 * Reports the visible area after the user stops moving the map — including
 * a real move that FlyToFocus triggers (geolocation, search, a ?at= deep
 * link), since Leaflet fires moveend for those the same as a manual pan.
 *
 * It deliberately does *not* also report on mount for the plain default
 * view (the whole country, no focus point): that view carries no information
 * about where the person actually is, so loading and showing this app's
 * handful of "verified" lakes for it would just be noise before the person
 * has said where they're interested in. `loadOnMount` is true only when
 * restoring a previously-visited view (returning from a lake's detail
 * page), where the view itself is meaningful.
 */
function ViewportWatcher({ onChange, loadOnMount }: { onChange: (viewport: Viewport) => void; loadOnMount: boolean }) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const map = useMapEvents({
    // A new move makes a report still waiting on the last one stale: reading
    // the map mid-flight would lock whichever state the flight was crossing.
    movestart: () => {
      if (timer.current) clearTimeout(timer.current);
    },
    moveend: () => schedule(),
  });

  function schedule() {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => onChange(read()), VIEWPORT_DEBOUNCE_MS);
  }

  function read(): Viewport {
    const c = map.getCenter();
    return { bbox: map.getBounds().toBBoxString(), zoom: map.getZoom(), center: [c.lat, c.lng] };
  }

  useEffect(() => {
    if (loadOnMount) onChange(read());
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
    // Mount-only: later reports come from moveend.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

/**
 * Flies to the last searched / located point: a searched place at town
 * scale, the person's own position at street level (zoomPolicy's
 * locationZoom). The map no longer re-fits itself to whatever markers are
 * loaded: markers are now *loaded from* the viewport, so fitting the
 * viewport to the markers would loop.
 */
function FlyToFocus({
  focusPoint,
  skipOnMount,
}: {
  focusPoint: { latitude: number; longitude: number; own?: { accuracy: number }; zoom?: number } | null;
  skipOnMount: boolean;
}) {
  const map = useMap();
  // When the map is remounted to restore a previous view (coming back from
  // a lake's detail map), the old search point must not yank it away again.
  // Tracks the point already flown to rather than skipping "the first run":
  // React runs mount effects twice in development, which used up such a
  // skip and flew anyway.
  const applied = useRef(skipOnMount ? focusPoint : null);
  useEffect(() => {
    if (!focusPoint || focusPoint === applied.current) return;
    applied.current = focusPoint;
    const at = L.latLng(focusPoint.latitude, focusPoint.longitude);
    const zoom = focusPoint.own
      ? locationZoom(map.getBoundsZoom(at.toBounds(focusPoint.own.accuracy * 2)))
      : (focusPoint.zoom ?? SEARCH_ZOOM);
    map.flyTo(at, zoom);
  }, [focusPoint, map]);
  return null;
}

// The dot is a marker icon, not an SVG circle. While the map zooms, Leaflet
// scales its whole SVG layer and redraws it only when the move ends, so a
// fixed-size circle swelled with every level of a flight (from state scale
// to street level, a thousandfold: the whole screen) and snapped back on
// landing. Markers are repositioned each frame and keep their size.
const YOU_ICON = L.divIcon({ className: "you-are-here-dot", iconSize: [18, 18], tooltipAnchor: [0, -10] });

// Below this many pixels the accuracy circle says nothing, and Leaflet draws
// it at least 1 px wide anyway: that pixel, scaled up by a flight, became a
// blue disc over the whole map. It is drawn only once the map is close enough.
const ACCURACY_MIN_PX = 4;

function metresPerPixel(latitude: number, zoom: number): number {
  return (40_075_016.686 * Math.cos((latitude * Math.PI) / 180)) / 2 ** (zoom + 8);
}

/**
 * "Use my location": a blue dot where the browser places the person, labelled,
 * in a pale circle as wide as the browser says the fix may be off. Neither
 * takes clicks, so a lake under them still opens.
 */
export function YouAreHere({
  at,
  region = null,
}: {
  at: { latitude: number; longitude: number; accuracy: number };
  region?: StateRegion | null;
}) {
  const map = useMap();
  // The zoom the map last settled at, not each frame of a zoom in progress.
  const [zoom, setZoom] = useState(() => map.getZoom());
  useMapEvents({ zoomend: () => setZoom(map.getZoom()) });
  const center: [number, number] = [at.latitude, displayLongitude(at.longitude, region)];
  const showAccuracy = at.accuracy / metresPerPixel(at.latitude, zoom) >= ACCURACY_MIN_PX;
  const t = useT();
  return (
    <>
      {showAccuracy && (
        <Circle
          center={center}
          radius={at.accuracy}
          interactive={false}
          pathOptions={{ color: YOU_COLOR, weight: 1, opacity: 0.5, fillColor: YOU_COLOR, fillOpacity: 0.12 }}
        />
      )}
      <Marker position={center} icon={YOU_ICON} interactive={false} keyboard={false} zIndexOffset={1000}>
        <Tooltip permanent direction="top" className="you-are-here">
          {t.map.youAreHere}
        </Tooltip>
      </Marker>
    </>
  );
}

const WORLD_RING: [number, number][] = [
  [-85, -540],
  [85, -540],
  [85, 540],
  [-85, 540],
];

/**
 * Applies the limits of the current mode (zoomPolicy.ts) and, inside a state,
 * locks the map to that state: it can't zoom out past the level that shows the
 * whole state, nor pan away from it. On the way back to national mode it
 * re-centres on the country.
 *
 * Rendered before FlyToFocus so that, when a search switches the mode and asks
 * for a new view in the same update, the limits are lifted before the map
 * flies rather than clamping the flight. Applied only when the mode or the
 * state actually changes: re-applying a floor the map already has is not a
 * no-op in Leaflet (setMinZoom snaps a map below it up to it), and landing
 * that mid-flight cancels the flight.
 *
 * `fit` frames the whole state — for a state just picked on the national
 * map. A state worked out from where the map already is (after a search, or
 * coming back from a lake) is locked without moving the map; so is the state
 * on a map remounted to restore a view (`skipFitOnMount`).
 */
function ViewLimits({
  mode,
  region,
  fit,
  skipFitOnMount,
}: {
  mode: MapMode;
  region: StateRegion | null;
  fit: boolean;
  skipFitOnMount: boolean;
}) {
  const map = useMap();
  const previous = useRef<{ mode: MapMode; code: string | null } | null>(null);
  useEffect(() => {
    const code = mode === "exploring" ? (region?.code ?? null) : null;
    const prev = previous.current;
    if (prev && prev.mode === mode && prev.code === code) return;
    previous.current = { mode, code };

    if (mode === "national") {
      const { min, max } = zoomLimitsFor("national");
      map.setMaxBounds(undefined);
      // Leaflet rejects a minimum above the current maximum, so the limit
      // that moves outward is set first.
      map.setMinZoom(min);
      if (prev?.mode === "exploring") map.setView(US_CENTER, US_ZOOM, { animate: false });
      map.setMaxZoom(max);
      return;
    }

    const { min, max } = zoomLimitsFor("exploring");
    map.setMaxZoom(max);
    if (!region) {
      map.setMaxBounds(undefined);
      // Up to the floor at once. setMinZoom alone would animate there, and
      // that animation ends after a search's flight has begun: it jumps the
      // map back to where it started and reports that view, which then
      // locks the wrong state.
      if (map.getZoom() < min) map.setZoom(min, { animate: false });
      map.setMinZoom(min);
      return;
    }
    const bounds = L.latLngBounds(region.bounds);
    // Alaska's region runs west of -180 (usStates.displayLongitude). A view
    // that landed on the Aleutians east of the date line (a search for Attu)
    // is the same place 360° west; move there before the bounds would drag
    // the map back to the mainland.
    const center = map.getCenter();
    if (region.bounds[0][1] < -180 && center.lng > 0) {
      map.setView([center.lat, center.lng - 360], map.getZoom(), { animate: false });
    }
    const pad = L.point(STATE_PADDING * 2, STATE_PADDING * 2);
    const floor = Math.max(min, map.getBoundsZoom(bounds, false, pad));
    if (fit && !(prev === null && skipFitOnMount)) {
      map.setMaxBounds(undefined);
      map.fitBounds(bounds, { padding: [STATE_PADDING, STATE_PADDING], animate: false });
    }
    map.setMinZoom(floor);
    map.setMaxBounds(bounds.pad(0.1));
  }, [map, mode, region, fit, skipFitOnMount]);
  return null;
}

/** Dims everything outside the state being explored and outlines it, so it
 * reads as "this state", not a crop of the whole map. */
function RegionMask({ region }: { region: StateRegion }) {
  return (
    <>
      <Polygon
        positions={[WORLD_RING, ...region.rings]}
        interactive={false}
        pathOptions={{ stroke: false, fillColor: "#1d3a30", fillOpacity: 0.22 }}
      />
      <Polygon
        positions={region.rings}
        interactive={false}
        pathOptions={{ color: "#1f6b52", weight: 2, opacity: 0.7, fill: false }}
      />
    </>
  );
}

/** Holds the map still while the "back to all states?" question is open. */
function Freeze({ frozen }: { frozen: boolean }) {
  const map = useMap();
  useEffect(() => {
    const handlers = [map.scrollWheelZoom, map.dragging, map.touchZoom, map.doubleClickZoom, map.boxZoom, map.keyboard];
    for (const h of handlers) {
      if (frozen) h.disable();
      else h.enable();
    }
  }, [map, frozen]);
  return null;
}

/**
 * "All states": the only way back to the national map, since exploring mode
 * stops zooming out at state scale (zoomPolicy.ts). A real Leaflet control in
 * the bottom-right corner, added after the zoom buttons so Leaflet stacks it
 * directly above + / − — it *is* the next zoom-out step — rather than another
 * floating button competing with the search bar at narrow widths.
 */
function AllStatesControl({ onClick }: { onClick: () => void }) {
  const map = useMap();
  const t = useT();
  const { allStates, allStatesTitle } = t.map;
  const latest = useRef(onClick);
  useEffect(() => {
    latest.current = onClick;
  });
  useEffect(() => {
    const control = new L.Control({ position: "bottomright" });
    control.onAdd = () => {
      const button = L.DomUtil.create("button", "map-toggle active all-states-control");
      button.type = "button";
      button.title = allStatesTitle;
      button.innerHTML =
        '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
        '<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z M9 3v15 M15 6v15" stroke-linejoin="round"/></svg>' +
        `<span>${allStates}</span>`;
      L.DomEvent.disableClickPropagation(button);
      L.DomEvent.on(button, "click", () => latest.current());
      return button;
    };
    control.addTo(map);
    return () => {
      control.remove();
    };
  }, [map, allStates, allStatesTitle]);
  return null;
}

const ZOOM_OUT_PROMPT_GAP_MS = 1200;

/**
 * Inside a state the map stops zooming out once the whole state shows
 * (ViewLimits), and a map
 * that silently refuses to zoom out reads as broken. This notices someone
 * trying to zoom out further while already at that floor — scroll wheel, the
 * "-" key, or a pinch — and tells the parent, which offers the way back to
 * the map of all states. It never moves the map itself: the person decides.
 *
 * Leaflet clamps zoom before any zoom event fires, so a refused zoom-out
 * can't be observed through Leaflet's own events; the raw input is watched
 * instead. Calls are spaced out so one long wheel spin asks once.
 */
export function ZoomOutLimit({ onBlocked }: { onBlocked: () => void }) {
  const map = useMap();
  const latest = useRef(onBlocked);
  useEffect(() => {
    latest.current = onBlocked;
  });
  useEffect(() => {
    const el = map.getContainer();
    let last = 0;
    const atFloor = () => map.getZoom() <= map.getMinZoom();
    const blocked = () => {
      const now = Date.now();
      if (now - last < ZOOM_OUT_PROMPT_GAP_MS) return;
      last = now;
      latest.current();
    };
    const onWheel = (e: WheelEvent) => {
      if (e.deltaY > 0 && atFloor()) blocked();
    };
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === "-" || e.key === "_") && atFloor()) blocked();
    };
    let pinchStart: number | null = null;
    const spread = (e: TouchEvent) => Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY,
    );
    const onTouchStart = (e: TouchEvent) => {
      pinchStart = e.touches.length === 2 ? spread(e) : null;
    };
    const onTouchMove = (e: TouchEvent) => {
      if (pinchStart === null || e.touches.length !== 2) return;
      // Fingers closing together = zoom out.
      if (spread(e) < pinchStart - 30 && atFloor()) {
        pinchStart = spread(e);
        blocked();
      }
    };
    el.addEventListener("wheel", onWheel, { passive: true });
    el.addEventListener("keydown", onKey);
    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchmove", onTouchMove, { passive: true });
    return () => {
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("keydown", onKey);
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchmove", onTouchMove);
    };
  }, [map]);
  return null;
}

/** The cluster bubble Leaflet.markercluster draws by default (same classes,
 * so the same look), plus words for a screen reader: the bubble is a
 * focusable button whose name is its text, and "12" alone says nothing. */
export function clusterIcon(cluster: { getChildCount: () => number }, label = "lakes here. Zoom in to see them.") {
  const n = cluster.getChildCount();
  const size = n < 10 ? "small" : n < 100 ? "medium" : "large";
  return L.divIcon({
    html: `<div><span>${n}<span class="sr-only"> ${label}</span></span></div>`,
    className: `marker-cluster marker-cluster-${size}`,
    iconSize: L.point(40, 40),
  });
}

function LakeMarker({ lake, onSelect, region }: { lake: WaterbodyListItem; onSelect: (id: number) => void; region?: StateRegion | null }) {
  const t = useT().map;
  const isOsm = lake.data_tier === "osm";
  const reported = lake.reported_species_count ?? 0;
  const icon = waterIcon(isOsm ? reported > 0 ? "reported" : "osm" : "verified");
  return (
    <Marker
      position={[lake.latitude, displayLongitude(lake.longitude, region)]}
      icon={icon}
      // Leaflet gives a div icon no alt; its title is the marker's name for
      // a screen reader (Leaflet makes the marker a focusable button).
      title={`${lake.name}, ${isOsm ? t.lakeUnverified : t.lakeVerified}`}
      eventHandlers={{ click: () => onSelect(lake.id) }}
    >
      <Popup>
        <strong>{lake.name}</strong>
        {isOsm ? (
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            {lake.public_access_status === "likely_private" ? t.probablyPrivate : ""}
            {lake.water_type === "pond" ? t.pond : ""}{t.unverifiedData}
            {reported > 0 && (
              <div style={{ color: "#92400e" }}>
                {t.speciesOnRecord(reported)}
              </div>
            )}
          </div>
        ) : (
          lake.field_tested && (
            <div style={{ fontSize: 12, color: "#2563eb" }}>{t.fieldTested}</div>
          )
        )}
      </Popup>
    </Marker>
  );
}

export default function LakeMap({
  waterbodies,
  onSelect,
  onViewportChange,
  focusPoint = null,
  you = null,
  initialView = null,
  pins = [],
  groups = [],
  shops = [],
  placing = false,
  draft = null,
  draftLabel = null,
  draftOff = false,
  onPlace,
  coveredStates = null,
  mode = "exploring",
  onEnterState = () => undefined,
  region = null,
  fitRegion = false,
  frozen = false,
  onAllStates,
  onZoomOutBlocked,
}: {
  waterbodies: WaterbodyListItem[];
  onSelect: (id: number) => void;
  onViewportChange: (viewport: Viewport) => void;
  focusPoint?: { latitude: number; longitude: number; own?: { accuracy: number }; zoom?: number } | null;
  // Where "Use my location" placed the person, marked while exploring.
  you?: { latitude: number; longitude: number; accuracy: number } | null;
  // Where to open the map; defaults to the whole country, where the states
  // layer is the way in.
  initialView?: { center: [number, number]; zoom: number } | null;
  // Your own catches in view, one by one; everyone else's, one bubble per
  // water (backend ADR 0040); and the "add a catch" mode (MapView.tsx).
  pins?: PinSummary[];
  groups?: WaterGroup[];
  // Bait and tackle shops in view (ShopLayer.tsx).
  shops?: Shop[];
  placing?: boolean;
  draft?: { latitude: number; longitude: number } | null;
  // The water the draft pin is on, or that it's on none (`draftOff`).
  draftLabel?: string | null;
  draftOff?: boolean;
  onPlace?: (lat: number, lng: number) => void;
  // State codes with lakes on file; null while unknown (StatesLayer.tsx).
  coveredStates?: Set<string> | null;
  // National (states only, zoom locked) or exploring — zoomPolicy.ts.
  mode?: MapMode;
  onEnterState?: (bounds: L.LatLngBounds, code: string) => void;
  // The state being explored: the map shows it alone and can't leave it.
  region?: StateRegion | null;
  // Frame the whole state (it was just picked) rather than lock in place.
  fitRegion?: boolean;
  // Hold the map still (a question about leaving the state is open).
  frozen?: boolean;
  // Shown (exploring mode, not placing a pin) when given.
  onAllStates?: () => void;
  // Called when the person tries to zoom out past exploring mode's floor.
  onZoomOutBlocked?: () => void;
}) {
  const verified = waterbodies.filter((w) => w.data_tier !== "osm");
  const osm = waterbodies.filter((w) => w.data_tier === "osm");
  const clusterLabel = useT().map.clusterLakes;
  const iconFor = useCallback(
    (cluster: { getChildCount: () => number }) => clusterIcon(cluster, clusterLabel),
    [clusterLabel],
  );

  return (
    <MapContainer
      center={initialView?.center ?? US_CENTER}
      zoom={initialView?.zoom ?? US_ZOOM}
      minZoom={MAP_MIN_ZOOM}
      maxZoom={MAP_MAX_ZOOM}
      scrollWheelZoom
      // A hard edge at the state's border (ViewLimits), not a rubber band.
      maxBoundsViscosity={1}
      className={placing ? "is-placing" : undefined}
      // Moved to the bottom right: the search bar sits in the top left,
      // where Leaflet puts the zoom buttons by default.
      zoomControl={false}
      style={{ height: "100%", width: "100%" }}
    >
      <BaseMap />
      <ZoomControl position="bottomright" />
      {mode === "exploring" && !placing && onAllStates && <AllStatesControl onClick={onAllStates} />}
      {mode === "exploring" && !placing && onZoomOutBlocked && <ZoomOutLimit onBlocked={onZoomOutBlocked} />}
      {/* Only at country scale, and never while placing a pin: a tap then
          means "here", not "go to this state". */}
      {mode === "national" && !placing && <StatesLayer covered={coveredStates} onEnter={onEnterState} />}
      <ViewLimits mode={mode} region={region} fit={fitRegion} skipFitOnMount={initialView !== null} />
      <Freeze frozen={frozen} />
      {mode === "exploring" && region && <RegionMask region={region} />}
      <ViewportWatcher onChange={onViewportChange} loadOnMount={initialView !== null} />
      <FlyToFocus focusPoint={focusPoint} skipOnMount={initialView !== null} />

      {/* No lake or pin layers at all on the national map, not just empty
          ones. Besides being what national mode means, removing the cluster
          group outright matters: emptying it in the same instant the map
          jumps back to the whole country left behind a ghost "0" cluster
          bubble that could be panned into view. */}
      {mode === "exploring" && (
        <>
        {you && <YouAreHere at={you} region={region} />}
        {/* Verified lakes are never clustered: there are few of them and
            they're the ones this app can actually say something about.
            That is a claim about data volume, not a rule of the map. Tried
            against a synthetic 5,000 verified lakes, a zoomed-out view of the
            whole country becomes an unreadable clump of pins. With dozens (a
            state's worth of curated lakes) it is fine; once a wide view can
            hold a few hundred, cluster them below some zoom. */}
        {verified.map((lake) => (
          <LakeMarker key={lake.id} lake={lake} onSelect={onSelect} region={region} />
        ))}

        {/* OSM lakes can number in the thousands in one view; clustering
            keeps the map readable and the browser responsive. A new group per
            state: Leaflet.markercluster builds its zoom levels once, from the
            map's limits when it is added, and ViewLimits changes those limits
            with the state. A group built before a state raised the floor
            (Use my location, a search) filed a lake with no neighbour under a
            level it never draws, so a lone lake had no marker. */}
        <MarkerClusterGroup
          key={region?.code ?? "no-state"}
          chunkedLoading
          showCoverageOnHover={false}
          iconCreateFunction={iconFor}
        >
          {osm.map((lake) => (
            <LakeMarker key={lake.id} lake={lake} onSelect={onSelect} region={region} />
          ))}
        </MarkerClusterGroup>

        <ShopMarkers shops={shops} region={region} />
        <WaterGroupMarkers groups={groups} />
        <PinMarkers pins={pins} />
        </>
      )}
      {placing && onPlace && <PlaceOnClick onPlace={onPlace} />}
      {draft && onPlace && <DraftMarker point={draft} onMove={onPlace} label={draftLabel} off={draftOff} />}
    </MapContainer>
  );
}
