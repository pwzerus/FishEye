import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LakeMatch } from "@/lib/api/types";
import { LocationSearchBar, clearPick, splitState } from "./LocationSearchBar";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, geocodePlace: vi.fn(), searchLakes: vi.fn(), listJurisdictions: vi.fn(async () => STATES) };
});
const { ApiError, geocodePlace, searchLakes } = await import("@/lib/api/client");

const NO_RULES = { covered: false, agency: null, agency_short: null, limits_url: null, license_url: null,
  bait_rules: [], bait_rules_sources: [], bait_rules_on_every_bait_question: false };
const STATES = [
  { ...NO_RULES, code: "GA", name: "Georgia" },
  { ...NO_RULES, code: "KY", name: "Kentucky" },
  { ...NO_RULES, code: "VA", name: "Virginia" },
  { ...NO_RULES, code: "WV", name: "West Virginia" },
  { ...NO_RULES, code: "OR", name: "Oregon" },
];

const match = (id: number, name: string, state_code: string, state_name: string): LakeMatch => ({
  id, name, latitude: 33.9, longitude: -84.1, state_code, state_name, data_tier: "osm",
});
const GA_FREEMAN = match(1, "Freeman Lake", "GA", "Georgia");
const KY_FREEMAN = match(2, "Freeman Lake", "KY", "Kentucky");

function search(text: string) {
  fireEvent.change(screen.getByLabelText("Search for a location"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: /^search$/i }));
}

describe("splitState", () => {
  it("reads a state named at the end of a search", () => {
    expect(splitState("Freeman Lake, GA", STATES)).toEqual({ name: "Freeman Lake", state: "GA" });
    expect(splitState("Freeman Lake GA", STATES)).toEqual({ name: "Freeman Lake", state: "GA" });
    expect(splitState("freeman lake, kentucky", STATES)).toEqual({ name: "freeman lake", state: "KY" });
    expect(splitState("Summit Lake, West Virginia", STATES)).toEqual({ name: "Summit Lake", state: "WV" });
  });

  it("leaves a name alone that only ends like a state code", () => {
    expect(splitState("Lake Erie", STATES)).toEqual({ name: "Lake Erie", state: null });
    expect(splitState("fish pond or", STATES)).toEqual({ name: "fish pond or", state: null });
  });
});

describe("clearPick", () => {
  it("opens the one lake of that name in the state being looked at", () => {
    expect(clearPick([GA_FREEMAN, KY_FREEMAN], "freeman lake", "GA")).toBe(GA_FREEMAN);
    expect(clearPick([GA_FREEMAN, KY_FREEMAN], "Lake Freeman", "KY")).toBe(KY_FREEMAN);
  });

  it("asks when it can't tell", () => {
    expect(clearPick([GA_FREEMAN, KY_FREEMAN], "Freeman Lake", null)).toBeNull();
    expect(clearPick([KY_FREEMAN], "Freeman Lake", "GA")).toBeNull();
    expect(clearPick([match(3, "Freeman Lake Estates Pond", "GA", "Georgia")], "Freeman Lake", "GA")).toBeNull();
  });

  it("of several in one state, takes the only one near where the map is", () => {
    const south = { ...match(4, "Freeman Lake", "GA", "Georgia"), latitude: 31.2, longitude: -83.5 };
    const gwinnett = GA_FREEMAN;
    expect(clearPick([gwinnett, south], "Freeman Lake", "GA", { latitude: 33.91, longitude: -84.14 })).toBe(gwinnett);
    expect(clearPick([gwinnett, south], "Freeman Lake", "GA", { latitude: 32.5, longitude: -83.8 })).toBeNull();
    expect(clearPick([gwinnett, south], "Freeman Lake", "GA")).toBeNull();
  });
});

// The 2026-10-29 walkthrough: "Freeman Lake" from Georgia flew to Kentucky's.
describe("LocationSearchBar with lakes", () => {
  beforeEach(() => {
    vi.mocked(geocodePlace).mockReset();
    vi.mocked(searchLakes).mockReset();
  });

  it("opens the lake of that name in the state being looked at", async () => {
    vi.mocked(searchLakes).mockResolvedValue([GA_FREEMAN, KY_FREEMAN]);
    const onLake = vi.fn();
    render(<LocationSearchBar onLocate={vi.fn()} onLake={onLake} stateCode="GA" />);
    search("Freeman Lake");
    await waitFor(() => expect(onLake).toHaveBeenCalledWith(GA_FREEMAN));
    expect(searchLakes).toHaveBeenCalledWith("Freeman Lake", "GA", null);
    expect(geocodePlace).not.toHaveBeenCalled();
  });

  it("lists the lakes sharing a name and lets the person pick, or search places", async () => {
    vi.mocked(searchLakes).mockResolvedValue([KY_FREEMAN, GA_FREEMAN]);
    vi.mocked(geocodePlace).mockResolvedValue({ query: "Freeman Lake", display_name: "Freeman Lake, KY", latitude: 37.7, longitude: -85.9 });
    const onLake = vi.fn();
    const onLocate = vi.fn();
    render(<LocationSearchBar onLocate={onLocate} onLake={onLake} />);
    search("Freeman Lake");
    fireEvent.click(await screen.findByRole("button", { name: "Freeman Lake Georgia" }));
    expect(onLake).toHaveBeenCalledWith(GA_FREEMAN);
    expect(screen.queryByRole("list", { name: "Lakes with that name" })).not.toBeInTheDocument();

    search("Freeman Lake");
    fireEvent.click(await screen.findByRole("button", { name: "Search places instead" }));
    await waitFor(() => expect(onLocate).toHaveBeenCalled());
  });

  it("sends a town or a lake FishEye doesn't have to the place search", async () => {
    vi.mocked(searchLakes).mockResolvedValue([]);
    vi.mocked(geocodePlace).mockResolvedValue({ query: "x", display_name: "Somewhere", latitude: 1, longitude: 2 });
    const onLocate = vi.fn();
    render(<LocationSearchBar onLocate={onLocate} onLake={vi.fn()} stateCode="GA" />);
    search("Gainesville, GA");
    await waitFor(() => expect(onLocate).toHaveBeenCalledTimes(1));
    search("Lake Nowhere");
    await waitFor(() => expect(onLocate).toHaveBeenCalledTimes(2));
    expect(searchLakes).toHaveBeenCalledWith("Lake Nowhere", "GA", null);
    search("30501"); // a ZIP is a place, never a lake
    await waitFor(() => expect(onLocate).toHaveBeenCalledTimes(3));
    expect(searchLakes).toHaveBeenCalledTimes(2);
  });

  it("offers the verified lake a bare name means, and the place a click away", async () => {
    const lanier = { ...match(5, "Lake Lanier", "GA", "Georgia"), data_tier: "verified" as const };
    const pond = match(6, "Lanier Pond", "GA", "Georgia");
    vi.mocked(searchLakes).mockResolvedValue([lanier, pond, match(7, "Laniers Millpond", "VA", "Virginia")]);
    vi.mocked(geocodePlace).mockResolvedValue({ query: "lanier", display_name: "Lanier County, GA", latitude: 31.0, longitude: -83.1 });
    const onLake = vi.fn();
    const onLocate = vi.fn();
    render(<LocationSearchBar onLocate={onLocate} onLake={onLake} stateCode="GA" />);
    search("lanier");
    fireEvent.click(await screen.findByRole("button", { name: "Lake Lanier Georgia" }));
    expect(onLake).toHaveBeenCalledWith(lanier);
    expect(onLocate).not.toHaveBeenCalled();
    // Only the lakes of that very name; the place is still there.
    search("lanier");
    expect(await screen.findByRole("button", { name: "Lanier Pond Georgia" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Laniers Millpond/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Search places instead" }));
    await waitFor(() => expect(onLocate).toHaveBeenCalled());
  });

  it("goes to the town when the verified lake of its name is right there", async () => {
    const waco = { ...match(9, "Lake Waco", "TX", "Texas"), data_tier: "verified" as const };
    vi.mocked(searchLakes).mockResolvedValue([waco]);
    vi.mocked(geocodePlace).mockResolvedValue({ query: "waco", display_name: "Waco, TX", latitude: 33.95, longitude: -84.15 });
    const onLocate = vi.fn();
    const onLake = vi.fn();
    render(<LocationSearchBar onLocate={onLocate} onLake={onLake} />);
    search("waco");
    await waitFor(() => expect(onLocate).toHaveBeenCalledWith({ latitude: 33.95, longitude: -84.15, label: "Waco, TX" }));
    expect(geocodePlace).toHaveBeenCalledTimes(1);
    expect(onLake).not.toHaveBeenCalled();
    expect(screen.queryByRole("list", { name: "Lakes with that name" })).not.toBeInTheDocument();
  });

  it("sends a bare name to the place search when no verified lake has it", async () => {
    vi.mocked(searchLakes).mockResolvedValue([match(8, "Lake Houston", "TX", "Texas")]);
    vi.mocked(geocodePlace).mockResolvedValue({ query: "houston", display_name: "Houston, TX", latitude: 29.8, longitude: -95.4 });
    const onLocate = vi.fn();
    render(<LocationSearchBar onLocate={onLocate} onLake={vi.fn()} />);
    search("houston");
    await waitFor(() => expect(onLocate).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("list", { name: "Lakes with that name" })).not.toBeInTheDocument();
  });

  it("says a bare name wasn't found from the one place search", async () => {
    vi.mocked(searchLakes).mockResolvedValue([]);
    vi.mocked(geocodePlace).mockRejectedValue(new ApiError("not found", 404));
    render(<LocationSearchBar onLocate={vi.fn()} onLake={vi.fn()} />);
    search("qwertyville");
    expect(await screen.findByText(/couldn't find "qwertyville"/i)).toBeInTheDocument();
    expect(geocodePlace).toHaveBeenCalledTimes(1);
  });
});
