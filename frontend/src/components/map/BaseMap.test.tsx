import { render } from "@testing-library/react";
import { MapContainer } from "react-leaflet";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BaseMap } from "./BaseMap";

const tiles = vi.hoisted(() => ({ url: "" }));

vi.mock("@/lib/map/tiles", () => ({
  MAP_STYLE_URL: null,
  TILE_ATTRIBUTION: "credit",
  get TILE_URL() {
    return tiles.url;
  },
}));

function renderMap() {
  return render(
    <MapContainer center={[30, -97]} zoom={5}>
      <BaseMap />
    </MapContainer>,
  );
}

describe("BaseMap's MapTiler logo", () => {
  beforeEach(() => {
    tiles.url = "";
  });

  it("links the logo to MapTiler when the map comes from MapTiler", () => {
    tiles.url = "https://api.maptiler.com/maps/landscape/256/{z}/{x}/{y}.png?key=k";
    const { container } = renderMap();
    const logo = container.querySelector<HTMLImageElement>('img[alt="MapTiler"]');
    expect(logo).not.toBeNull();
    expect(logo?.closest("a")?.href).toBe("https://www.maptiler.com/");
  });

  it("shows no logo when the map comes from elsewhere", () => {
    tiles.url = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
    const { container } = renderMap();
    expect(container.querySelector('img[alt="MapTiler"]')).toBeNull();
  });
});
