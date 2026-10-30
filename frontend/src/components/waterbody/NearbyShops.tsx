"use client";

import { useEffect, useState } from "react";

import { directionsUrl } from "@/components/map/shops";
import { useT } from "@/i18n/client";
import { listShopsNear } from "@/lib/api/client";
import type { Shop } from "@/lib/api/types";

/** "4.2" or "12": miles, to a tenth under ten. */
export function milesNumber(km: number): string {
  const tenths = Math.round(km * 6.21371) / 10;
  return tenths < 10 ? tenths.toFixed(1) : String(Math.round(tenths));
}

export function miles(km: number): string {
  return `${milesNumber(km)} mi`;
}

/** The closest bait and tackle shops to a lake (OpenStreetMap), on its
 * Entrances tab: where to stop on the way. Nothing is shown when none is
 * mapped within reach. */
export function NearbyShops({ latitude, longitude }: { latitude: number; longitude: number }) {
  const [shops, setShops] = useState<Shop[] | null>(null);
  const all = useT();

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
      <h3>{all.lake.shopsNearby}</h3>
      <ul>
        {shops.map((s) => (
          <li key={s.id}>
            <span className="legend-shop" aria-hidden="true" />
            <span className="nearby-shop-body">
              <strong>{s.name}</strong>
              <span className="muted">
                {all.shops[s.kind]}
                {s.distance_km != null && all.lake.away(all.common.miles(milesNumber(s.distance_km)))}
              </span>
            </span>
            <a href={directionsUrl(s)} target="_blank" rel="noreferrer" className="text-link">
              {all.shops.directions}
            </a>
          </li>
        ))}
      </ul>
      <p className="nearby-shops-credit muted">{all.lake.shopsCredit}</p>
    </div>
  );
}
