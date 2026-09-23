import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { RecommendationResponse, WaterbodyDetail, Weather } from "@/lib/api/types";
import { WaterbodyPanel } from "./WaterbodyPanel";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return {
    ...actual,
    getWaterbody: vi.fn(),
    getWeather: vi.fn(),
    postRecommendations: vi.fn(),
  };
});

// Imported after the mock so we get the mocked references.
const { getWaterbody, getWeather, postRecommendations } = await import("@/lib/api/client");

const mockDetail: WaterbodyDetail = {
  id: 1,
  name: "Lake Fork",
  latitude: 32.8,
  longitude: -95.6,
  access_summary: "A great bass lake.",
  source_url: "https://tpwd.texas.gov/fork",
  source_updated_at: "2026-09-01T00:00:00Z",
  field_tested: true,
  public_access_status: "open",
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

const mockWeather: Weather = {
  latitude: 32.8,
  longitude: -95.6,
  current: {
    temperature: 78,
    temperature_unit: "F",
    wind_speed: "10 mph",
    wind_direction: "SE",
    short_forecast: "Partly Sunny",
    is_daytime: true,
  },
  hourly: [],
  alerts: [],
  source: "nws",
  stale: false,
  fetched_at: "2026-09-22T12:00:00Z",
};

const mockRecommendations: RecommendationResponse = {
  waterbody_id: 1,
  waterbody_name: "Lake Fork",
  target_species: null,
  candidates: [
    {
      access_point_id: 1,
      name: "Lake Fork Dam Bank Access",
      latitude: 32.83,
      longitude: -95.57,
      access_type: "bank",
      public_access_status: "confirmed_public",
      score: 0.9,
      confidence: 0.67,
      factors: [
        { name: "access", weight: 0.3, value: 1.0, reason: "confirmed public bank access" },
        { name: "habitat", weight: 0.25, value: null, reason: "no bathymetry data" },
      ],
      missing_signals: ["habitat"],
    },
  ],
  best_time_window: null,
  safety_warnings: [],
  weather_source: "nws",
  generated_at: "2026-09-22T12:00:00Z",
};

describe("WaterbodyPanel", () => {
  beforeEach(() => {
    vi.mocked(getWaterbody).mockReset();
    vi.mocked(getWeather).mockReset();
    vi.mocked(postRecommendations).mockReset();
    // Default to resolved values for every test that doesn't override
    // them — this keeps the weather/recommendations calls from becoming
    // real network requests (and hanging) in tests that only care about
    // the lake-detail rendering above them.
    vi.mocked(getWeather).mockResolvedValue(mockWeather);
    vi.mocked(postRecommendations).mockResolvedValue(mockRecommendations);
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

  it("requests weather and recommendations for the selected lake's own coordinates", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(getWeather).toHaveBeenCalledWith(32.8, -95.6));
    expect(postRecommendations).toHaveBeenCalledWith({
      waterbody_id: 1,
      target_species: undefined,
    });
  });

  it("shows current conditions once weather resolves", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(screen.getByText("Partly Sunny")).toBeInTheDocument());
    expect(screen.getByText(/78°F/)).toBeInTheDocument();
  });

  it("shows a plain notice instead of fake readings when weather falls back", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    vi.mocked(getWeather).mockResolvedValue({
      ...mockWeather,
      current: {
        temperature: null,
        temperature_unit: "F",
        wind_speed: null,
        wind_direction: null,
        short_forecast: "Weather data temporarily unavailable",
        is_daytime: true,
      },
      source: "fallback",
      stale: true,
    });
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/weather data is temporarily unavailable/i)).toBeInTheDocument(),
    );
    // The fallback forecast text must not be presented as if it were real.
    expect(screen.queryByText("Weather data temporarily unavailable")).not.toBeInTheDocument();
  });

  it("renders ranked candidates with their score and confidence", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() =>
      expect(screen.getAllByText(/Lake Fork Dam Bank Access/).length).toBeGreaterThan(0),
    );
    expect(screen.getByText("90")).toBeInTheDocument(); // score
    expect(screen.getByText("67% confidence")).toBeInTheDocument();
  });

  it("surfaces severe weather warnings above the candidate list", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    vi.mocked(postRecommendations).mockResolvedValue({
      ...mockRecommendations,
      safety_warnings: [
        { event: "Severe Thunderstorm Warning", severity: "Severe", headline: "Until 8 PM" },
      ],
    });
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() =>
      expect(screen.getByText("Severe Thunderstorm Warning")).toBeInTheDocument(),
    );
  });

  it("re-requests recommendations when the target species changes", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(postRecommendations).toHaveBeenCalledTimes(1));

    const select = await screen.findByLabelText(/target species/i);
    fireEvent.change(select, { target: { value: "Largemouth Bass" } });

    await waitFor(() =>
      expect(postRecommendations).toHaveBeenLastCalledWith({
        waterbody_id: 1,
        target_species: "Largemouth Bass",
      }),
    );
  });

  it("shows a closed-to-the-public banner instead of recommendations for a closed lake", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...mockDetail,
      id: 4,
      public_access_status: "closed",
      access_points: [],
    });
    render(<WaterbodyPanel waterbodyId={4} />);

    await waitFor(() =>
      expect(screen.getByText(/currently closed to public access/i)).toBeInTheDocument(),
    );
    expect(screen.getByText("closed to the public")).toBeInTheDocument();
    // No point scoring recommendations for a lake nobody can legally fish.
    expect(postRecommendations).not.toHaveBeenCalled();
    expect(getWeather).not.toHaveBeenCalled();
  });
});
