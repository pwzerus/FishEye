"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { Marker, Popup, useMapEvents } from "react-leaflet";
import type { Marker as LeafletMarker } from "leaflet";

import { catchIcon } from "./catchIcon";
import type { PinSummary } from "@/lib/api/types";

/** Community pins on the main map, each with a small preview popup. */
export function PinMarkers({ pins }: { pins: PinSummary[] }) {
  return (
    <>
      {pins.map((p) => (
        <Marker
          key={p.id}
          position={[p.latitude, p.longitude]}
          icon={catchIcon({ private: p.visibility === "private", mine: p.is_mine })}
          zIndexOffset={500}
        >
          <Popup className="catch-popup">
            <div className="catch-pop">
              {p.thumb_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={p.thumb_url} alt="" />
              )}
              <strong>{p.title}</strong>
              <span>
                {p.species_label ?? "Catch"} · {p.is_mine ? "you" : p.author.display_name}
                {p.visibility === "private" ? " · only you" : ""}
              </span>
              <Link href={`/community/${p.id}`}>Open pin →</Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

/** While placing a pin: a click drops (or moves) the draft pin. */
export function PlaceOnClick({ onPlace }: { onPlace: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: (e) => onPlace(e.latlng.lat, e.latlng.lng),
  });
  return null;
}

/** The pin being created: draggable, so it can be nudged onto the exact spot. */
export function DraftMarker({
  point,
  onMove,
}: {
  point: { latitude: number; longitude: number };
  onMove: (lat: number, lng: number) => void;
}) {
  const ref = useRef<LeafletMarker>(null);
  useEffect(() => {
    ref.current?.getElement()?.classList.add("draft-drop");
  }, []);
  return (
    <Marker
      ref={ref}
      position={[point.latitude, point.longitude]}
      icon={catchIcon({ draft: true })}
      draggable
      zIndexOffset={1000}
      eventHandlers={{
        dragend: () => {
          const ll = ref.current?.getLatLng();
          if (ll) onMove(ll.lat, ll.lng);
        },
      }}
    />
  );
}
