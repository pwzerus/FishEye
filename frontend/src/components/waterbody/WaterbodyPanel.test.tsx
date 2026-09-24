import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type {
  AdvisorResponse,
  RecommendationResponse,
  WaterbodyDetail,
  Weather,
} from "@/lib/api/types";
import { WaterbodyPanel } from "./WaterbodyPanel";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return {
    ...actual,
    getWaterbody: vi.fn(),
    getWeather: vi.fn(),
    postRecommendations: vi.fn(),
    postAdvisorExplain: vi.fn(),
  };
});

// Imported after the mock so we get the mocked references.
const { getWaterbody, getWeather, postRecommendations, postAdvisorExplain } = await import(
  "@/lib/api/client"
);

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
  data_tier: "verified",
  water_type: null,
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
  reported_species: [],
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

const mockAdvisor: AdvisorResponse = {
  waterbody_id: 1,
  waterbody_name: "Lake Fork",
  target_species: null,
  explanation: {
    summary: "Lake Fork Dam Bank Access is the strongest option right now.",
    gear: ["A medium-power spinning rod."],
    bait: [],
    steps: ["Work the NW shore — the wind pushes bait toward it."],
    risks: [],
    sources: [{ url: "https://tpwd.texas.gov/fork", label: "Lake Fork — official source" }],
  },
  answer_source: "llm",
  confidence: 0.67,
  safety_warnings: [],
  best_time_window: null,
  candidates: [],
  weather_source: "nws",
  trace: {
    trace_id: "trace-abc-123",
    provider: "mock",
    model: "mock-advisor-v1",
    latency_ms: 4.2,
    prompt_tokens: 1014,
    completion_tokens: 227,
    estimated_cost_usd: 0,
    validation_attempts: 1,
    outcome: "ok",
    retrieved_source_count: 1,
    cache_hit: false,
  },
  generated_at: "2026-09-23T12:00:00Z",
};

describe("WaterbodyPanel", () => {
  beforeEach(() => {
    vi.mocked(getWaterbody).mockReset();
    vi.mocked(getWeather).mockReset();
    vi.mocked(postRecommendations).mockReset();
    vi.mocked(postAdvisorExplain).mockReset();
    // Default to resolved values for every test that doesn't override
    // them — this keeps the weather/recommendations calls from becoming
    // real network requests (and hanging) in tests that only care about
    // the lake-detail rendering above them.
    vi.mocked(getWeather).mockResolvedValue(mockWeather);
    vi.mocked(postRecommendations).mockResolvedValue(mockRecommendations);
    vi.mocked(postAdvisorExplain).mockResolvedValue(mockAdvisor);
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
    // Scoped to the species list's own entry: the same name also appears as
    // an <option> in the target-species dropdown below, so an unscoped
    // query matches two elements and fails.
    expect(screen.getByText("Largemouth Bass", { selector: "strong" })).toBeInTheDocument();
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

    // Wait for something that only exists once the recommendations have
    // actually resolved. The access-point name was a bad thing to wait on:
    // it's in the lake-detail list from the very first render, so the
    // waitFor returned before any of this had loaded.
    await waitFor(() => expect(screen.getByText("67% confidence")).toBeInTheDocument());
    expect(screen.getByText("90")).toBeInTheDocument(); // score
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
    expect(screen.queryByRole("button", { name: /explain these picks/i })).not.toBeInTheDocument();
  });

  // --- Unverified lakes (statewide OpenStreetMap layer) ---

  const osmDetail: WaterbodyDetail = {
    ...mockDetail,
    id: 7,
    name: "Lake Tawakoni",
    field_tested: false,
    public_access_status: "unknown",
    data_tier: "osm",
    water_type: "reservoir",
    source_url: "https://www.openstreetmap.org/way/2",
    access_points: [
      {
        id: 70,
        name: "Wind Point Park Ramp",
        latitude: 32.85,
        longitude: -95.95,
        access_type: "boat_ramp",
        public_status: "osm_reported",
        parking: false,
      },
    ],
    species: [],
  };

  it("labels an OpenStreetMap lake as unverified and says why", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(osmDetail);
    render(<WaterbodyPanel waterbodyId={7} />);

    await waitFor(() => expect(screen.getByText("unverified")).toBeInTheDocument());
    expect(screen.getByText(/comes from OpenStreetMap/i)).toBeInTheDocument();
    expect(screen.getByText(/no fish records for this lake yet/i)).toBeInTheDocument();
  });

  it("never presents an OpenStreetMap entrance as confirmed public access", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(osmDetail);
    render(<WaterbodyPanel waterbodyId={7} />);

    await waitFor(() =>
      expect(screen.getByText("Entrances reported on OpenStreetMap")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Confirmed public access points")).not.toBeInTheDocument();
    expect(screen.getByText("reported, not verified")).toBeInTheDocument();
    expect(screen.queryByText(/confirmed public/i)).not.toBeInTheDocument();
  });

  it("offers no AI explanation for an unverified lake", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(osmDetail);
    render(<WaterbodyPanel waterbodyId={7} />);

    await waitFor(() => expect(screen.getByText("unverified")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /explain these picks/i })).not.toBeInTheDocument();
    // Weather still shows: it's official NWS data about a location, not a
    // claim about the lake.
    await waitFor(() => expect(getWeather).toHaveBeenCalledWith(osmDetail.latitude, osmDetail.longitude));
  });

  it("warns that a pond may be on private land", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...osmDetail,
      id: 8,
      name: "Bee Creek Park Pond",
      water_type: "pond",
    });
    render(<WaterbodyPanel waterbodyId={8} />);

    await waitFor(() => expect(screen.getByText("unverified")).toBeInTheDocument());
    expect(screen.getByText(/many ponds are on private land/i)).toBeInTheDocument();
  });

  it("does not show the pond warning for an unverified reservoir", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(osmDetail);
    render(<WaterbodyPanel waterbodyId={7} />);

    await waitFor(() => expect(screen.getByText("unverified")).toBeInTheDocument());
    expect(screen.queryByText(/many ponds are on private land/i)).not.toBeInTheDocument();
  });

  it("does not show the unverified banner for a verified lake", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(screen.getByText("Lake Fork")).toBeInTheDocument());
    expect(screen.queryByText("unverified")).not.toBeInTheDocument();
    expect(screen.queryByText(/comes from OpenStreetMap/i)).not.toBeInTheDocument();
  });

  // --- AI advisor panel ---

  it("does not call the advisor until the user asks for an explanation", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(postRecommendations).toHaveBeenCalled());
    // The ranking loads on its own; the written explanation costs tokens,
    // so it waits to be asked for.
    expect(postAdvisorExplain).not.toHaveBeenCalled();
  });

  it("requests and renders an explanation when asked", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    const button = await screen.findByRole("button", { name: /explain these picks/i });
    fireEvent.click(button);

    await waitFor(() =>
      expect(
        screen.getByText(/Lake Fork Dam Bank Access is the strongest option/),
      ).toBeInTheDocument(),
    );
    expect(postAdvisorExplain).toHaveBeenCalledWith({
      waterbody_id: 1,
      target_species: undefined,
    });
    expect(screen.getByText(/Work the NW shore/)).toBeInTheDocument();
  });

  it("asks the advisor about the same species the ranking is using", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    const select = await screen.findByLabelText(/target species/i);
    fireEvent.change(select, { target: { value: "Largemouth Bass" } });
    fireEvent.click(await screen.findByRole("button", { name: /explain these picks/i }));

    // The two panels must never disagree about which fish is being asked
    // about — that would be a quiet, plausible-looking bug.
    await waitFor(() =>
      expect(postAdvisorExplain).toHaveBeenCalledWith({
        waterbody_id: 1,
        target_species: "Largemouth Bass",
      }),
    );
  });

  it("labels a mock-model answer as such", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);
    fireEvent.click(await screen.findByRole("button", { name: /explain these picks/i }));

    // Mock output must never be presented as a real model's, the same way
    // fallback weather is never presented as a real reading.
    await waitFor(() => expect(screen.getByText("mock model")).toBeInTheDocument());
  });

  it("says plainly when the answer is the fixed template, and why", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    vi.mocked(postAdvisorExplain).mockResolvedValue({
      ...mockAdvisor,
      answer_source: "fallback",
      explanation: {
        ...mockAdvisor.explanation,
        summary: "Top-ranked spot on Lake Fork: Lake Fork Dam Bank Access (score 90).",
      },
      trace: { ...mockAdvisor.trace, outcome: "ungrounded_source" },
    });
    render(<WaterbodyPanel waterbodyId={1} />);
    fireEvent.click(await screen.findByRole("button", { name: /explain these picks/i }));

    await waitFor(() => expect(screen.getByText("plain summary")).toBeInTheDocument());
    // The reason is shown, not swallowed: a discarded answer is a fact
    // about this response the reader is entitled to.
    expect(
      screen.getByText(/cited a source the backend never supplied/i),
    ).toBeInTheDocument();
  });

  it("exposes the request trace on demand", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);
    fireEvent.click(await screen.findByRole("button", { name: /explain these picks/i }));

    fireEvent.click(await screen.findByRole("button", { name: /show request trace/i }));

    expect(screen.getByText("trace-abc-123")).toBeInTheDocument();
    expect(screen.getByText("mock / mock-advisor-v1")).toBeInTheDocument();
    expect(screen.getByText("1014 / 227")).toBeInTheDocument();
  });

  it("surfaces an advisor error without taking the rest of the panel down", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    vi.mocked(postAdvisorExplain).mockRejectedValue(new ApiError("advisor exploded", 500));
    render(<WaterbodyPanel waterbodyId={1} />);
    fireEvent.click(await screen.findByRole("button", { name: /explain these picks/i }));

    await waitFor(() => expect(screen.getByText("advisor exploded")).toBeInTheDocument());
    // The ranking above is unaffected — it never depended on the advisor.
    expect(screen.getAllByText(/Lake Fork Dam Bank Access/).length).toBeGreaterThan(0);
  });
  // --- Species on record (GBIF): never presented as confirmed ---

  const bassOnRecord = {
    common_name: "Largemouth Bass",
    records: 37,
    last_year: 2023,
    sources: [
      { name: "Fishes of Texas (UT Austin)", records: 30 },
      { name: "iNaturalist", records: 7 },
    ],
    latest_record_url: "https://www.gbif.org/occurrence/1",
    weak: false,
    also_confirmed: false,
  };
  const oldCatfish = {
    common_name: "Channel Catfish",
    records: 1,
    last_year: 1968,
    sources: [{ name: "Fishes of Texas (UT Austin)", records: 1 }],
    latest_record_url: "https://www.gbif.org/occurrence/2",
    weak: true,
    also_confirmed: false,
  };

  it("shows an unverified lake's fish records with their strength and sources", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({ ...osmDetail, reported_species: [bassOnRecord, oldCatfish] });
    render(<WaterbodyPanel waterbodyId={7} />);

    await waitFor(() => expect(screen.getByText("Fish on record (not verified)")).toBeInTheDocument());
    expect(screen.getByText("37 records · last recorded 2023")).toBeInTheDocument();
    expect(screen.getByText("Fishes of Texas (UT Austin) 30 · iNaturalist 7")).toBeInTheDocument();
    expect(screen.getByText("Weak evidence: a single record from 1968.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /latest record on GBIF/i })[0]).toHaveAttribute(
      "href",
      "https://www.gbif.org/occurrence/1",
    );
    // Never the official confidence badge.
    expect(screen.queryByText("confirmed")).not.toBeInTheDocument();
    expect(screen.getAllByText("on record")).toHaveLength(2);
  });

  it("lists only the species a verified lake's official survey doesn't mention", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...mockDetail,
      reported_species: [{ ...bassOnRecord, also_confirmed: true }, { ...oldCatfish, common_name: "Striped Bass" }],
    });
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() =>
      expect(screen.getByText("Also on record (not in the official survey)")).toBeInTheDocument(),
    );
    const section = screen.getByRole("region", { name: "Fish on record" });
    expect(section).toHaveTextContent("Striped Bass");
    expect(section).not.toHaveTextContent("Largemouth Bass");
  });

  it("adds no records section to a verified lake when every record is already confirmed", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...mockDetail,
      reported_species: [{ ...bassOnRecord, also_confirmed: true }],
    });
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(screen.getByText("Lake Fork")).toBeInTheDocument());
    expect(screen.queryByRole("region", { name: "Fish on record" })).not.toBeInTheDocument();
  });
});
