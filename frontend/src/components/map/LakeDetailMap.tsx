"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { CircleMarker, MapContainer, Marker, Popup, ZoomControl, useMap, useMapEvents } from "react-leaflet";
import { type RefObject, useEffect, useRef, useState } from "react";

import { useT } from "@/i18n/client";
import { ApiError, getWaterbody } from "@/lib/api/client";
import type { WaterbodyDetail } from "@/lib/api/types";
import { MAP_MAX_ZOOM, MAP_MIN_ZOOM } from "@/lib/map/tiles";
import { BaseMap } from "./BaseMap";
import { waterIcon } from "./waterIcon";
import { type MapViewState, lakeDetailExitZoom } from "./zoomPolicy";

// Fish attractors: small teal dots, so they read as spots in the water and
// not as more places to park.
const ATTRACTOR_STYLE = { color: "#0f766e", fillColor: "#14b8a6", fillOpacity: 0.85, weight: 1 };

const FIT_PADDING = 60;
// Closer than this, a pond fills the screen and the land around it (roads,
// parking) is cut off.
const MAX_FIT_ZOOM = 16;

/** The zoom to open a lake at when nothing says how big it is: the zoom the
 * person was already at (they clicked it there, so it was in view), kept to
 * lake scale. It used to be a fixed 12, about 15 km across: a small lake
 * opened from close in became a dot in a city (2026-10-29 review). */
export function fallbackLakeZoom(fromZoom: number | undefined): number {
  return Math.min(MAX_FIT_ZOOM, Math.max(13, Math.round(fromZoom ?? 14)));
}

/** How many pixels at the bottom of the map `cover` hides: a phone's sheet
 * lies over the map; beside it (desktop) or below it, it hides nothing. */
export function coveredBottom(map: DOMRect, cover: DOMRect | null): number {
  if (!cover || cover.left >= map.right || cover.right <= map.left) return 0;
  return Math.max(0, Math.min(map.bottom, cover.bottom) - Math.max(map.top, cover.top));
}

/** Frames the lake, and reports the zoom it actually settles at so the
 * zoom-out exit below can be measured from there. Measured after the fit
 * rather than predicted before it: a prediction off by a level or two (the
 * map's size still settling, say) would close the lake the moment it opened
 * or never at all.
 *
 * What it frames, best first: the water's own box (`bounds`, from its
 * OpenStreetMap outline) with its entrances; else the entrances and its
 * centre; else the centre at the zoom the person came from.
 *
 * It frames the lake in the part of the map left visible above `cover`. On a
 * phone the lake's sheet rises over half the map as the lake opens, and a lake
 * centred on the whole map sat at the sheet's edge, half under it
 * (2026-10-29 review). */
function FitToLakeExtent({
  detail,
  fromZoom,
  cover,
  onSettled,
}: {
  detail: WaterbodyDetail;
  fromZoom?: number;
  cover?: RefObject<HTMLElement | null>;
  onSettled: (zoom: number) => void;
}) {
  const map = useMap();
  useEffect(() => {
    const points: [number, number][] = [
      [detail.latitude, detail.longitude],
      ...detail.access_points.map((ap) => [ap.latitude, ap.longitude] as [number, number]),
    ];
    if (detail.bounds) {
      const [south, west, north, east] = detail.bounds;
      points.push([south, west], [north, east]);
    }
    let cancelled = false;
    let fallback: ReturnType<typeof setTimeout> | undefined;
    const settle = () => onSettled(map.getZoom());
    const fit = () => {
      if (cancelled) return;
      const hidden = coveredBottom(
        map.getContainer().getBoundingClientRect(),
        cover?.current?.getBoundingClientRect() ?? null,
      );
      map.once("moveend", settle);
      // A fit that changes nothing may not move the map; don't wait forever.
      fallback = setTimeout(settle, 1500);
      if (points.length === 1) {
        // Just the centre: a fitBounds on one point zooms all the way in.
        // The map's middle moves down by half the hidden strip, so the lake
        // sits in the middle of what shows.
        const zoom = fallbackLakeZoom(fromZoom);
        map.setView(map.unproject(map.project(points[0], zoom).add([0, hidden / 2]), zoom), zoom);
      } else {
        map.fitBounds(L.latLngBounds(points), {
          paddingTopLeft: [FIT_PADDING, FIT_PADDING],
          paddingBottomRight: [FIT_PADDING, FIT_PADDING + hidden],
          maxZoom: MAX_FIT_ZOOM,
        });
      }
    };
    // Measured once the sheet has stopped rising, not partway up.
    const rising = cover?.current?.getAnimations?.() ?? [];
    Promise.all(rising.map((a) => a.finished)).then(fit, fit);
    return () => {
      cancelled = true;
      map.off("moveend", settle);
      clearTimeout(fallback);
    };
    // onSettled is a state setter wrapper from the parent; stable in effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail, map]);
  return null;
}

/**
 * Zooming out of a single lake means the person is looking around, not at
 * this lake: behave like "← All lakes" and hand back the current view, so the
 * overview opens right where they are instead of jumping. The threshold is
 * two steps out from where this lake settled (zoomPolicy.lakeDetailExitZoom),
 * so a big reservoir framed at zoom 9 doesn't exit on its own initial fit.
 */
function ExitWhenZoomedOut({
  exitBelow,
  onExit,
  onViewChange,
}: {
  exitBelow: number | null;
  onExit: (view: MapViewState) => void;
  onViewChange: (view: MapViewState) => void;
}) {
  const exited = useRef(false);
  const map = useMapEvents({
    moveend: () => onViewChange(read()),
    zoomend: () => {
      if (exited.current || exitBelow === null) return;
      if (map.getZoom() < exitBelow) {
        exited.current = true;
        onExit(read());
      }
    },
  });
  function read(): MapViewState {
    const c = map.getCenter();
    return { center: [c.lat, c.lng], zoom: map.getZoom() };
  }
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
export default function LakeDetailMap({
  waterbodyId,
  fromZoom,
  cover,
  onExit = () => undefined,
  onViewChange = () => undefined,
}: {
  waterbodyId: number;
  // The overview's zoom when the lake was clicked, for a lake with no
  // outline or entrances on file (fallbackLakeZoom).
  fromZoom?: number;
  // What may lie over the map's bottom: the lake's sheet on a phone.
  cover?: RefObject<HTMLElement | null>;
  // Zoomed out far enough to leave the lake: MapView returns to the overview.
  onExit?: (view: MapViewState) => void;
  // Where the map is looking, so "← All lakes" has somewhere to return to
  // when the lake was opened from a link rather than from the overview.
  onViewChange?: (view: MapViewState) => void;
}) {
  const t = useT().map;
  const lakeMapError = t.lakeMapError;
  const [detail, setDetail] = useState<WaterbodyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exitBelow, setExitBelow] = useState<number | null>(null);

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
        setError(e instanceof ApiError ? e.message : lakeMapError);
      });
    return () => {
      cancelled = true;
    };
  }, [waterbodyId, lakeMapError]);

  if (error) return <div className="map-loading panel-error">{error}</div>;
  if (!detail) return <div className="map-loading">{t.loadingLakeMap}</div>;

  const isClosed = detail.public_access_status === "closed";

  return (
    <MapContainer
      center={[detail.latitude, detail.longitude]}
      zoom={fallbackLakeZoom(fromZoom)}
      minZoom={MAP_MIN_ZOOM}
      maxZoom={MAP_MAX_ZOOM}
      scrollWheelZoom
      // Bottom right, clear of the "← All lakes" button (same fix as LakeMap).
      zoomControl={false}
      style={{ height: "100%", width: "100%" }}
    >
      <BaseMap />
      <ZoomControl position="bottomright" />
      <FitToLakeExtent
        detail={detail}
        fromZoom={fromZoom}
        cover={cover}
        onSettled={(z) => setExitBelow(lakeDetailExitZoom(z))}
      />
      <ExitWhenZoomedOut exitBelow={exitBelow} onExit={onExit} onViewChange={onViewChange} />
      <Marker position={[detail.latitude, detail.longitude]} icon={waterIcon()} title={`${detail.name}, ${t.lakeCenter}`}>
        <Popup>
          <strong>{detail.name}</strong>
          <div style={{ fontSize: 12, color: "#6b7280" }}>{t.lakeCenterApprox}</div>
          {isClosed && (
            <div style={{ fontSize: 12, color: "#991b1b", fontWeight: 600 }}>
              {t.closedToPublic}
            </div>
          )}
        </Popup>
      </Marker>
      {/* Never rendered for a closed lake — access_points is always empty
          there (see backend upsert_access_points), but the check is kept
          explicit rather than relying on that being true forever. */}
      {!isClosed &&
        detail.access_points.map((ap) => (
          <Marker
            key={ap.id}
            position={[ap.latitude, ap.longitude]}
            icon={waterIcon(ap.public_status === "confirmed_public" ? "access" : "osm")}
            title={`${ap.name}, ${ap.public_status === "confirmed_public" ? t.publicEntrance : t.unverifiedEntrance}`}
          >
            <Popup>
              <strong>{ap.name}</strong>
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                {t.accessTypes[ap.access_type] ?? ap.access_type.replace("_", " ")}
                {ap.parking ? t.parking : ""}
              </div>
              {ap.public_status === "osm_reported" && (
                <div style={{ fontSize: 12, color: "#92400e" }}>
                  {t.osmEntrance}
                </div>
              )}
            </Popup>
          </Marker>
        ))}
      {!isClosed &&
        (detail.fish_attractors ?? []).map((a) => (
          <CircleMarker key={`att-${a.id}`} center={[a.latitude, a.longitude]} radius={5} pathOptions={ATTRACTOR_STYLE}>
            <Popup>
              <strong>{t.attractor}</strong>
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                {a.attractor_type}
                {a.placed_year ? t.attractorPlaced(a.placed_year) : ""}
                {a.depth_ft ? t.attractorDepth(Math.round(a.depth_ft)) : ""}
              </div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>{t.attractorNote}</div>
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}
