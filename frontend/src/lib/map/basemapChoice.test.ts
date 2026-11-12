import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { setBasemapChoice, useBasemapChoice } from "./basemapChoice";

// The product owner, 2026-11-12: the plain map by default, satellite (billed
// per tile) only when asked for.
describe("basemap choice", () => {
  it("starts on the plain map", () => {
    window.localStorage.removeItem("fisheye.basemap");
    const { result } = renderHook(() => useBasemapChoice());
    expect(result.current).toBe("plain");
  });

  it("switches every map to satellite and remembers it", () => {
    const { result } = renderHook(() => useBasemapChoice());
    act(() => setBasemapChoice("satellite"));
    expect(result.current).toBe("satellite");
    expect(window.localStorage.getItem("fisheye.basemap")).toBe("satellite");
    act(() => setBasemapChoice("plain"));
    expect(result.current).toBe("plain");
  });
});
