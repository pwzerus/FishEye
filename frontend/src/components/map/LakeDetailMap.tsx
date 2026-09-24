"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, ZoomControl, useMap } from "react-leaflet";
import { useEffect, useState } from "react";

import { ApiError, getWaterbody } from "@/lib/api/client";
import type { WaterbodyDetail } from "@/lib/api/types";

// Same CDN icon approach as LakeMap.tsx (see its comment) — a distinct
// color for access points so they read as a different kind of pin than
// the lake-centroid marker, without pulling in a whole icon set for two
// colors.
const lakeCenterIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const accessPointIcon = L.icon({
  ...lakeCenterIcon.options,
  className: "access-point-marker",
});

function FitToLakeExtent({ detail }: { detail: WaterbodyDetail }) {
  const map = useMap();
  useEffect(() => {
    const points: [number, number][] = [
      [detail.latitude, detail.longitude],
      ...detail.access_points.map((ap) => [ap.latitude, ap.longitude] as [number, number]),
    ];
    if (points.length === 1) {
      // Just the centroid — a fitBounds on a single point zooms in far
      // too aggressively (or not at all), so set an explicit lake-scale
      // zoom instead.
      map.setView(points[0], 12);
      return;
    }
    map.fitBounds(L.latLngBounds(points), { padding: [60, 60] });
  }, [detail, map]);
  return null;
}

/**
 * The zoomed-in, single-lake map shown after clicking a marker on the
 * statewide LakeMap. Deliberately fetches its own WaterbodyDetail rather
 * than sharing WaterbodyPanel's — same pattern as WeatherRecommendations,
 * which also fetches independently of the panel that renders it. That
 * duplicates one request per lake selection, which is an acceptable
 * tradeoff for a portfolio demo's data volume; a shared cache would be
 * the right fix if this ever needs to scale.
 *
 * This is also the intended home for future per-lake overlays — the AI
 * Advisor's cited spots and the lightweight community pins both need a
 * map scoped to one lake, not the statewide view, which is the whole
 * reason this component exists rather than just re-centering LakeMap.
 */
export default function LakeDetailMap({ waterbodyId }: { waterbodyId: number }) {
  const [detail, setDetail] = useState<WaterbodyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // No reset of detail/error at the top of this effect: MapView mounts
    // this component with `key={selectedId}`, so a new lake selection is
    // always a fresh instance (initial state already null), not a
    // re-render of the same one — resetting here would just be a
    // synchronous setState in an effect body for no reason.
    let cancelled = false;
    getWaterbody(waterbodyId)
      .then((d) => {
        if (cancelled) return;
        setDetail(d);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : "Could not load this lake's map.");
      });
    return () => {
      cancelled = true;
    };
  }, [waterbodyId]);

  if (error) return <div className="map-loading panel-error">{error}</div>;
  if (!detail) return <div className="map-loading">Loading lake map…</div>;

  const isClosed = detail.public_access_status === "closed";

  return (
    <MapContainer
      center={[detail.latitude, detail.longitude]}
      zoom={12}
      scrollWheelZoom
      // Bottom right, clear of the "← All lakes" button (same fix as LakeMap).
      zoomControl={false}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ZoomControl position="bottomright" />
      <FitToLakeExtent detail={detail} />
      <Marker position={[detail.latitude, detail.longitude]} icon={lakeCenterIcon}>
        <Popup>
          <strong>{detail.name}</strong>
          <div style={{ fontSize: 12, color: "#6b7280" }}>lake center (approximate)</div>
          {isClosed && (
            <div style={{ fontSize: 12, color: "#991b1b", fontWeight: 600 }}>
              Closed to the public
            </div>
          )}
        </Popup>
      </Marker>
      {/* Never rendered for a closed lake — access_points is always empty
          there (see backend upsert_access_points), but the check is kept
          explicit rather than relying on that being true forever. */}
      {!isClosed &&
        detail.access_points.map((ap) => (
          <Marker key={ap.id} position={[ap.latitude, ap.longitude]} icon={accessPointIcon}>
            <Popup>
              <strong>{ap.name}</strong>
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                {ap.access_type.replace("_", " ")}
                {ap.parking ? ", parking available" : ""}
              </div>
              {ap.public_status === "osm_reported" && (
                <div style={{ fontSize: 12, color: "#92400e" }}>
                  Reported on OpenStreetMap, not verified. Check it&apos;s public before you go.
                </div>
              )}
            </Popup>
          </Marker>
        ))}
    </MapContainer>
  );
}
