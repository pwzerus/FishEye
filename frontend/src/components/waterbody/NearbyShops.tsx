"use client";

import { useEffect, useState } from "react";

import { SHOP_KIND_LABEL, directionsUrl } from "@/components/map/shops";
import { listShopsNear } from "@/lib/api/client";
import type { Shop } from "@/lib/api/types";

export function miles(km: number): string {
  const tenths = Math.round(km * 6.21371) / 10;
  return tenths < 10 ? `${tenths.toFixed(1)} mi` : `${Math.round(tenths)} mi`;
}

/** The closest bait and tackle shops to a lake (OpenStreetMap), on its
 * Entrances tab: where to stop on the way. Nothing is shown when none is
 * mapped within reach. */
export function NearbyShops({ latitude, longitude }: { latitude: number; longitude: number }) {
  const [shops, setShops] = useState<Shop[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    listShopsNear(latitude, longitude)
      .then((s) => !cancelled && setShops(s))
      .catch(() => !cancelled && setShops([]));
    return () => {
      cancelled = true;
    };
  }, [latitude, longitude]);

  if (!shops || shops.length === 0) return null;
  return (
    <div className="nearby-shops">
      <h3>Bait &amp; tackle nearby</h3>
      <ul>
        {shops.map((s) => (
          <li key={s.id}>
            <span className="legend-shop" aria-hidden="true" />
            <span className="nearby-shop-body">
              <strong>{s.name}</strong>
              <span className="muted">
                {SHOP_KIND_LABEL[s.kind]}
                {s.distance_km != null && <> · {miles(s.distance_km)} away</>}
              </span>
            </span>
            <a href={directionsUrl(s)} target="_blank" rel="noreferrer" className="text-link">
              Directions
            </a>
          </li>
        ))}
      </ul>
      <p className="nearby-shops-credit muted">Straight-line distance · © OpenStreetMap contributors · check hours before you go</p>
    </div>
  );
}
