"use client";

import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, TileLayer } from "react-leaflet";

import { catchIcon } from "@/components/map/catchIcon";
import { TILE_ATTRIBUTION, TILE_URL } from "@/lib/map/tiles";

/** Read-only map of one pin, for its detail page. */
export default function PinMiniMap({ lat, lng, isPrivate }: { lat: number; lng: number; isPrivate: boolean }) {
  return (
    <MapContainer center={[lat, lng]} zoom={13} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
      <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} />
      <Marker position={[lat, lng]} icon={catchIcon({ private: isPrivate })} />
    </MapContainer>
  );
}
