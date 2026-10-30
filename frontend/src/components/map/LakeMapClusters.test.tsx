import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WaterbodyListItem } from "@/lib/api/types";
import LakeMap from "./LakeMap";
import type { StateRegion } from "./usStates";

// The raster fallback would try to fetch tiles; the basemap plays no part here.
vi.mock("./BaseMap", () => ({ BaseMap: () => null }));

// jsdom lays nothing out, so Leaflet would see a 0×0 map whose view is a
// single point, and the clusterer draws only markers inside the view.
const sizes = ["clientWidth", "clientHeight"] as const;
const saved = sizes.map((p) => Object.getOwnPropertyDescriptor(HTMLElement.prototype, p));
beforeEach(() => {
  sizes.forEach((p, i) =>
    Object.defineProperty(HTMLElement.prototype, p, {
      configurable: true,
      get(this: HTMLElement) {
        return this.classList.contains("leaflet-container") ? [800, 600][i] : 0;
      },
    }),
  );
});
afterEach(() => {
  sizes.forEach((p, i) => {
    const d = saved[i];
    if (d) Object.defineProperty(HTMLElement.prototype, p, d);
    else delete (HTMLElement.prototype as unknown as Record<string, unknown>)[p];
  });
});

// A state a county wide: framing it all takes zoom 9, well above the floor
// the map has before any state is chosen.
const SMALL_STATE: StateRegion = {
  code: "ZZ",
  name: "Smallstate",
  bounds: [
    [33.5, -84.6],
    [34.3, -83.7],
  ],
  rings: [
    [
      [33.5, -84.6],
      [34.3, -84.6],
      [34.3, -83.7],
      [33.5, -83.7],
    ],
  ],
};

const LONE_POND: WaterbodyListItem = {
  id: 1,
  name: "Freeman Lake",
  latitude: 33.9197,
  longitude: -84.1438,
  field_tested: false,
  public_access_status: "unknown",
  data_tier: "osm",
  water_type: "pond",
  reported_species_count: 0,
};

// The 2026-10-29 walkthrough: after Use my location the only lake nearby
// came back from the server but never appeared on the map.
describe("lakes after the map locks to a state", () => {
  it("draws a lake with no neighbour to cluster with", async () => {
    const props = {
      onSelect: () => undefined,
      onViewportChange: () => undefined,
      initialView: { center: [33.92, -84.14] as [number, number], zoom: 15 },
      mode: "exploring" as const,
    };
    // Use my location: the map flies there with no state chosen yet…
    const { container, rerender } = render(<LakeMap {...props} waterbodies={[]} region={null} />);
    // …then locks to the state it landed in, which raises the zoom floor,
    // and that state's lakes arrive.
    rerender(<LakeMap {...props} waterbodies={[LONE_POND]} region={SMALL_STATE} />);
    await act(async () => {}); // the cluster group adds markers in a microtask

    const marker = container.querySelector('.leaflet-marker-pane [title^="Freeman Lake"]');
    expect(marker).not.toBeNull();
  });
});
