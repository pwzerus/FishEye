import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { GeocodeResult } from "@/lib/api/types";
import { suggestPlaces } from "@/lib/usCities";
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

describe("Chinese names", () => {
  it("suggests a city typed in Chinese, under its English name", () => {
    expect(suggestPlaces("纽约")).toEqual(["New York, NY"]);
    expect(suggestPlaces("圣")).toContain("San Diego, CA");
    expect(suggestPlaces("不存在的地方")).toEqual([]);
  });
});

describe("LocationSearchBar", () => {
  beforeEach(() => {
    vi.mocked(geocodePlace).mockReset();
  });

  it("offers places as you type and searches the one picked", async () => {
    vi.mocked(geocodePlace).mockResolvedValue(mockResult);
    const onLocate = vi.fn();
    render(<LocationSearchBar onLocate={onLocate} />);
    fireEvent.change(screen.getByLabelText("Search for a location"), { target: { value: "s" } });
    const names = screen.getAllByRole("option").map((o) => o.textContent);
    expect(names).toEqual(expect.arrayContaining(["San Antonio, TX", "San Diego, CA"]));
    fireEvent.click(screen.getByRole("option", { name: "San Diego, CA" }));
    await waitFor(() => expect(geocodePlace).toHaveBeenCalledWith("San Diego, CA"));
    await waitFor(() => expect(onLocate).toHaveBeenCalled());
    expect(screen.queryByRole("option")).not.toBeInTheDocument();
  });

  it("goes through the suggestions with the arrow keys", async () => {
    vi.mocked(geocodePlace).mockResolvedValue(mockResult);
    render(<LocationSearchBar onLocate={vi.fn()} />);
    const box = screen.getByLabelText("Search for a location");
    fireEvent.change(box, { target: { value: "seat" } });
    fireEvent.keyDown(box, { key: "ArrowDown" });
    expect(screen.getByRole("option", { name: "Seattle, WA" })).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(box, { key: "Enter" });
    await waitFor(() => expect(geocodePlace).toHaveBeenCalledWith("Seattle, WA"));
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

  it("shows the server's message when the search limit is hit", async () => {
    vi.mocked(geocodePlace).mockRejectedValue(
      new ApiError("Please wait a moment and try again.", 429, "rate_limited"),
    );
    render(<LocationSearchBar onLocate={vi.fn()} />);

    search("Lake Fork");

    await waitFor(() =>
      expect(screen.getByText("Please wait a moment and try again.")).toBeInTheDocument(),
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
          coords: { latitude: 30.1, longitude: -97.7, accuracy: 35 },
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
        own: { accuracy: 35 },
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
