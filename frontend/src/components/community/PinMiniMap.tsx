"use client";

import "leaflet/dist/leaflet.css";
import { MapContainer, Marker } from "react-leaflet";

import { catchIcon } from "@/components/map/catchIcon";
import { BaseMap } from "@/components/map/BaseMap";
import type { PinPointKind } from "@/lib/api/types";
import { MAP_MAX_ZOOM, MAP_MIN_ZOOM } from "@/lib/map/tiles";

// A point that stands for a lake, a river's reach or a county isn't a spot
// to zoom in on.
const ZOOM: Record<PinPointKind, number> = { exact: 13, lake: 12, river: 11, county: 9, area: 10 };

/** Read-only map of one pin, for its detail page. */
export default function PinMiniMap({
  lat,
  lng,
  isPrivate,
  place = "exact",
}: {
  lat: number;
  lng: number;
  isPrivate: boolean;
  place?: PinPointKind;
}) {
  return (
    <MapContainer
      center={[lat, lng]}
      zoom={ZOOM[place]}
      minZoom={MAP_MIN_ZOOM}
      maxZoom={MAP_MAX_ZOOM}
      scrollWheelZoom={false}
      style={{ height: "100%", width: "100%" }}
    >
      <BaseMap />
      <Marker position={[lat, lng]} icon={catchIcon({ private: isPrivate, approx: place !== "exact" })} />
    </MapContainer>
  );
}
