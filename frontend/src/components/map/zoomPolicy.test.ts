import { describe, expect, it } from "vitest";

import {
  MIN_ZOOM_FOR_ALL_LAKES,
  MIN_ZOOM_FOR_LAKES,
  lakeQueryForZoom,
  listStateNames,
} from "./zoomPolicy";

describe("lakeQueryForZoom", () => {
  it("asks for nothing at country scale", () => {
    expect(lakeQueryForZoom(3)).toBeNull();
    expect(lakeQueryForZoom(MIN_ZOOM_FOR_LAKES - 1)).toBeNull();
  });

  it("asks for verified lakes only at state scale", () => {
    expect(lakeQueryForZoom(MIN_ZOOM_FOR_LAKES)).toEqual({ tier: "verified" });
    expect(lakeQueryForZoom(MIN_ZOOM_FOR_ALL_LAKES - 1)).toEqual({ tier: "verified" });
  });

  it("asks for every lake once zoomed in", () => {
    expect(lakeQueryForZoom(MIN_ZOOM_FOR_ALL_LAKES)).toEqual({});
    expect(lakeQueryForZoom(14)).toEqual({});
  });

  it("keeps the tiers in order", () => {
    expect(MIN_ZOOM_FOR_LAKES).toBeLessThan(MIN_ZOOM_FOR_ALL_LAKES);
  });
});

describe("listStateNames", () => {
  it("reads naturally for one, two and many", () => {
    expect(listStateNames([])).toBe("");
    expect(listStateNames(["Texas"])).toBe("Texas");
    expect(listStateNames(["Texas", "Oklahoma"])).toBe("Texas and Oklahoma");
    expect(listStateNames(["Texas", "Oklahoma", "Louisiana"])).toBe("Texas, Oklahoma and Louisiana");
  });
});
