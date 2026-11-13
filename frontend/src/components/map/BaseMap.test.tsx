import { act, render, waitFor } from "@testing-library/react";
import L from "leaflet";
import { MapContainer } from "react-leaflet";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setBasemapChoice } from "@/lib/map/basemapChoice";

import { BaseMap } from "./BaseMap";

vi.mock("@/lib/map/tiles", async (original) => ({
  ...(await original<typeof import("@/lib/map/tiles")>()),
  MAP_STYLE_URL: "https://satellite.test/style.json",
  PLAIN_STYLE_URL: "https://plain.test/style.json",
}));
// The vector layer itself needs WebGL; any Leaflet layer stands in for it.
vi.mock("@maplibre/maplibre-gl-leaflet", () => ({ maplibreGL: () => L.layerGroup() }));

const fetched: string[] = [];
beforeEach(() => {
  fetched.length = 0;
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as RenderingContext);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      fetched.push(url);
      return { ok: true, json: async () => ({ version: 8, sources: {}, layers: [] }) };
    }),
  );
  act(() => setBasemapChoice("satellite"));
});
afterEach(() => {
  act(() => setBasemapChoice("plain"));
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function map(child: React.ReactNode) {
  return render(
    <MapContainer center={[33.9, -84.2]} zoom={9} style={{ height: 300, width: 300 }}>
      {child}
    </MapContainer>,
  );
}

// The product owner, 2026-11-12: satellite on a state's map and a lake's,
// never the country's.
describe("BaseMap", () => {
  it("draws satellite where the map allows it and it was picked", async () => {
    map(<BaseMap satellite />);
    await waitFor(() => expect(fetched[0]).toBe("https://satellite.test/style.json"));
  });

  it("stays plain on any other map, whatever was picked", async () => {
    map(<BaseMap />);
    await waitFor(() => expect(fetched[0]).toBe("https://plain.test/style.json"));
  });
});
