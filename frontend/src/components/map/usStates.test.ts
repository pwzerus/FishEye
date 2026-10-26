import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { type StatesFile, regionOf, stateCodeAt } from "./usStates";

const file = JSON.parse(
  readFileSync(join(__dirname, "../../../public/geo/us-states.json"), "utf8"),
) as StatesFile;
const covered = new Set(["CA", "GA", "TX"]);

describe("stateCodeAt", () => {
  it("finds the state a city is in", () => {
    expect(stateCodeAt(file, 32.78, -96.8)).toBe("TX"); // Dallas
    expect(stateCodeAt(file, 33.75, -84.39)).toBe("GA"); // Atlanta
    expect(stateCodeAt(file, 34.05, -118.24)).toBe("CA"); // Los Angeles
    expect(stateCodeAt(file, 35.47, -97.52)).toBe("OK"); // Oklahoma City
  });

  it("keeps Lake Lanier in Georgia, not over the line", () => {
    expect(stateCodeAt(file, 34.2, -83.95)).toBe("GA");
  });

  it("still places a point just off the coast", () => {
    expect(stateCodeAt(file, 29.3, -94.75, covered)).toBe("TX"); // Galveston
  });

  it("returns null far from any state", () => {
    expect(stateCodeAt(file, 0, 0)).toBeNull();
  });
});

describe("regionOf", () => {
  it("boxes the state and keeps its outline", () => {
    const tx = regionOf(file, "TX")!;
    const [[south, west], [north, east]] = tx.bounds;
    expect(south).toBeCloseTo(25.8, 0);
    expect(north).toBeCloseTo(36.5, 0);
    expect(west).toBeCloseTo(-106.6, 0);
    expect(east).toBeCloseTo(-93.5, 0);
    expect(tx.rings.length).toBeGreaterThan(0);
    expect(tx.name).toBe("Texas");
  });

  it("is null for an unknown code", () => {
    expect(regionOf(file, "ZZ")).toBeNull();
  });
});
