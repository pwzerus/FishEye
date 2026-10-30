import type { Shop } from "@/lib/api/types";

// Leaflet-free, so the lake panel (rendered on the server too) can use them.

/** The shop kinds' labels live with the other strings: t.shops[shop.kind]. */
export type ShopKind = Shop["kind"];

/** A link that opens directions in the phone's or browser's maps app. */
export function directionsUrl(shop: Pick<Shop, "latitude" | "longitude">): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${shop.latitude},${shop.longitude}`;
}
