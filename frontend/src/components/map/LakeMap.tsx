"use client";

import "leaflet/dist/leaflet.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.Default.css";
import L from "leaflet";
import { useEffect, useRef } from "react";
import { MapContainer, Marker, Popup, ZoomControl, useMap, useMapEvents } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

import type { PinSummary, WaterbodyListItem } from "@/lib/api/types";
import { MAP_MAX_ZOOM, MAP_MIN_ZOOM } from "@/lib/map/tiles";
import { BaseMap } from "./BaseMap";
import { DraftMarker, PinMarkers, PlaceOnClick } from "./PinLayer";
import { StatesLayer } from "./StatesLayer";
import { US_CENTER, US_ZOOM, type MapMode, zoomLimitsFor } from "./zoomPolicy";

// Leaflet's default marker icons reference image files by relative URL,
// which breaks under bundlers (webpack rewrites the paths). Point them at
// CDN-hosted copies instead of shipping our own icon assets for the MVP.
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const fieldTestedIcon = L.icon({
  ...defaultIcon.options,
  className: "field-tested-marker",
});

// Same pin, greyed out by CSS: a lake OpenStreetMap knows about but this
// app has no verified information on. Deliberately less eye-catching than
// a verified lake's pin.
const osmIcon = L.icon({
  ...defaultIcon.options,
  className: "osm-marker",
});

// An unverified lake that has fish records (GBIF): tinted amber so people can
// find the lakes FishEye knows *something* about, while staying distinct
// from a verified lake's blue pin. See docs/adr/0012-gbif-reported-species.md.
const reportedIcon = L.icon({
  ...defaultIcon.options,
  className: "osm-marker-reported",
});

const SEARCH_ZOOM = 11;
const VIEWPORT_DEBOUNCE_MS = 300;

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
 * Flies to the last searched / located point. The map no longer re-fits
 * itself to whatever markers are loaded: markers are now *loaded from* the
 * viewport, so fitting the viewport to the markers would loop.
 */
function FlyToFocus({
  focusPoint,
  skipOnMount,
}: {
  focusPoint: { latitude: number; longitude: number } | null;
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
    map.flyTo([focusPoint.latitude, focusPoint.longitude], SEARCH_ZOOM);
  }, [focusPoint, map]);
  return null;
}

/**
 * Applies the zoom limits of the current mode (zoomPolicy.ts), and on the
 * way back to national mode re-centres on the country. Rendered before
 * FitToBounds and FlyToFocus so that, when a state click or a search switches
 * the mode and asks for a new view in the same update, the ceiling is lifted
 * before the map flies in rather than clamping the flight at country scale.
 *
 * Order matters inside each branch too: Leaflet rejects a minimum above the
 * current maximum, so the limit that moves outward is set first.
 */
function ModeLimits({ mode }: { mode: MapMode }) {
  const map = useMap();
  const previous = useRef<MapMode | null>(null);
  useEffect(() => {
    const { min, max } = zoomLimitsFor(mode);
    // Only when they change. Re-applying a floor the map already has is not
    // a no-op in Leaflet: setMinZoom snaps any map below it up to it, and if
    // that lands mid-flight (React re-runs mount effects in development, and
    // the fly-to for a search or ?at= link starts in the same update) it
    // cancels the flight and strands the map at state scale.
    if (map.getMinZoom() === min && map.getMaxZoom() === max && previous.current === mode) return;
    if (mode === "national") {
      map.setMinZoom(min);
      if (previous.current === "exploring") map.setView(US_CENTER, US_ZOOM, { animate: false });
      map.setMaxZoom(max);
    } else {
      map.setMaxZoom(max);
      map.setMinZoom(min);
    }
    previous.current = mode;
  }, [map, mode]);
  return null;
}

/** Fits the map to a chosen state's outline (StatesLayer → MapView).
 *
 * Acts only on a state it hasn't fitted yet. When the map is remounted to
 * restore a view (coming back from a lake), the state picked earlier is still
 * the current `bounds`, and re-fitting to it would throw the person from where
 * they zoomed out of the lake back to the whole state. Tracking the applied
 * target, rather than skipping "the first run", also survives React running
 * mount effects twice in development. */
function FitToBounds({ bounds, skipOnMount }: { bounds: L.LatLngBounds | null; skipOnMount: boolean }) {
  const map = useMap();
  const applied = useRef<L.LatLngBounds | null>(skipOnMount ? bounds : null);
  useEffect(() => {
    if (!bounds || bounds === applied.current) return;
    applied.current = bounds;
    map.fitBounds(bounds, { padding: [24, 24] });
  }, [bounds, map]);
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
  const latest = useRef(onClick);
  useEffect(() => {
    latest.current = onClick;
  });
  useEffect(() => {
    const control = new L.Control({ position: "bottomright" });
    control.onAdd = () => {
      const button = L.DomUtil.create("button", "map-toggle active all-states-control");
      button.type = "button";
      button.title = "Back to the map of all states";
      button.innerHTML =
        '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
        '<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z M9 3v15 M15 6v15" stroke-linejoin="round"/></svg>' +
        "<span>All states</span>";
      L.DomEvent.disableClickPropagation(button);
      L.DomEvent.on(button, "click", () => latest.current());
      return button;
    };
    control.addTo(map);
    return () => {
      control.remove();
    };
  }, [map]);
  return null;
}

function LakeMarker({ lake, onSelect }: { lake: WaterbodyListItem; onSelect: (id: number) => void }) {
  const isOsm = lake.data_tier === "osm";
  const reported = lake.reported_species_count ?? 0;
  const icon = isOsm
    ? reported > 0
      ? reportedIcon
      : osmIcon
    : lake.field_tested
      ? fieldTestedIcon
      : defaultIcon;
  return (
    <Marker
      position={[lake.latitude, lake.longitude]}
      icon={icon}
      eventHandlers={{ click: () => onSelect(lake.id) }}
    >
      <Popup>
        <strong>{lake.name}</strong>
        {isOsm ? (
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            {lake.water_type === "pond" ? "Pond · " : ""}Unverified · from OpenStreetMap
            {reported > 0 && (
              <div style={{ color: "#92400e" }}>
                {reported} fish species on record
              </div>
            )}
          </div>
        ) : (
          lake.field_tested && (
            <div style={{ fontSize: 12, color: "#2563eb" }}>Friend field-tested</div>
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
  initialView = null,
  pins = [],
  placing = false,
  draft = null,
  onPlace,
  coveredStates = null,
  mode = "exploring",
  onEnterState = () => undefined,
  focusBounds = null,
  onAllStates,
}: {
  waterbodies: WaterbodyListItem[];
  onSelect: (id: number) => void;
  onViewportChange: (viewport: Viewport) => void;
  focusPoint?: { latitude: number; longitude: number } | null;
  // Where to open the map; defaults to the whole country, where the states
  // layer is the way in.
  initialView?: { center: [number, number]; zoom: number } | null;
  // Community pins in view, and the "add a pin" mode (MapView.tsx).
  pins?: PinSummary[];
  placing?: boolean;
  draft?: { latitude: number; longitude: number } | null;
  onPlace?: (lat: number, lng: number) => void;
  // State codes with lakes on file; null while unknown (StatesLayer.tsx).
  coveredStates?: Set<string> | null;
  // National (states only, zoom locked) or exploring — zoomPolicy.ts.
  mode?: MapMode;
  onEnterState?: (bounds: L.LatLngBounds) => void;
  // A state the person just picked, to fit the map to.
  focusBounds?: L.LatLngBounds | null;
  // Shown (exploring mode, not placing a pin) when given.
  onAllStates?: () => void;
}) {
  const verified = waterbodies.filter((w) => w.data_tier !== "osm");
  const osm = waterbodies.filter((w) => w.data_tier === "osm");

  return (
    <MapContainer
      center={initialView?.center ?? US_CENTER}
      zoom={initialView?.zoom ?? US_ZOOM}
      minZoom={MAP_MIN_ZOOM}
      maxZoom={MAP_MAX_ZOOM}
      scrollWheelZoom
      className={placing ? "is-placing" : undefined}
      // Moved to the bottom right: the search bar sits in the top left,
      // where Leaflet puts the zoom buttons by default.
      zoomControl={false}
      style={{ height: "100%", width: "100%" }}
    >
      <BaseMap />
      <ZoomControl position="bottomright" />
      {mode === "exploring" && !placing && onAllStates && <AllStatesControl onClick={onAllStates} />}
      {/* Only at country scale, and never while placing a pin: a tap then
          means "here", not "go to this state". */}
      {mode === "national" && !placing && <StatesLayer covered={coveredStates} onEnter={onEnterState} />}
      <ModeLimits mode={mode} />
      <FitToBounds bounds={focusBounds} skipOnMount={initialView !== null} />
      <ViewportWatcher onChange={onViewportChange} loadOnMount={initialView !== null} />
      <FlyToFocus focusPoint={focusPoint} skipOnMount={initialView !== null} />

      {/* No lake or pin layers at all on the national map, not just empty
          ones. Besides being what national mode means, removing the cluster
          group outright matters: emptying it in the same instant the map
          jumps back to the whole country left behind a ghost "0" cluster
          bubble that could be panned into view. */}
      {mode === "exploring" && (
        <>
        {/* Verified lakes are never clustered: there are few of them and
            they're the ones this app can actually say something about.
            That is a claim about data volume, not a rule of the map. Tried
            against a synthetic 5,000 verified lakes, a zoomed-out view of the
            whole country becomes an unreadable clump of pins. With dozens (a
            state's worth of curated lakes) it is fine; once a wide view can
            hold a few hundred, cluster them below some zoom. */}
        {verified.map((lake) => (
          <LakeMarker key={lake.id} lake={lake} onSelect={onSelect} />
        ))}

        {/* OSM lakes can number in the thousands in one view; clustering
            keeps the map readable and the browser responsive. */}
        <MarkerClusterGroup chunkedLoading showCoverageOnHover={false}>
          {osm.map((lake) => (
            <LakeMarker key={lake.id} lake={lake} onSelect={onSelect} />
          ))}
        </MarkerClusterGroup>

        <PinMarkers pins={pins} />
        </>
      )}
      {placing && onPlace && <PlaceOnClick onPlace={onPlace} />}
      {draft && onPlace && <DraftMarker point={draft} onMove={onPlace} />}
    </MapContainer>
  );
}
