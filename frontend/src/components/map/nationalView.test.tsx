import { act, render } from "@testing-library/react";
import L from "leaflet";
import { MapContainer } from "react-leaflet";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LakeMap, { NATIONAL_SHARE, ViewLimits } from "./LakeMap";
import type { StateRegion } from "./usStates";

// The raster fallback would try to fetch tiles; the basemap plays no part here.
vi.mock("./BaseMap", () => ({ BaseMap: () => null }));

// jsdom lays nothing out; give the map a size so its view is a real area.
// And Leaflet allows zooms between whole levels only where the browser does
// 3D transforms, which every browser the site supports does and jsdom doesn't.
let size: [number, number] = [800, 600];
const browser = L.Browser as { any3d: boolean };
const any3d = browser.any3d;
const sizes = ["clientWidth", "clientHeight"] as const;
const saved = sizes.map((p) => Object.getOwnPropertyDescriptor(HTMLElement.prototype, p));
beforeEach(() => {
  size = [800, 600];
  browser.any3d = true;
  sizes.forEach((p, i) =>
    Object.defineProperty(HTMLElement.prototype, p, {
      configurable: true,
      get(this: HTMLElement) {
        return this.classList.contains("leaflet-container") ? size[i] : 0;
      },
    }),
  );
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ type: "FeatureCollection", features: [] }) })));
});
afterEach(() => {
  browser.any3d = any3d;
  sizes.forEach((p, i) => {
    const d = saved[i];
    if (d) Object.defineProperty(HTMLElement.prototype, p, d);
    else delete (HTMLElement.prototype as unknown as Record<string, unknown>)[p];
  });
  vi.unstubAllGlobals();
});

const LOWER_48 = { south: 24.51, west: -124.73, north: 49.38, east: -66.98 };

const SMALL_STATE: StateRegion = {
  code: "ZZ",
  name: "Smallstate",
  bounds: [
    [33.5, -84.6],
    [34.3, -83.7],
  ],
  rings: [],
};

function limited(mode: "national" | "exploring", region: StateRegion | null = null) {
  return (
    <ViewLimits mode={mode} region={region} fit={region !== null} skipFitOnMount={false} />
  );
}

function nationalMap() {
  let map: L.Map | null = null;
  const view = render(
    <MapContainer ref={(m) => { map = m; }} center={[39.5, -98.35]} zoom={4} minZoom={3} maxZoom={18} style={{ height: 600, width: 800 }}>
      {limited("national")}
    </MapContainer>,
  );
  const rerender = (child: React.ReactNode) =>
    view.rerender(
      <MapContainer ref={(m) => { map = m; }} center={[39.5, -98.35]} zoom={4} minZoom={3} maxZoom={18} style={{ height: 600, width: 800 }}>
        {child}
      </MapContainer>,
    );
  return { map: map!, rerender };
}

// The product owner, 2026-11-11: the country map is the US, filling the
// screen with a little of Canada, Mexico and the oceans round it; no
// dragging; Alaska and Hawaii by their buttons.
describe("the country-scale map", () => {
  it("centres the lower 48, at NATIONAL_SHARE of the map's width", () => {
    const { map } = nationalMap();
    const view = map.getBounds();
    expect(view.getWest()).toBeLessThan(LOWER_48.west);
    expect(view.getEast()).toBeGreaterThan(LOWER_48.east);
    expect(view.getSouth()).toBeLessThan(LOWER_48.south);
    expect(view.getNorth()).toBeGreaterThan(LOWER_48.north);
    const share = (LOWER_48.east - LOWER_48.west) / (view.getEast() - view.getWest());
    expect(share).toBeCloseTo(NATIONAL_SHARE, 2);
    // Centred: as much room on the left as on the right.
    const left = LOWER_48.west - view.getWest();
    const right = view.getEast() - LOWER_48.east;
    expect(Math.abs(left - right)).toBeLessThan(0.5);
  });

  it("holds that one zoom, in and out", () => {
    const { map } = nationalMap();
    expect(map.getMinZoom()).toBe(map.getZoom());
    expect(map.getMaxZoom()).toBe(map.getZoom());
  });

  it("frames the country again when the map changes size", () => {
    const { map } = nationalMap();
    const wide = map.getZoom();
    size = [400, 600];
    act(() => {
      map.invalidateSize({ animate: false });
    });
    expect(map.getZoom()).toBeLessThan(wide);
    const view = map.getBounds();
    expect(view.getWest()).toBeLessThan(LOWER_48.west);
    expect(view.getEast()).toBeGreaterThan(LOWER_48.east);
  });

  it("is back on whole zoom levels inside a state", () => {
    const { map, rerender } = nationalMap();
    rerender(limited("exploring", SMALL_STATE));
    expect(Number.isInteger(map.getZoom())).toBe(true);
    expect(map.getMaxZoom()).toBe(18);
  });
});

describe("LakeMap at country scale", () => {
  const props = { waterbodies: [], onSelect: () => undefined, onViewportChange: () => undefined };

  it("can't be dragged and has no zoom buttons", () => {
    const { container } = render(<LakeMap {...props} mode="national" />);
    expect(container.querySelector(".leaflet-container")?.classList.contains("leaflet-grab")).toBe(false);
    expect(container.querySelector(".leaflet-control-zoom")).toBeNull();
  });

  it("moves and zooms again inside a state", () => {
    const { container } = render(
      <LakeMap {...props} mode="exploring" initialView={{ center: [33.9, -84.2], zoom: 9 }} />,
    );
    expect(container.querySelector(".leaflet-container")?.classList.contains("leaflet-grab")).toBe(true);
    expect(container.querySelector(".leaflet-control-zoom")).not.toBeNull();
  });
});
