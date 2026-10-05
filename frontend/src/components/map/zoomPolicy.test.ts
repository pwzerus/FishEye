import { describe, expect, it } from "vitest";

import {
  MIN_ZOOM_FOR_ALL_LAKES,
  MIN_ZOOM_FOR_LAKES,
  US_ZOOM,
  asExploringView,
  lakeDetailExitZoom,
  lakeQueryFor,
  listStateNames,
  zoomLimitsFor,
} from "./zoomPolicy";

describe("zoomLimitsFor", () => {
  it("locks the national map at country scale, so a scroll can't reach state scale", () => {
    const { max } = zoomLimitsFor("national");
    expect(max).toBe(US_ZOOM);
    expect(max).toBeLessThan(MIN_ZOOM_FOR_LAKES);
  });

  it("keeps exploring at state scale or closer, so a scroll can't fall back to country scale", () => {
    expect(zoomLimitsFor("exploring").min).toBe(MIN_ZOOM_FOR_LAKES);
  });

  it("leaves no zoom level that both modes share", () => {
    expect(zoomLimitsFor("national").max).toBeLessThan(zoomLimitsFor("exploring").min);
  });
});

describe("lakeQueryFor", () => {
  it("never asks for lakes in national mode, whatever the zoom", () => {
    expect(lakeQueryFor("national", 3)).toBeNull();
    expect(lakeQueryFor("national", 12)).toBeNull();
  });

  it("asks for verified lakes only at state scale", () => {
    expect(lakeQueryFor("exploring", MIN_ZOOM_FOR_LAKES)).toEqual({ tier: "verified" });
    expect(lakeQueryFor("exploring", MIN_ZOOM_FOR_ALL_LAKES - 1)).toEqual({ tier: "verified" });
  });

  it("asks for every lake once zoomed in", () => {
    expect(lakeQueryFor("exploring", MIN_ZOOM_FOR_ALL_LAKES)).toEqual({});
    expect(lakeQueryFor("exploring", 14)).toEqual({});
  });
});

describe("asExploringView", () => {
  it("pulls a too-wide view up to state scale", () => {
    expect(asExploringView({ center: [31, -97], zoom: 4 }).zoom).toBe(MIN_ZOOM_FOR_LAKES);
  });

  it("keeps a view that is already in range", () => {
    expect(asExploringView({ center: [31, -97], zoom: 9 })).toEqual({ center: [31, -97], zoom: 9 });
  });
});

describe("lakeDetailExitZoom", () => {
  it("stays on the lake one step out, leaves two steps out", () => {
    for (const settled of [9, 12, 13, 16]) {
      const exitBelow = lakeDetailExitZoom(settled);
      expect(settled - 1).not.toBeLessThan(exitBelow); // one step out: stays
      expect(settled - 2).toBeLessThan(exitBelow); // two steps out: leaves
    }
  });

  it("never triggers on the lake's own initial fit", () => {
    for (const z of [5, 8, 10, 12, 15, 18]) expect(z).not.toBeLessThan(lakeDetailExitZoom(z));
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
