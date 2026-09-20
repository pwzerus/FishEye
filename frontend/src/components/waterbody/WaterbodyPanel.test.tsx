import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { WaterbodyDetail } from "@/lib/api/types";
import { WaterbodyPanel } from "./WaterbodyPanel";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return {
    ...actual,
    getWaterbody: vi.fn(),
  };
});

// Imported after the mock so we get the mocked reference.
const { getWaterbody } = await import("@/lib/api/client");

const mockDetail: WaterbodyDetail = {
  id: 1,
  name: "Lake Fork",
  latitude: 32.8,
  longitude: -95.6,
  access_summary: "A great bass lake.",
  source_url: "https://tpwd.texas.gov/fork",
  source_updated_at: "2026-09-01T00:00:00Z",
  field_tested: true,
  access_points: [
    {
      id: 1,
      name: "Lake Fork Dam Bank Access",
      latitude: 32.83,
      longitude: -95.57,
      access_type: "bank",
      public_status: "confirmed_public",
      parking: true,
    },
  ],
  species: [
    {
      common_name: "Largemouth Bass",
      difficulty: "beginner",
      confidence: "confirmed",
      evidence: "TPWD lake page",
      source_url: "https://tpwd.texas.gov/fork",
      observed_at: "2026-09-01T00:00:00Z",
    },
  ],
};

describe("WaterbodyPanel", () => {
  beforeEach(() => {
    vi.mocked(getWaterbody).mockReset();
  });

  it("shows the empty-state prompt when nothing is selected", () => {
    render(<WaterbodyPanel waterbodyId={null} />);
    expect(screen.getByText(/click a lake marker/i)).toBeInTheDocument();
  });

  it("renders lake details, access points, and species once loaded", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(screen.getByText("Lake Fork")).toBeInTheDocument());

    expect(screen.getByText("field-tested")).toBeInTheDocument();
    expect(screen.getByText(/Lake Fork Dam Bank Access/)).toBeInTheDocument();
    expect(screen.getByText("Largemouth Bass")).toBeInTheDocument();
    expect(screen.getByText("confirmed")).toBeInTheDocument();
  });

  it("surfaces the API's own error message when the fetch fails", async () => {
    vi.mocked(getWaterbody).mockRejectedValue(new ApiError("boom", 500));
    render(<WaterbodyPanel waterbodyId={2} />);

    await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
    expect(screen.queryByText("Lake Fork")).not.toBeInTheDocument();
  });

  it("falls back to a generic message for a non-API error (e.g. network failure)", async () => {
    vi.mocked(getWaterbody).mockRejectedValue(new TypeError("fetch failed"));
    render(<WaterbodyPanel waterbodyId={2} />);

    await waitFor(() =>
      expect(screen.getByText("Could not load lake details.")).toBeInTheDocument(),
    );
  });

  it("never shows a species list built by assuming a statewide species list applies", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({ ...mockDetail, id: 3, species: [] });
    render(<WaterbodyPanel waterbodyId={3} />);

    await waitFor(() =>
      expect(screen.getByText(/never assumed from a statewide list/i)).toBeInTheDocument(),
    );
  });
});
