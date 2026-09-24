"use client";

import "leaflet/dist/leaflet.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.Default.css";
import L from "leaflet";
import { useEffect, useRef } from "react";
import { MapContainer, Marker, Popup, TileLayer, ZoomControl, useMap, useMapEvents } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

import type { WaterbodyListItem } from "@/lib/api/types";

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

const TEXAS_CENTER: [number, number] = [31.4, -99.3];
const SEARCH_ZOOM = 11;
const VIEWPORT_DEBOUNCE_MS = 300;

export interface Viewport {
  bbox: string; // "west,south,east,north"
  zoom: number;
  center: [number, number];
}

/**
 * Reports the visible area after the user stops moving the map — and once
 * on mount, since Leaflet doesn't fire moveend for the initial view. The
 * parent decides what to load for it (MapView.tsx); this component only
 * says where the map is looking.
 */
function ViewportWatcher({ onChange }: { onChange: (viewport: Viewport) => void }) {
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
    onChange(read());
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
  return (
    <Marker
      position={[lake.latitude, lake.longitude]}
      icon={isOsm ? osmIcon : lake.field_tested ? fieldTestedIcon : defaultIcon}
      eventHandlers={{ click: () => onSelect(lake.id) }}
    >
      <Popup>
        <strong>{lake.name}</strong>
        {isOsm ? (
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            {lake.water_type === "pond" ? "Pond · " : ""}Unverified · from OpenStreetMap
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
}: {
  waterbodies: WaterbodyListItem[];
  onSelect: (id: number) => void;
  onViewportChange: (viewport: Viewport) => void;
  focusPoint?: { latitude: number; longitude: number } | null;
  // Where to open the map; defaults to the Texas overview.
  initialView?: { center: [number, number]; zoom: number } | null;
}) {
  const verified = waterbodies.filter((w) => w.data_tier !== "osm");
  const osm = waterbodies.filter((w) => w.data_tier === "osm");

  return (
    <MapContainer
      center={initialView?.center ?? TEXAS_CENTER}
      zoom={initialView?.zoom ?? 6}
      scrollWheelZoom
      // Moved to the bottom right: the search bar sits in the top left,
      // where Leaflet puts the zoom buttons by default.
      zoomControl={false}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ZoomControl position="bottomright" />
      <ViewportWatcher onChange={onViewportChange} />
      <FlyToFocus focusPoint={focusPoint} skipOnMount={initialView !== null} />

      {/* Verified lakes are never clustered: there are few of them and
          they're the ones this app can actually say something about. */}
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
    </MapContainer>
  );
}
