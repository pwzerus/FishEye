import { describe, expect, it } from "vitest";

import { readExif, readPhotoFacts } from "./exif";
import { JPEG_PLAIN, JPEG_WITH_EXIF, fixtureBytes } from "./exif.fixture";

describe("readExif", () => {
  it("reads the day and the spot a phone photo was taken", () => {
    const facts = readExif(fixtureBytes(JPEG_WITH_EXIF).buffer);
    expect(facts.takenOn).toBe("2026-09-20");
    expect(facts.latitude).toBeCloseTo(32.80639, 4);
    expect(facts.longitude).toBeCloseTo(-95.58639, 4);
  });

  it("says nothing for a photo without metadata, or a file that isn't a JPEG", () => {
    expect(readExif(fixtureBytes(JPEG_PLAIN).buffer)).toEqual({ takenOn: null, latitude: null, longitude: null });
    expect(readExif(new TextEncoder().encode("not a photo").buffer)).toEqual({ takenOn: null, latitude: null, longitude: null });
  });

  it("reads only JPEG files", async () => {
    const png = new File([fixtureBytes(JPEG_WITH_EXIF)], "a.png", { type: "image/png" });
    expect((await readPhotoFacts(png)).takenOn).toBeNull();
  });
});
