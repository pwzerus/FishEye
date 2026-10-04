import { afterEach, describe, expect, it, vi } from "vitest";

/** The module reads process.env once, at import time — the same moment Next
 * inlines the value at build time — so each case needs a fresh import. */
async function loadTiles(env: Record<string, string | undefined>) {
  vi.resetModules();
  // undefined deletes the variable, which is the "nobody configured this"
  // case; "" is the distinct "configured, but blank" case.
  for (const [key, value] of Object.entries(env)) vi.stubEnv(key, value);
  return import("./tiles");
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("tile source", () => {
  it("falls back to OpenStreetMap when nothing is configured", async () => {
    const { TILE_URL, TILE_ATTRIBUTION } = await loadTiles({
      NEXT_PUBLIC_TILE_URL: undefined,
      NEXT_PUBLIC_TILE_ATTRIBUTION: undefined,
    });
    expect(TILE_URL).toBe("https://tile.openstreetmap.org/{z}/{x}/{y}.png");
    expect(TILE_ATTRIBUTION).toContain("OpenStreetMap");
  });

  it("uses the configured provider when one is set", async () => {
    const url = "https://api.maptiler.com/maps/streets-v4/256/{z}/{x}/{y}.png?key=abc123";
    const { TILE_URL, TILE_ATTRIBUTION } = await loadTiles({
      NEXT_PUBLIC_TILE_URL: url,
      NEXT_PUBLIC_TILE_ATTRIBUTION: "&copy; MapTiler",
    });
    expect(TILE_URL).toBe(url);
    expect(TILE_ATTRIBUTION).toBe("&copy; MapTiler");
  });

  // A blank value is what a half-edited .env.local or an unresolved CI secret
  // produces. `??` would pass the empty string through and render a grey grid
  // with no clue why, so this pins the `||`.
  it("falls back when the variable is present but blank", async () => {
    const { TILE_URL, TILE_ATTRIBUTION } = await loadTiles({
      NEXT_PUBLIC_TILE_URL: "",
      NEXT_PUBLIC_TILE_ATTRIBUTION: "",
    });
    expect(TILE_URL).toBe("https://tile.openstreetmap.org/{z}/{x}/{y}.png");
    expect(TILE_ATTRIBUTION).toContain("OpenStreetMap");
  });

  // The subdomain rotation the map components used to carry: no hosted
  // provider supports it, and OSM serves from the bare host now.
  it("does not use OSM subdomain rotation", async () => {
    const { TILE_URL } = await loadTiles({ NEXT_PUBLIC_TILE_URL: undefined });
    expect(TILE_URL).not.toContain("{s}");
  });
});
