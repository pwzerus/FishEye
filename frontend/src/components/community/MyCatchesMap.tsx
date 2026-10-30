"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import Link from "next/link";
import { useEffect } from "react";
import { MapContainer, Marker, Popup, useMap } from "react-leaflet";

import { BaseMap } from "@/components/map/BaseMap";
import { catchIcon } from "@/components/map/catchIcon";
import { useT } from "@/i18n/client";
import type { PinSummary } from "@/lib/api/types";
import { MAP_MAX_ZOOM, MAP_MIN_ZOOM } from "@/lib/map/tiles";

function FitAll({ pins }: { pins: PinSummary[] }) {
  const map = useMap();
  useEffect(() => {
    if (pins.length === 0) return;
    const bounds = L.latLngBounds(pins.map((p) => [p.latitude, p.longitude] as [number, number]));
    map.fitBounds(bounds, { padding: [28, 28], maxZoom: 12, animate: false });
  }, [map, pins]);
  return null;
}

/** Everywhere you've pinned a catch, on one map (the account page). */
export default function MyCatchesMap({ pins }: { pins: PinSummary[] }) {
  const t = useT().catch;
  return (
    <MapContainer
      center={[39.5, -98.35]}
      zoom={4}
      minZoom={MAP_MIN_ZOOM}
      maxZoom={MAP_MAX_ZOOM}
      scrollWheelZoom={false}
      style={{ height: "100%", width: "100%" }}
    >
      <BaseMap />
      <FitAll pins={pins} />
      {pins.map((p) => (
        <Marker
          key={p.id}
          position={[p.latitude, p.longitude]}
          icon={catchIcon({ private: p.visibility === "private", mine: true })}
          title={p.title}
        >
          <Popup className="catch-popup">
            <div className="catch-pop">
              {p.thumb_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={p.thumb_url} alt="" />
              )}
              <strong>{p.title}</strong>
              <span>
                {p.species_label ?? t.catch}
                {p.water ? ` · ${p.water.name}` : p.lake ? ` · ${p.lake.name}` : ""}
                {p.visibility === "private" ? ` · ${t.onlyYouShort}` : ""}
              </span>
              <Link href={`/community/${p.id}`}>{t.openShort}</Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
