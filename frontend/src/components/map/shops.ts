import type { Shop } from "@/lib/api/types";

// Leaflet-free, so the lake panel (rendered on the server too) can use them.

export const SHOP_KIND_LABEL: Record<Shop["kind"], string> = {
  bait: "Bait & tackle",
  tackle: "Tackle shop",
  store: "Fishing gear · sporting goods store",
};

/** A link that opens directions in the phone's or browser's maps app. */
export function directionsUrl(shop: Pick<Shop, "latitude" | "longitude">): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${shop.latitude},${shop.longitude}`;
}
