"use client";

import "leaflet/dist/leaflet.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.Default.css";
import L from "leaflet";
import { useEffect, useRef } from "react";
import { MapContainer, Marker, Popup, TileLayer, ZoomControl, useMap, useMapEvents } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

import type { PinSummary, WaterbodyListItem } from "@/lib/api/types";
import { TILE_ATTRIBUTION, TILE_URL } from "@/lib/map/tiles";
import { DraftMarker, PinMarkers, PlaceOnClick } from "./PinLayer";
import { StatesLayer } from "./StatesLayer";
import { US_CENTER, US_ZOOM } from "./zoomPolicy";

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
  const skip = useRef(skipOnMount);
  useEffect(() => {
    if (skip.current) {
      skip.current = false;
      return;
    }
    if (focusPoint) map.flyTo([focusPoint.latitude, focusPoint.longitude], SEARCH_ZOOM);
  }, [focusPoint, map]);
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
}) {
  const verified = waterbodies.filter((w) => w.data_tier !== "osm");
  const osm = waterbodies.filter((w) => w.data_tier === "osm");

  return (
    <MapContainer
      center={initialView?.center ?? US_CENTER}
      zoom={initialView?.zoom ?? US_ZOOM}
      scrollWheelZoom
      className={placing ? "is-placing" : undefined}
      // Moved to the bottom right: the search bar sits in the top left,
      // where Leaflet puts the zoom buttons by default.
      zoomControl={false}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} />
      <ZoomControl position="bottomright" />
      {/* Hidden while placing a pin: a tap then means "here", not "go to
          this state". */}
      {!placing && <StatesLayer covered={coveredStates} />}
      <ViewportWatcher onChange={onViewportChange} loadOnMount={initialView !== null} />
      <FlyToFocus focusPoint={focusPoint} skipOnMount={initialView !== null} />

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
      {placing && onPlace && <PlaceOnClick onPlace={onPlace} />}
      {draft && onPlace && <DraftMarker point={draft} onMove={onPlace} />}
    </MapContainer>
  );
}
