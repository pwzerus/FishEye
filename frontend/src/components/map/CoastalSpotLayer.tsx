"use client";

import L from "leaflet";
import { useCallback } from "react";
import { Marker, Popup } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

import { useT } from "@/i18n/client";
import type { CoastalSpot } from "@/lib/api/types";
import { MAP_POPUP_PAD } from "./popupPad";
import { directionsUrl } from "./shops";
import { displayLongitude, type StateRegion } from "./usStates";

// A rounded square in sea blue with a pier and a wave: not a lake's teardrop,
// a catch's badge or a shop's purple square (2026-11-18: the owner asked for
// the coast's public piers and jetties on the map).
const COAST_ICON = L.divIcon({
  className: "coast-marker-wrap",
  html: `<span class="coast-marker"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9h16"/><path d="M7 9v6M12 9v6M17 9v6"/><path d="M3 19c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0"/></svg></span>`,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
  popupAnchor: [0, -12],
});

/** Below this zoom, spots close together are one sea-blue square with
 * their number: Florida's Gulf coast has hundreds of ramps and piers, which
 * ran together into one blue line at zoom 8 (2026-11-18). */
export const COAST_UNCLUSTER_ZOOM = 12;

/** A sea-blue rounded square with the count: not a lake cluster's circle.
 * Its name for a screen reader says what it holds. */
export function coastClusterIcon(cluster: { getChildCount: () => number }, label: string) {
  const n = cluster.getChildCount();
  return L.divIcon({
    html: `<span class="coast-cluster">${n}<span class="sr-only"> ${label}</span></span>`,
    className: "coast-cluster-wrap",
    iconSize: L.point(34, 34),
  });
}

/** Saltwater piers, jetties, fishing spots and boat ramps in view, from
 * OpenStreetMap and, in California, CDFW's list of public piers. */
export function CoastalSpotMarkers({ spots, region = null }: { spots: CoastalSpot[]; region?: StateRegion | null }) {
  const t = useT().coast;
  const iconFor = useCallback(
    (cluster: { getChildCount: () => number }) => coastClusterIcon(cluster, t.cluster),
    [t.cluster],
  );
  return (
    // A new group per state, as for the lakes (LakeMap): the group builds its
    // zoom levels once, from the map's limits when it is added.
    <MarkerClusterGroup
      key={region?.code ?? "no-state"}
      chunkedLoading
      showCoverageOnHover={false}
      maxClusterRadius={45}
      disableClusteringAtZoom={COAST_UNCLUSTER_ZOOM}
      iconCreateFunction={iconFor}
    >
      {spots.map((s) => {
        const title = s.name ?? t[s.kind];
        return (
          <Marker
            key={s.id}
            position={[s.latitude, displayLongitude(s.longitude, region)]}
            icon={COAST_ICON}
            title={s.name ? `${s.name}, ${t[s.kind]}` : t[s.kind]}
            zIndexOffset={150}
          >
            <Popup className="shop-popup coast-popup" {...MAP_POPUP_PAD}>
              <div className="shop-pop">
                <span className="shop-pop-kind">{t[s.kind]}</span>
                <strong>{title}</strong>
                {s.operator && <span>{s.operator}</span>}
                {s.fee && <span>{t.fee(s.fee)}</span>}
                {s.opening_hours && <span className="shop-pop-hours">{t.hours(s.opening_hours)}</span>}
                {s.lit && <span>{t.lit}</span>}
                <span className="shop-pop-links">
                  <a href={directionsUrl(s)} target="_blank" rel="noreferrer">
                    {t.directions}
                  </a>
                  {s.website && (
                    <a href={s.website} target="_blank" rel="noreferrer nofollow">
                      {t.website}
                    </a>
                  )}
                </span>
                {s.no_license ? (
                  <span className="coast-pop-free">
                    {t.noLicense}
                    {s.license_note && <> {t.licenseNotes[s.license_note]}</>}
                  </span>
                ) : (
                  <span className="coast-pop-note">{t.checkRules}</span>
                )}
                <span className="coast-pop-sources">
                  {s.source === "cdfw" && (
                    <a className="shop-pop-source" href={s.source_url} target="_blank" rel="noreferrer">
                      {t.sourceCdfw}
                    </a>
                  )}
                  {s.osm_url && (
                    <a className="shop-pop-source" href={s.osm_url} target="_blank" rel="noreferrer">
                      {t.source}
                    </a>
                  )}
                </span>
              </div>
            </Popup>
          </Marker>
        );
      })}
    </MarkerClusterGroup>
  );
}
