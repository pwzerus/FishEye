"use client";

import L from "leaflet";
import { Marker, Popup } from "react-leaflet";

import type { Shop } from "@/lib/api/types";
import { SHOP_KIND_LABEL, directionsUrl } from "./shops";
import { displayLongitude, type StateRegion } from "./usStates";

// A small square badge with a hook: not a lake's teardrop or a catch's round
// badge, so a shop never reads as water or as a report.
const SHOP_ICON = L.divIcon({
  className: "shop-marker-wrap",
  html: `<span class="shop-marker"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M14 3v11a4 4 0 0 1-8 0v-2"/><path d="M6 12l-2 2"/><circle cx="14" cy="3" r="1"/></svg></span>`,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
  popupAnchor: [0, -12],
});

/** Bait and tackle shops in view, from OpenStreetMap. */
export function ShopMarkers({ shops, region = null }: { shops: Shop[]; region?: StateRegion | null }) {
  return (
    <>
      {shops.map((s) => (
        <Marker
          key={s.id}
          position={[s.latitude, displayLongitude(s.longitude, region)]}
          icon={SHOP_ICON}
          // Leaflet gives a div icon no alt; its title is the marker's name.
          title={`${s.name}, ${SHOP_KIND_LABEL[s.kind]}`}
          zIndexOffset={200}
        >
          <Popup className="shop-popup">
            <div className="shop-pop">
              <span className="shop-pop-kind">{SHOP_KIND_LABEL[s.kind]}</span>
              <strong>{s.name}</strong>
              {s.address && <span>{s.address}</span>}
              {s.opening_hours && <span className="shop-pop-hours">Hours: {s.opening_hours}</span>}
              <span className="shop-pop-links">
                <a href={directionsUrl(s)} target="_blank" rel="noreferrer">
                  Directions
                </a>
                {s.phone && <a href={`tel:${s.phone.replace(/[^\d+]/g, "")}`}>Call</a>}
                {s.website && (
                  <a href={s.website} target="_blank" rel="noreferrer nofollow">
                    Website
                  </a>
                )}
              </span>
              <a className="shop-pop-source" href={s.osm_url} target="_blank" rel="noreferrer">
                © OpenStreetMap contributors · check hours before you go
              </a>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}
