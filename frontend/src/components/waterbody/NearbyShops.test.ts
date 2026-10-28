import { describe, expect, it } from "vitest";

import { miles } from "./NearbyShops";

describe("miles", () => {
  it("gives tenths under 10 miles and whole miles from there", () => {
    expect(miles(3.2)).toBe("2.0 mi");
    expect(miles(16.08)).toBe("10 mi");
    expect(miles(29.0)).toBe("18 mi");
  });
});
