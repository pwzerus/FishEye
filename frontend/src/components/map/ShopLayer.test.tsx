import { render } from "@testing-library/react";
import { MapContainer } from "react-leaflet";
import { describe, expect, it } from "vitest";

import type { Shop } from "@/lib/api/types";
import { ShopMarkers } from "./ShopLayer";
import { MESSAGES } from "@/i18n/messages";
import { directionsUrl } from "./shops";

const SHOP: Shop = {
  id: 1,
  name: "Lake Sinclair Bait And Tackle",
  kind: "bait",
  latitude: 33.15,
  longitude: -83.2,
  address: "100 Hwy 441, Milledgeville, GA",
  phone: "+1 478-555-0100",
  website: "https://bait.example",
  opening_hours: "Mo-Su 05:00-19:00",
  osm_url: "https://www.openstreetmap.org/node/1",
};

describe("ShopMarkers", () => {
  it("marks each shop, named for screen readers", () => {
    const { container } = render(
      <MapContainer center={[33.15, -83.2]} zoom={12} style={{ height: 300, width: 300 }}>
        <ShopMarkers shops={[SHOP, { ...SHOP, id: 2, name: "Bass Pro Shops", kind: "store" }]} />
      </MapContainer>,
    );
    const markers = container.querySelectorAll(".leaflet-marker-pane .shop-marker-wrap");
    expect(markers).toHaveLength(2);
    expect(markers[0].getAttribute("title")).toBe("Lake Sinclair Bait And Tackle, Bait & tackle");
    expect(markers[1].getAttribute("title")).toBe(`Bass Pro Shops, ${MESSAGES.en.shops.store}`);
  });

  it("gives directions to the shop's own point", () => {
    expect(directionsUrl(SHOP)).toBe("https://www.google.com/maps/dir/?api=1&destination=33.15,-83.2");
  });
});
