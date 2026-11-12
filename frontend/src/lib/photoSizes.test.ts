import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { photoSrcSet, sized } from "./photoSizes";

const BASS =
  "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Largemouth_Bass_%28Micropterus_salmoides%29.jpg/960px-Largemouth_Bass_%28Micropterus_salmoides%29.jpg";

describe("smaller copies of the 960px photos", () => {
  it("asks Wikimedia for its standard widths", () => {
    expect(photoSrcSet(BASS, 960)).toBe(
      [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Largemouth_Bass_%28Micropterus_salmoides%29.jpg/330px-Largemouth_Bass_%28Micropterus_salmoides%29.jpg 330w",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Largemouth_Bass_%28Micropterus_salmoides%29.jpg/500px-Largemouth_Bass_%28Micropterus_salmoides%29.jpg 500w",
        `${BASS} 960w`,
      ].join(", "),
    );
  });

  it("asks for thumbnails of an original file smaller than it", () => {
    const shrimp = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Raw_Shrimp.jpg";
    expect(photoSrcSet(shrimp, 960)).toBe(
      "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Raw_Shrimp.jpg/330px-Raw_Shrimp.jpg 330w, " +
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Raw_Shrimp.jpg/500px-Raw_Shrimp.jpg 500w, " +
        `${shrimp} 960w`,
    );
    // A link with a query keeps it; the thumbnails don't need it.
    const trout = "https://upload.wikimedia.org/wikipedia/commons/e/ee/Brook_trout_in_water.jpg?utm_source=en";
    expect(photoSrcSet(trout, 420)).toBe(
      `https://upload.wikimedia.org/wikipedia/commons/thumb/e/ee/Brook_trout_in_water.jpg/330px-Brook_trout_in_water.jpg 330w, ${trout} 420w`,
    );
    expect(photoSrcSet("https://upload.wikimedia.org/wikipedia/commons/a/ab/Small.jpg", 300)).toBeUndefined();
    expect(photoSrcSet("https://upload.wikimedia.org/wikipedia/commons/a/ab/Map.svg", 960)).toBeUndefined();
  });

  it("uses the 500px copy of FishEye's own gear photos, at their real width", () => {
    expect(photoSrcSet("/gear-photos/hook-treble.jpg", 737)).toBe("/gear-photos/500/hook-treble.jpg 500w, /gear-photos/hook-treble.jpg 737w");
    expect(photoSrcSet("/gear-photos/tiny.jpg", 400)).toBeUndefined();
  });

  it("leaves any other photo as it is", () => {
    expect(photoSrcSet("https://example.org/photo.jpg", 960)).toBeUndefined();
    expect(sized("/api/pins/3/photos/1/thumb", 400, "56px")).toEqual({ src: "/api/pins/3/photos/1/thumb" });
    expect(sized(BASS, 960, "56px")).toMatchObject({ src: BASS, sizes: "56px" });
  });

  it("has a 500px copy of every own gear photo (all are wider than that)", () => {
    const dir = join(process.cwd(), "public", "gear-photos");
    const photos = readdirSync(dir).filter((f) => statSync(join(dir, f)).isFile());
    expect(photos.length).toBeGreaterThan(0);
    const copies = new Set(readdirSync(join(dir, "500")));
    expect(photos.filter((f) => !copies.has(f))).toEqual([]);
  });
});
