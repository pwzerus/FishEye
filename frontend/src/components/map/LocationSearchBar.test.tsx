import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { GeocodeResult } from "@/lib/api/types";
import { LocationSearchBar } from "./LocationSearchBar";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return {
    ...actual,
    geocodePlace: vi.fn(),
  };
});

const { geocodePlace } = await import("@/lib/api/client");

const mockResult: GeocodeResult = {
  query: "Lake Fork",
  display_name: "Lake Fork Reservoir, Wood County, Texas, United States",
  latitude: 32.8065,
  longitude: -95.5931,
};

function search(text: string) {
  fireEvent.change(screen.getByLabelText("Search for a location"), {
    target: { value: text },
  });
  fireEvent.click(screen.getByRole("button", { name: /search/i }));
}

describe("LocationSearchBar", () => {
  beforeEach(() => {
    vi.mocked(geocodePlace).mockReset();
  });

  it("geocodes the typed query and reports the resolved point", async () => {
    vi.mocked(geocodePlace).mockResolvedValue(mockResult);
    const onLocate = vi.fn();
    render(<LocationSearchBar onLocate={onLocate} />);

    search("Lake Fork");

    await waitFor(() =>
      expect(onLocate).toHaveBeenCalledWith({
        latitude: 32.8065,
        longitude: -95.5931,
        label: mockResult.display_name,
      }),
    );
    expect(geocodePlace).toHaveBeenCalledWith("Lake Fork");
  });

  it("does not search on a query that's too short to mean anything", () => {
    const onLocate = vi.fn();
    render(<LocationSearchBar onLocate={onLocate} />);

    search("a");

    expect(geocodePlace).not.toHaveBeenCalled();
    expect(onLocate).not.toHaveBeenCalled();
  });

  it("shows a not-found message on a 404, distinct from a service error", async () => {
    vi.mocked(geocodePlace).mockRejectedValue(new ApiError("not found", 404));
    render(<LocationSearchBar onLocate={vi.fn()} />);

    search("asdkfjasldkfj");

    await waitFor(() =>
      expect(screen.getByText(/couldn't find "asdkfjasldkfj"/i)).toBeInTheDocument(),
    );
  });

  it("shows a service-unavailable message on a non-404 failure", async () => {
    vi.mocked(geocodePlace).mockRejectedValue(new ApiError("boom", 503));
    render(<LocationSearchBar onLocate={vi.fn()} />);

    search("Lake Fork");

    await waitFor(() =>
      expect(screen.getByText(/temporarily unavailable/i)).toBeInTheDocument(),
    );
  });

  describe("use my location", () => {
    const originalGeolocation = navigator.geolocation;

    afterEach(() => {
      Object.defineProperty(navigator, "geolocation", {
        value: originalGeolocation,
        configurable: true,
      });
    });

    it("reports the browser's own position, with no geocoding call at all", () => {
      const getCurrentPosition = vi.fn((success: PositionCallback) => {
        success({
          coords: { latitude: 30.1, longitude: -97.7 },
        } as GeolocationPosition);
      });
      Object.defineProperty(navigator, "geolocation", {
        value: { getCurrentPosition },
        configurable: true,
      });
      const onLocate = vi.fn();
      render(<LocationSearchBar onLocate={onLocate} />);

      fireEvent.click(screen.getByRole("button", { name: /use my location/i }));

      expect(onLocate).toHaveBeenCalledWith({
        latitude: 30.1,
        longitude: -97.7,
        label: "Your location",
      });
      expect(geocodePlace).not.toHaveBeenCalled();
    });

    it("explains a denied permission without blaming the user", () => {
      const PERMISSION_DENIED = 1;
      const getCurrentPosition = vi.fn(
        (_success: PositionCallback, error: PositionErrorCallback) => {
          error({ code: PERMISSION_DENIED, PERMISSION_DENIED } as GeolocationPositionError);
        },
      );
      Object.defineProperty(navigator, "geolocation", {
        value: { getCurrentPosition },
        configurable: true,
      });
      render(<LocationSearchBar onLocate={vi.fn()} />);

      fireEvent.click(screen.getByRole("button", { name: /use my location/i }));

      expect(screen.getByText(/location access was denied/i)).toBeInTheDocument();
    });
  });
});
