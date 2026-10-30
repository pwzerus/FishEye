import { describe, expect, it } from "vitest";

import { coveredBottom, fallbackLakeZoom } from "./LakeDetailMap";

// The 2026-10-29 review: a small lake opened from close in jumped out to a
// fixed zoom 12, about 15 km across, so the lake became a dot in a city.
describe("fallbackLakeZoom", () => {
  it("keeps the zoom the person clicked the lake at", () => {
    expect(fallbackLakeZoom(15)).toBe(15);
    expect(fallbackLakeZoom(14.4)).toBe(14);
  });

  it("stays at lake scale whatever they came from", () => {
    expect(fallbackLakeZoom(9)).toBe(13); // a state-wide view: zoom in to the lake
    expect(fallbackLakeZoom(18)).toBe(16); // closer than this shows only water
    expect(fallbackLakeZoom(undefined)).toBe(14); // opened from a link
  });
});

const rect = (x: number, y: number, width: number, height: number) =>
  ({ left: x, top: y, right: x + width, bottom: y + height, width, height }) as DOMRect;

// The same review, on a phone: the lake opened centred on the whole map, at
// the edge of the sheet that had risen over the map's lower half.
describe("coveredBottom", () => {
  const map = rect(0, 58, 375, 688);

  it("measures a phone's sheet lying over the map", () => {
    expect(coveredBottom(map, rect(0, 436, 375, 310))).toBe(310);
  });

  it("finds nothing hidden by a panel beside or below the map", () => {
    expect(coveredBottom(rect(0, 58, 920, 802), rect(920, 58, 446, 802))).toBe(0); // desktop
    expect(coveredBottom(map, rect(0, 746, 375, 400))).toBe(0); // stacked under it
    expect(coveredBottom(map, null)).toBe(0);
  });
});
