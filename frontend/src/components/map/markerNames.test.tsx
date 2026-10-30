import { render } from "@testing-library/react";
import { MapContainer } from "react-leaflet";
import { describe, expect, it } from "vitest";

import type { PinSummary } from "@/lib/api/types";
import { clusterIcon } from "./LakeMap";
import { PinMarkers } from "./PinLayer";
import { waterIcon } from "./waterIcon";

// The 2026-10-28 review: shop markers had names for screen readers, lake
// markers, catches and the cluster bubbles didn't.
describe("names for screen readers", () => {
  it("says what a cluster bubble holds, not just a number", () => {
    const div = document.createElement("div");
    div.innerHTML = (clusterIcon({ getChildCount: () => 12 }).options.html as string) ?? "";
    expect(div.textContent).toBe("12 lakes here. Zoom in to see them.");
    expect(div.querySelector(".sr-only")).not.toBeNull(); // the number is all that shows
    expect(clusterIcon({ getChildCount: () => 3 }).options.className).toBe("marker-cluster marker-cluster-small");
    expect(clusterIcon({ getChildCount: () => 250 }).options.className).toBe("marker-cluster marker-cluster-large");
  });

  it("hides a lake marker's glyph, so its title names it rather than \"≈\"", () => {
    for (const kind of ["verified", "osm", "access"] as const) {
      const div = document.createElement("div");
      div.innerHTML = waterIcon(kind).options.html as string;
      expect(div.firstElementChild?.getAttribute("aria-hidden")).toBe("true");
    }
  });

  it("names each catch on the map", () => {
    const pin = {
      id: 1, latitude: 32.8, longitude: -95.6, location_shown: "lake", share_exact: false, public_place: "lake",
      title: "Riprap by the dam", species_slug: null, species_label: null, species_check: null, species_check_label: null,
      caught_on: null, created_at: "2026-09-25T12:00:00Z", visibility: "public", status: "published", status_reason: null,
      author: { id: 2, display_name: "Bob" }, lake: null, photo_count: 0, thumb_url: null, is_mine: false,
    } satisfies PinSummary;
    const { container } = render(
      <MapContainer center={[32.8, -95.6]} zoom={12} style={{ height: 300, width: 300 }}>
        <PinMarkers pins={[pin]} />
      </MapContainer>,
    );
    const marker = container.querySelector(".leaflet-marker-pane .catch-marker-wrap");
    expect(marker?.getAttribute("title")).toBe("Riprap by the dam, a catch by Bob");
    expect(marker?.getAttribute("role")).toBe("button");
  });
});
