import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CatchAnalysis } from "@/lib/api/types";
import { makeUser, renderApp, router } from "@/test-utils";

vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn(), getCatchAnalysis: vi.fn() };
});
const session = await import("@/lib/api/session");
const { CatchAnalysisView } = await import("./CatchAnalysisView");

const counts = (keys: string[], values: Record<string, number>) => keys.map((key) => ({ key, count: values[key] ?? 0 }));

function analysis(overrides: Partial<CatchAnalysis> = {}): CatchAnalysis {
  const fish = [
    { key: "largemouth-bass", slug: "largemouth-bass", label: "Largemouth Bass", count: 6 },
    { key: "bluegill", slug: "bluegill", label: "Bluegill", count: 3 },
    { key: "~sauger", slug: null, label: "Sauger", count: 1 },
  ];
  return {
    all_species: fish,
    species: null,
    total: 11,
    first_on: "2026-03-02",
    last_on: "2026-11-18",
    fish,
    waters: [{ kind: "lake", id: 4, name: "Lake Fork", count: 7 }],
    months: [0, 0, 2, 3, 0, 4, 0, 0, 0, 1, 1, 0],
    baits: [
      { key: "lure-soft-worm", count: 5, label: "Soft plastic worms" },
      { key: "bait-nightcrawler", count: 3, label: "Nightcrawlers and worms" },
    ],
    baits_logged: 8,
    times: counts(["dawn", "morning", "midday", "afternoon", "dusk", "night"], { dawn: 4, dusk: 2, midday: 1 }),
    times_logged: 7,
    skies: counts(["clear", "partly", "cloudy", "rain", "snow"], { cloudy: 3, clear: 1 }),
    trends: counts(["rising", "steady", "falling"], { falling: 2, steady: 1 }),
    temps: counts(["cold", "cool", "warm", "hot"], { warm: 3, hot: 1 }),
    winds: counts(["calm", "breeze", "windy"], { calm: 2, breeze: 2 }),
    weather_logged: 4,
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(session.getMe).mockResolvedValue(makeUser());
  vi.mocked(session.getCatchAnalysis).mockReset();
  router.replace.mockReset();
});

describe("CatchAnalysisView", () => {
  it("leads with the top fish, bait, time and weather, each out of the catches that record it", async () => {
    vi.mocked(session.getCatchAnalysis).mockResolvedValue(analysis());
    renderApp(<CatchAnalysisView />);
    expect(await screen.findByRole("heading", { name: "My catch analysis" })).toBeInTheDocument();
    expect(screen.getByText("Free in beta")).toBeInTheDocument();
    expect(screen.getByText("11 catches · 3 kinds of fish · since Mar 2, 2026")).toBeInTheDocument();
    const tiles = screen.getAllByText(/^Top /).map((label) => label.parentElement as HTMLElement);
    expect(tiles.map((t) => t.textContent)).toEqual([
      "Top fishLargemouth Bass6 of 10 catches",
      "Top baitSoft plastic worms5 of 8 catches",
      "Top time of dayDawn4 of 7 catches",
      "Top weatherCloudy3 of 4 catches",
    ]);
  });

  it("draws each count as a bar with its number beside it, and tells the share on focus", async () => {
    vi.mocked(session.getCatchAnalysis).mockResolvedValue(analysis());
    renderApp(<CatchAnalysisView />);
    const times = await screen.findByRole("list", { name: "Time of day" });
    const rows = within(times).getAllByRole("listitem");
    // In the day's order, not ranked; hours with nothing still show.
    expect(rows.map((r) => r.getAttribute("aria-label"))).toEqual([
      "Dawn: 4 of 7 · 57%",
      "Morning: 0 of 7 · 0%",
      "Midday: 1 of 7 · 14%",
      "Afternoon: 0 of 7 · 0%",
      "Dusk: 2 of 7 · 29%",
      "Night: 0 of 7 · 0%",
    ]);
    expect(screen.getByText("7 catches have a time")).toBeInTheDocument();
    const months = screen.getByRole("list", { name: "Catches by month" });
    expect(within(months).getAllByRole("listitem")[5]).toHaveAttribute("aria-label", "June: 4 of 11 · 36%");
    expect(within(screen.getByRole("list", { name: "Waters" })).getByText("Lake Fork")).toBeInTheDocument();
  });

  it("shows one fish at a time, holding the last answer while the next loads", async () => {
    vi.mocked(session.getCatchAnalysis).mockResolvedValueOnce(analysis());
    let answer: (a: CatchAnalysis) => void = () => undefined;
    vi.mocked(session.getCatchAnalysis).mockReturnValueOnce(new Promise((resolve) => (answer = resolve)));
    const { container } = renderApp(<CatchAnalysisView />);
    const select = await screen.findByRole("combobox", { name: "Which fish" });
    fireEvent.change(select, { target: { value: "largemouth-bass" } });
    expect(session.getCatchAnalysis).toHaveBeenLastCalledWith("largemouth-bass");
    await waitFor(() => expect(container.querySelector(".an-body")).toHaveClass("is-refreshing"));
    answer(analysis({ species: "largemouth-bass", total: 6, fish: [], baits_logged: 2, baits: [{ key: "lure-soft-worm", count: 2 }] }));
    expect(await screen.findByText("6 catches · since Mar 2, 2026")).toBeInTheDocument();
    expect(container.querySelector(".an-body")).not.toHaveClass("is-refreshing");
    // One fish has no "Top fish", and too few baits for a "Top bait".
    expect(screen.queryByText("Top fish")).not.toBeInTheDocument();
    expect(screen.queryByText("Top bait")).not.toBeInTheDocument();
  });

  it("says how to fill a chart that has nothing yet", async () => {
    vi.mocked(session.getCatchAnalysis).mockResolvedValue(
      analysis({ total: 2, times_logged: 0, weather_logged: 0, baits: [], baits_logged: 0, all_species: [], fish: [] }),
    );
    renderApp(<CatchAnalysisView />);
    expect(await screen.findByText("Add the time when you log a catch, and it shows up here.")).toBeInTheDocument();
    expect(screen.getByText("Pick the bait when you log a catch, and it shows up here.")).toBeInTheDocument();
    expect(screen.getByText("Catches logged within 7 days get their weather automatically.")).toBeInTheDocument();
    expect(screen.getByText("Log a few more catches and the patterns get clearer.")).toBeInTheDocument();
  });

  it("invites a first catch when there are none", async () => {
    vi.mocked(session.getCatchAnalysis).mockResolvedValue(analysis({ total: 0, all_species: [], fish: [], first_on: null }));
    renderApp(<CatchAnalysisView />);
    expect(await screen.findByText("No catches yet. Log one and it shows up here.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Share a catch" })).toHaveAttribute("href", "/map?addPin=1");
  });

  it("sends a signed-out visitor to sign in first", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    renderApp(<CatchAnalysisView />);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login?next=/account/analysis"));
    expect(session.getCatchAnalysis).not.toHaveBeenCalled();
  });
});
