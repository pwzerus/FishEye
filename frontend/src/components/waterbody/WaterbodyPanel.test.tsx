import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type {
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
    listShopsNear: vi.fn(),
  };
});

// Imported after the mock so we get the mocked references.
const { getWaterbody, getWeather, listShopsNear, postRecommendations } = await import("@/lib/api/client");

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
  plan: {
    species: "Largemouth Bass",
    species_options: ["Largemouth Bass", "Bluegill"],
    species_on_record: true,
    where: { shore: "NW", text: "Try the NW bank. The SE wind is pushing baitfish toward it." },
    when: { start_time: "2026-09-22T18:00:00-05:00", end_time: "2026-09-22T21:00:00-05:00", label: "evening" },
    also: null,
    conditions: "78°F, partly sunny, SE wind 10 mph",
    lures: [{ name: "Topwater lures", why: "Low light at dusk: bass come up and hit surface lures." }],
    baits: [{ name: "Large live shiners (8–9 in) under a bobber", why: "Fish it next to cover." }],
    lure_note: null,
    heads_up: [],
  },
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
    vi.mocked(listShopsNear).mockReset();
    vi.mocked(listShopsNear).mockResolvedValue([]);
  });

  it("names the nearest bait and tackle shops, with how far they are", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    vi.mocked(listShopsNear).mockResolvedValue([
      {
        id: 4, name: "Lake Fork Marina Bait", kind: "bait", latitude: 32.81, longitude: -95.59, address: null,
        phone: null, website: null, opening_hours: null, osm_url: "https://www.openstreetmap.org/node/4", distance_km: 3.2,
      },
    ]);
    render(<WaterbodyPanel waterbodyId={1} />);
    expect(await screen.findByText("Lake Fork Marina Bait")).toBeInTheDocument();
    expect(screen.getByText(/2\.0 mi away/)).toBeInTheDocument();
    expect(listShopsNear).toHaveBeenCalledWith(32.8, -95.6);
  });

  it("shows the empty-state prompt when nothing is selected", () => {
    render(<WaterbodyPanel waterbodyId={null} />);
    expect(screen.getByText(/search a place or choose a highlighted state/i)).toBeInTheDocument();
  });

  it("retries a failed lake without reloading the map", async () => {
    vi.mocked(getWaterbody).mockRejectedValueOnce(new ApiError("Try later", 503)).mockResolvedValueOnce(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);
    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Lake Fork")).toBeInTheDocument();
    expect(getWaterbody).toHaveBeenCalledTimes(2);
  });

  it("does not show one lake's error while loading another lake", async () => {
    vi.mocked(getWaterbody).mockRejectedValueOnce(new ApiError("First lake unavailable", 503)).mockResolvedValueOnce({ ...mockDetail, id: 2 });
    const page = render(<WaterbodyPanel waterbodyId={1} />);
    await screen.findByText("First lake unavailable");
    page.rerender(<WaterbodyPanel waterbodyId={2} />);
    expect(screen.queryByText("First lake unavailable")).not.toBeInTheDocument();
    expect(await screen.findByText("Lake Fork")).toBeInTheDocument();
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

  it("gives each keyed part of the panel its own key (React warns when siblings share one)", async () => {
    // The access list and the weather block are both keyed by lake so they
    // reset when the lake changes; with the same bare id they collided.
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);
    await waitFor(() => expect(screen.getByText("Lake Fork")).toBeInTheDocument());

    const keyWarnings = errors.mock.calls.filter((call) => String(call[0]).includes("same key"));
    errors.mockRestore();
    expect(keyWarnings).toEqual([]);
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
    expect(postRecommendations).toHaveBeenCalledWith({ waterbody_id: 1, target_species: undefined });
  });

  it("shows current conditions once weather resolves", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(screen.getByText("Partly Sunny")).toBeInTheDocument());
    expect(screen.getByText("78°F")).toBeInTheDocument();
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

  it("doesn't rank spots: weather and best times only", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    // Wait for the weather panel to have resolved, so the absence checked
    // below isn't just "hasn't loaded yet".
    await waitFor(() => expect(screen.getByText("Partly Sunny")).toBeInTheDocument());
    expect(screen.queryByText(/recommended spots/i)).not.toBeInTheDocument();
    // The access point appears once, in the lake's own list, not again as a ranked card.
    expect(screen.getAllByText(/Lake Fork Dam Bank Access/)).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /explain these picks/i })).not.toBeInTheDocument();
  });

  it("surfaces severe weather warnings", async () => {
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

  it("shows today's plan: where, when, lures and bait", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    await waitFor(() => expect(screen.getByText(/Try the NW bank/)).toBeInTheDocument());
    expect(screen.getByText("Topwater lures")).toBeInTheDocument();
    expect(screen.getByText("Large live shiners (8–9 in) under a bobber")).toBeInTheDocument();
    expect(screen.getByText(/Evening bite, 6–9 PM/)).toBeInTheDocument();
  });

  it("asks for a new plan when the fish changes", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(mockDetail);
    render(<WaterbodyPanel waterbodyId={1} />);

    const select = await screen.findByLabelText(/fishing for/i);
    fireEvent.change(select, { target: { value: "Bluegill" } });

    await waitFor(() =>
      expect(postRecommendations).toHaveBeenLastCalledWith({ waterbody_id: 1, target_species: "Bluegill" }),
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
      expect(screen.getByText(/Closed to public access\./i)).toBeInTheDocument(),
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
    expect(screen.getByText(/unverified lake from OpenStreetMap/i)).toBeInTheDocument();
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

  it("still shows weather for an unverified lake", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(osmDetail);
    render(<WaterbodyPanel waterbodyId={7} />);

    await waitFor(() => expect(screen.getByText("unverified")).toBeInTheDocument());
    // Weather still shows: it's official NWS data about a location, not a
    // claim about the lake.
    await waitFor(() => expect(getWeather).toHaveBeenCalledWith(osmDetail.latitude, osmDetail.longitude));
  });

  it("warns that a pond with no reported entrance may be on private land", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...osmDetail,
      id: 8,
      name: "Bee Creek Park Pond",
      water_type: "pond",
      access_points: [],
    });
    render(<WaterbodyPanel waterbodyId={8} />);

    await waitFor(() => expect(screen.getByText("unverified")).toBeInTheDocument());
    expect(screen.getByText(/many ponds are on private land/i)).toBeInTheDocument();
  });

  it("gives a pond with a reported entrance only the short banner", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...osmDetail,
      id: 9,
      name: "Park Pond",
      water_type: "pond",
    });
    render(<WaterbodyPanel waterbodyId={9} />);

    await waitFor(() => expect(screen.getByText("unverified")).toBeInTheDocument());
    expect(screen.getByText(/unverified lake from OpenStreetMap/i)).toBeInTheDocument();
    expect(screen.queryByText(/many ponds are on private land/i)).not.toBeInTheDocument();
  });

  it("says clearly private lakes are left out but some private ones may remain", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(osmDetail);
    render(<WaterbodyPanel waterbodyId={7} />);

    await waitFor(() => expect(screen.getByText("unverified")).toBeInTheDocument());
    expect(screen.getByText(/some may remain/i)).toBeInTheDocument();
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
    expect(screen.queryByText(/lake from OpenStreetMap/i)).not.toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("tab", { name: "Fish" }));
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
    fireEvent.click(screen.getByRole("tab", { name: "Fish" }));
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
  // --- What the state agency says (TPWD lake page and survey) ---

  const profiled: WaterbodyDetail = {
    ...mockDetail,
    id: 9,
    name: "Lake Somerville",
    agency_profile: {
      agency: "tpwd",
      agency_name: "Lake Somerville",
      page_url: "https://tpwd.texas.gov/fishboat/fish/recreational/lakes/somerville/",
      access_page_url: "https://tpwd.texas.gov/fishboat/fish/recreational/lakes/somerville/access.phtml",
      survey_report_url: "https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1374/",
      survey_year: 2020,
      location: "On Yegua Creek in Washington County",
      surface_acres: 11456,
      max_depth_ft: 38,
      impounded: "1967",
      predominant_species: ["Largemouth bass", "White & black crappie"],
      ratings: [
        { label: "Largemouth Bass", rating: "Excellent" },
        { label: "Crappie", rating: "Good" },
      ],
      placement: "osm_name",
    },
  };

  it("shows the agency's ratings, facts and links, credited to the agency", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(profiled);
    render(<WaterbodyPanel waterbodyId={9} />);

    await waitFor(() => expect(screen.getByText("From Texas Parks & Wildlife")).toBeInTheDocument());
    expect(screen.getByText(/11,456 acres · up to 38 ft deep · impounded 1967/)).toBeInTheDocument();
    expect(screen.getByLabelText("Excellent, 4 of 4")).toBeInTheDocument();
    expect(screen.getByLabelText("Good, 3 of 4")).toBeInTheDocument();
    expect(screen.getByText("2020 survey report").closest("a")).toHaveAttribute(
      "href",
      "https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1374/",
    );
    expect(screen.queryByText(/marker is near the shore/)).not.toBeInTheDocument();
  });

  it("says when a lake is plotted at its boat ramps", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...profiled,
      agency_profile: { ...profiled.agency_profile!, placement: "ramps" },
    });
    render(<WaterbodyPanel waterbodyId={9} />);
    await waitFor(() => expect(screen.getByText(/marker is near the shore/)).toBeInTheDocument());
  });

  it("doesn't call a verified lake's OpenStreetMap entrances confirmed", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...profiled,
      access_points: [{ ...osmDetail.access_points[0] }],
    });
    render(<WaterbodyPanel waterbodyId={9} />);
    await waitFor(() => expect(screen.getByText("Public access points")).toBeInTheDocument());
    expect(screen.queryByText("Confirmed public access points")).not.toBeInTheDocument();
    expect(screen.getByText("reported, not verified")).toBeInTheDocument();
  });
  it("shows a few of a big lake's ramps and the rest on request", async () => {
    const ramps = Array.from({ length: 12 }, (_, i) => ({
      id: 100 + i,
      name: `Public boat ramp (TPWD #${i})`,
      latitude: 31,
      longitude: -94,
      access_type: "boat_ramp",
      public_status: "confirmed_public",
      parking: false,
    }));
    vi.mocked(getWaterbody).mockResolvedValue({ ...profiled, access_points: ramps });
    render(<WaterbodyPanel waterbodyId={9} />);

    await waitFor(() => expect(screen.getByText("Public boat ramp (TPWD #0)")).toBeInTheDocument());
    expect(screen.queryByText("Public boat ramp (TPWD #5)")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show all 12" }));
    expect(screen.getByText("Public boat ramp (TPWD #11)")).toBeInTheDocument();
  });
  // --- Georgia WRD: access sites, forecast link, fish attractors ---

  const georgia: WaterbodyDetail = {
    ...mockDetail,
    id: 21,
    name: "Lake Lanier",
    agency_profile: {
      agency: "ga_wrd",
      agency_name: "Lake Sidney Lanier",
      page_url: "https://storymaps.arcgis.com/stories/bf90dbefc6d34795a96fdc0181e746d9",
      access_page_url: "https://georgiawildlife.com/locations/fishing",
      survey_report_url: null,
      survey_year: null,
      location: "Forsyth, Hall Counties",
      surface_acres: 38000,
      max_depth_ft: null,
      impounded: null,
      predominant_species: ["Largemouth bass", "Spotted bass", "Striped bass"],
      ratings: [],
      placement: "osm_name",
    },
    fish_attractors: [
      { id: 1, latitude: 34.2, longitude: -83.9, attractor_type: "Trees/Brush", units: 1, depth_ft: 15, placed_year: 2017, source: "ga_wrd" },
      { id: 2, latitude: 34.21, longitude: -83.91, attractor_type: "PVC Trees", units: 1, depth_ft: null, placed_year: 2023, source: "ga_wrd" },
    ],
  };

  it("credits Georgia WRD and links its fishing forecast", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(georgia);
    render(<WaterbodyPanel waterbodyId={21} />);
    await waitFor(() => expect(screen.getByText("From Georgia WRD")).toBeInTheDocument());
    expect(screen.getByText("WRD fishing forecast").closest("a")).toHaveAttribute(
      "href",
      "https://storymaps.arcgis.com/stories/bf90dbefc6d34795a96fdc0181e746d9",
    );
    expect(screen.getByText("WRD fishing map").closest("a")).toHaveAttribute("href", "https://georgiawildlife.com/locations/fishing");
    expect(screen.getByText(/Fish WRD lists at its access sites/)).toBeInTheDocument();
  });

  it("says how many fish attractors WRD sank and when", async () => {
    vi.mocked(getWaterbody).mockResolvedValue(georgia);
    render(<WaterbodyPanel waterbodyId={21} />);
    await waitFor(() => expect(screen.getByText("Fish attractors")).toBeInTheDocument());
    expect(screen.getByText(/2 fish-holding structures by Georgia WRD, placed 2017–2023/)).toBeInTheDocument();
  });

  it("shows no attractor section on a lake without any, or on a closed lake", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({ ...georgia, public_access_status: "closed" });
    render(<WaterbodyPanel waterbodyId={21} />);
    await waitFor(() => expect(screen.getByText("Lake Lanier")).toBeInTheDocument());
    expect(screen.queryByText("Fish attractors")).not.toBeInTheDocument();
  });

  it("says when a lake is plotted at WRD's access sites", async () => {
    vi.mocked(getWaterbody).mockResolvedValue({
      ...georgia,
      agency_profile: { ...georgia.agency_profile!, placement: "sites", page_url: "https://georgiawildlife.com/locations/fishing", access_page_url: null },
    });
    render(<WaterbodyPanel waterbodyId={21} />);
    await waitFor(() => expect(screen.getByText(/Georgia WRD's access sites: this lake has no outline/)).toBeInTheDocument());
    expect(screen.getByText("WRD fishing map")).toBeInTheDocument();
  });

  describe("facts with links (data-sourcing rule 3)", () => {
    const california: WaterbodyDetail = {
      ...mockDetail,
      id: 31,
      name: "Lake Natoma",
      source_url: "https://www.openstreetmap.org/way/1",
      data_tier: "verified",
      field_tested: false,
      data_credit: "Data: California Department of Fish and Wildlife",
      official_name: "Natoma Lake",
      public_land: "open",
      public_land_name: "Folsom Lake State Recreation Area",
      public_land_manager: "State Park",
      species: [
        {
          common_name: "Rainbow Trout",
          difficulty: "beginner",
          confidence: "confirmed",
          evidence: "CDFW's 2026 stocking plan lists Rainbow Trout for this water.",
          source_url: "https://nrm.dfg.ca.gov/plan",
          observed_at: "2026-01-01T00:00:00Z",
          evidence_items: [
            { evidence: "CDFW's fish planting schedule lists trout planted here the week of January 4, 2026.", source_url: "https://nrm.dfg.ca.gov/FishPlants/PublicPlantSearch?Params.StockingWaterID=2700", kind: "stocking", year: 2026, publisher: "California Department of Fish and Wildlife" },
            { evidence: "CDFW's 2026 stocking plan lists Rainbow Trout for this water.", source_url: "https://nrm.dfg.ca.gov/plan", kind: "stocking_plan", year: 2026, publisher: "California Department of Fish and Wildlife" },
          ],
        },
      ],
      sources: [
        { title: "Recent Stocked Waters - California [ds778]", publisher: "California Department of Fish and Wildlife", licence: "CC BY 4.0", citation: "Cited as BIOS asks", url: "https://filelib.wildlife.ca.gov/ds778.zip" },
      ],
    };

    it("links every fact behind a species to its source", async () => {
      vi.mocked(getWaterbody).mockResolvedValue(california);
      render(<WaterbodyPanel waterbodyId={31} />);
      await waitFor(() => expect(screen.getByText("Rainbow Trout")).toBeInTheDocument());
      const links = screen.getAllByText("Source ↗").map((a) => a.closest("a"));
      expect(links.map((a) => a?.getAttribute("href"))).toEqual([
        "https://nrm.dfg.ca.gov/FishPlants/PublicPlantSearch?Params.StockingWaterID=2700",
        "https://nrm.dfg.ca.gov/plan",
      ]);
      expect(links.every((a) => a?.getAttribute("target") === "_blank")).toBe(true);
    });

    it("credits the datasets, the agency and OpenStreetMap on the Sources tab", async () => {
      vi.mocked(getWaterbody).mockResolvedValue(california);
      render(<WaterbodyPanel waterbodyId={31} />);
      await waitFor(() => expect(screen.getByText("Lake Natoma")).toBeInTheDocument());
      expect(screen.getByText("Official name: Natoma Lake")).toBeInTheDocument();
      expect(screen.getByText("Data: California Department of Fish and Wildlife")).toBeInTheDocument();
      expect(screen.getByText("Map data © OpenStreetMap contributors (ODbL)")).toBeInTheDocument();
      expect(screen.getByText("Recent Stocked Waters - California [ds778]").closest("a")).toHaveAttribute("href", "https://filelib.wildlife.ca.gov/ds778.zip");
      expect(screen.getByText(/CC BY 4.0/)).toBeInTheDocument();
    });

    it("says a verified lake lies on public land, from PAD-US", async () => {
      vi.mocked(getWaterbody).mockResolvedValue(california);
      render(<WaterbodyPanel waterbodyId={31} />);
      await waitFor(() => expect(screen.getByText(/in Folsom Lake State Recreation Area \(State Park\), land open to the public \(PAD-US\)/)).toBeInTheDocument());
    });

    it("tells an unverified lake on public land apart from one that may be private", async () => {
      const onForest: WaterbodyDetail = {
        ...mockDetail, id: 32, name: "Frog Lake", data_tier: "osm", public_access_status: "unknown", water_type: "pond",
        field_tested: false, access_points: [], species: [],
        source_url: "https://services2.arcgis.com/x/CA_Lakes_wm/FeatureServer/0/query?where=DFGWATERID%3D9001",
        public_land: "open", public_land_name: "Stanislaus National Forest", public_land_manager: "Forest Service",
      };
      vi.mocked(getWaterbody).mockResolvedValue(onForest);
      render(<WaterbodyPanel waterbodyId={32} />);
      await waitFor(() => expect(screen.getByText("Unverified lake from CDFW's California Lakes map.")).toBeInTheDocument());
      expect(screen.getByText(/in Stanislaus National Forest \(Forest Service\), land open to the public/)).toBeInTheDocument();
      // On open public land, the private-pond warning doesn't apply.
      expect(screen.queryByText(/Many ponds are on private land/)).not.toBeInTheDocument();
    });

    it("lists fish an official source names on an unverified lake", async () => {
      const recorded: WaterbodyDetail = {
        ...california, id: 33, data_tier: "osm", public_access_status: "unknown", public_land: null,
        species: [{ ...california.species[0], common_name: "Brook Trout", evidence_items: [] }],
      };
      vi.mocked(getWaterbody).mockResolvedValue(recorded);
      render(<WaterbodyPanel waterbodyId={33} />);
      await waitFor(() => expect(screen.getByText("Fish named by official sources")).toBeInTheDocument());
      expect(screen.getByText("Brook Trout")).toBeInTheDocument();
      expect(screen.getByText("Source ↗").closest("a")).toHaveAttribute("href", "https://nrm.dfg.ca.gov/plan");
    });
  });
});
