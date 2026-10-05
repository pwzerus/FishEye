"use client";

import "leaflet/dist/leaflet.css";
import { MapContainer, Marker } from "react-leaflet";

import { catchIcon } from "@/components/map/catchIcon";
import { BaseMap } from "@/components/map/BaseMap";
import { MAP_MAX_ZOOM, MAP_MIN_ZOOM } from "@/lib/map/tiles";

/** Read-only map of one pin, for its detail page. */
export default function PinMiniMap({ lat, lng, isPrivate }: { lat: number; lng: number; isPrivate: boolean }) {
  return (
    <MapContainer
      center={[lat, lng]}
      zoom={13}
      minZoom={MAP_MIN_ZOOM}
      maxZoom={MAP_MAX_ZOOM}
      scrollWheelZoom={false}
      style={{ height: "100%", width: "100%" }}
    >
      <BaseMap />
      <Marker position={[lat, lng]} icon={catchIcon({ private: isPrivate })} />
    </MapContainer>
  );
}
