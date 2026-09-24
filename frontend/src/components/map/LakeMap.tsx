"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";

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

const TEXAS_CENTER: [number, number] = [31.4, -99.3];

/**
 * Two different reasons the view might need to move, handled by one effect
 * so they can't fight each other over who owns the map's position:
 *
 * - Markers present -> fit bounds to them, same as always.
 * - No markers, but the user just searched/located a point that came back
 *   with nothing nearby -> fly there anyway rather than leaving the map
 *   sitting on the old view. An empty result is a real, honest answer
 *   ("nothing on file here yet" — see MapView's own empty-state message),
 *   not a reason to pretend the search didn't happen.
 */
function FitToView({
  waterbodies,
  focusPoint,
}: {
  waterbodies: WaterbodyListItem[];
  focusPoint: { latitude: number; longitude: number } | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (waterbodies.length > 0) {
      const bounds = L.latLngBounds(waterbodies.map((w) => [w.latitude, w.longitude]));
      map.fitBounds(bounds, { padding: [40, 40] });
    } else if (focusPoint) {
      map.flyTo([focusPoint.latitude, focusPoint.longitude], 10);
    }
  }, [waterbodies, focusPoint, map]);
  return null;
}

export default function LakeMap({
  waterbodies,
  onSelect,
  focusPoint = null,
}: {
  waterbodies: WaterbodyListItem[];
  onSelect: (id: number) => void;
  // The last point a search or "use my location" resolved to — used only
  // when there are no markers to fit bounds to (see FitToView above).
  focusPoint?: { latitude: number; longitude: number } | null;
}) {
  return (
    <MapContainer
      center={TEXAS_CENTER}
      zoom={6}
      scrollWheelZoom
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToView waterbodies={waterbodies} focusPoint={focusPoint} />
      {waterbodies.map((w) => (
        <Marker
          key={w.id}
          position={[w.latitude, w.longitude]}
          icon={w.field_tested ? fieldTestedIcon : defaultIcon}
          eventHandlers={{ click: () => onSelect(w.id) }}
        >
          <Popup>
            <strong>{w.name}</strong>
            {w.field_tested && (
              <div style={{ fontSize: 12, color: "#2563eb" }}>Friend field-tested</div>
            )}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
