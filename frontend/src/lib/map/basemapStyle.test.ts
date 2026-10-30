import type { LayerSpecification, StyleSpecification } from "maplibre-gl";
import { describe, expect, it } from "vitest";

import { hideAirportIcons, isHiddenLayer, styleAttribution, withLinkedAttributions } from "./basemapStyle";

// The five airport-related layers of MapTiler streets-v4, as read from its
// style.json (ids, types and source layers exactly as served), plus a few
// neighbours that must be left alone.
const LAYERS = [
  { id: "Airport zone", type: "fill", source: "t", "source-layer": "aviation" },
  { id: "Aeroway", type: "line", source: "t", "source-layer": "aviation_line" },
  { id: "Airport gate labels", type: "symbol", source: "t", "source-layer": "poi_station" },
  { id: "Airport terminal", type: "symbol", source: "t", "source-layer": "poi_station", layout: { "icon-image": "terminal" } },
  { id: "Airport labels", type: "symbol", source: "t", "source-layer": "poi_station", layout: { "text-size": 12 } },
  { id: "Railway station", type: "symbol", source: "t", "source-layer": "poi_station" },
  { id: "Lake labels", type: "symbol", source: "t", "source-layer": "water_name" },
  { id: "Road", type: "line", source: "t", "source-layer": "transportation" },
] as unknown as LayerSpecification[];

const STYLE = { version: 8, sources: {}, layers: LAYERS } as unknown as StyleSpecification;

const visibility = (style: StyleSpecification) =>
  Object.fromEntries(
    style.layers.map((l) => [l.id, (l.layout as { visibility?: string } | undefined)?.visibility ?? "visible"]),
  );

describe("hideAirportIcons", () => {
  it("hides the airport icon and label layers", () => {
    const v = visibility(hideAirportIcons(STYLE));
    expect(v["Airport labels"]).toBe("none");
    expect(v["Airport terminal"]).toBe("none");
    expect(v["Airport gate labels"]).toBe("none");
  });

  it("keeps the runway lines and the airport zone", () => {
    const v = visibility(hideAirportIcons(STYLE));
    expect(v["Aeroway"]).toBe("visible");
    expect(v["Airport zone"]).toBe("visible");
  });

  it("leaves every other layer alone", () => {
    const v = visibility(hideAirportIcons(STYLE));
    expect(v["Railway station"]).toBe("visible");
    expect(v["Lake labels"]).toBe("visible");
    expect(v["Road"]).toBe("visible");
  });

  it("keeps a hidden layer's other layout properties", () => {
    const labels = hideAirportIcons(STYLE).layers.find((l) => l.id === "Airport labels");
    expect(labels?.layout).toEqual({ "text-size": 12, visibility: "none" });
  });

  it("does not modify the style it was given", () => {
    const before = JSON.stringify(STYLE);
    hideAirportIcons(STYLE);
    expect(JSON.stringify(STYLE)).toBe(before);
  });
});

describe("isHiddenLayer", () => {
  it("survives small renames by MapTiler", () => {
    const sym = (id: string) => ({ id, type: "symbol", source: "t" }) as unknown as LayerSpecification;
    expect(isHiddenLayer(sym("Airport label"))).toBe(true);
    expect(isHiddenLayer(sym("aerodrome_label"))).toBe(true);
    expect(isHiddenLayer(sym("Airstrip"))).toBe(true);
    expect(isHiddenLayer(sym("Lake labels"))).toBe(false);
  });
});

describe("styleAttribution", () => {
  const credit = '<a href="https://www.maptiler.com/copyright/">© MapTiler</a> <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>';
  const withSources = (sources: Record<string, unknown>) =>
    ({ version: 8, sources, layers: [] }) as unknown as StyleSpecification;

  it("names each credit once even when two sources carry it", () => {
    const style = withSources({
      maptiler_attribution: { type: "vector", attribution: credit },
      maptiler_planet_v4: { type: "vector", attribution: ` ${credit} ` },
    });
    expect(styleAttribution(style, "fallback")).toBe(credit);
  });

  it("keeps distinct credits, in order", () => {
    const style = withSources({ a: { type: "vector", attribution: "A" }, b: { type: "vector", attribution: "B" } });
    expect(styleAttribution(style, "fallback")).toBe("A, B");
  });

  it("falls back rather than showing no credit", () => {
    const style = withSources({ a: { type: "vector" }, b: { type: "vector", attribution: "  " } });
    expect(styleAttribution(style, "fallback")).toBe("fallback");
  });
});

describe("withLinkedAttributions", () => {
  const credit = '<a href="https://www.maptiler.com/copyright/">&copy; MapTiler</a> <a href="https://www.openstreetmap.org/copyright">&copy; OpenStreetMap contributors</a>';
  const withSources = (sources: Record<string, unknown>) =>
    ({ version: 8, sources, layers: [] }) as unknown as StyleSpecification;

  it("credits MapTiler for a style that keeps its credit in the TileJSON (Satellite Hybrid)", async () => {
    // The shape of hybrid-v4: both sources by url, no attribution in the style.
    const style = withSources({
      maptiler_planet: { type: "vector", url: "https://api.maptiler.com/tiles/v4/tiles.json" },
      satellite: { type: "raster", url: "https://api.maptiler.com/tiles/satellite-v2/tiles.json" },
    });
    const fetched: string[] = [];
    const resolved = await withLinkedAttributions(style, async (url) => {
      fetched.push(url);
      return { attribution: credit };
    });
    expect(fetched).toHaveLength(2);
    expect(styleAttribution(resolved, "fallback")).toBe(credit);
    expect(style.sources.satellite).not.toHaveProperty("attribution");
  });

  it("leaves a credit the style already names, and does not fetch for it", async () => {
    const style = withSources({ a: { type: "vector", url: "https://x/tiles.json", attribution: "A" } });
    let calls = 0;
    const resolved = await withLinkedAttributions(style, async () => {
      calls += 1;
      return { attribution: "B" };
    });
    expect(calls).toBe(0);
    expect(styleAttribution(resolved, "fallback")).toBe("A");
  });

  it("keeps the fallback when a TileJSON fails or names no credit", async () => {
    const style = withSources({
      a: { type: "vector", url: "https://x/a.json" },
      b: { type: "vector", url: "https://x/b.json" },
      c: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
    });
    const resolved = await withLinkedAttributions(style, async (url) => {
      if (url.endsWith("a.json")) throw new Error("offline");
      return {};
    });
    expect(styleAttribution(resolved, "fallback")).toBe("fallback");
  });
});
