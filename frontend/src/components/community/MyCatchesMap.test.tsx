import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PinSummary } from "@/lib/api/types";

// The basemap needs WebGL, which the test browser lacks.
vi.mock("@/components/map/BaseMap", () => ({ BaseMap: () => null }));
const { default: MyCatchesMap } = await import("./MyCatchesMap");

const pin = (id: number, latitude: number, longitude: number, visibility: "public" | "private" = "public"): PinSummary => ({
  id,
  latitude,
  longitude,
  title: `Catch ${id}`,
  species_slug: "bluegill",
  species_label: "Bluegill",
  species_check: "confirmed",
  species_check_label: null,
  caught_on: "2026-10-20",
  created_at: "2026-10-20T12:00:00Z",
  visibility,
  status: "published",
  status_reason: null,
  author: { id: 1, display_name: "You" },
  lake: null,
  photo_count: 1,
  thumb_url: null,
  is_mine: true,
});

describe("MyCatchesMap", () => {
  it("marks every place you've pinned, private ones dashed", () => {
    const { container } = render(
      <div style={{ height: 300, width: 300 }}>
        <MyCatchesMap pins={[pin(1, 33.9, -84.2), pin(2, 30.3, -97.7, "private")]} />
      </div>,
    );
    const markers = container.querySelectorAll(".leaflet-marker-pane .catch-marker");
    expect(markers).toHaveLength(2);
    expect([...markers].filter((m) => m.classList.contains("is-private"))).toHaveLength(1);
    expect(container.querySelector(".leaflet-marker-icon")?.getAttribute("title")).toBe("Catch 1");
  });
});
