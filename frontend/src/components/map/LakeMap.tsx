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

function FitToMarkers({ waterbodies }: { waterbodies: WaterbodyListItem[] }) {
  const map = useMap();
  useEffect(() => {
    if (waterbodies.length === 0) return;
    const bounds = L.latLngBounds(waterbodies.map((w) => [w.latitude, w.longitude]));
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [waterbodies, map]);
  return null;
}

export default function LakeMap({
  waterbodies,
  onSelect,
}: {
  waterbodies: WaterbodyListItem[];
  onSelect: (id: number) => void;
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
      <FitToMarkers waterbodies={waterbodies} />
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
