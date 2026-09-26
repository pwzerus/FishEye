"use client";

import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, TileLayer } from "react-leaflet";

import { catchIcon } from "@/components/map/catchIcon";

/** Read-only map of one pin, for its detail page. */
export default function PinMiniMap({ lat, lng, isPrivate }: { lat: number; lng: number; isPrivate: boolean }) {
  return (
    <MapContainer center={[lat, lng]} zoom={13} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker position={[lat, lng]} icon={catchIcon({ private: isPrivate })} />
    </MapContainer>
  );
}
