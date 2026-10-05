import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { FishingPlan } from "@/lib/api/types";
import { PlanCard, lakeClock, lakeDay, lakeRange } from "./WeatherRecommendations";

const plan: FishingPlan = {
  species: "Largemouth Bass",
  species_slug: "largemouth-bass",
  species_options: ["Largemouth Bass", "Bluegill"],
  species_on_record: true,
  where: { shore: "NW", text: "Try the NW bank. The SE wind is pushing baitfish toward it." },
  when: { start_time: "2026-09-22T18:00:00-05:00", end_time: "2026-09-22T21:00:00-05:00", label: "evening" },
  also: { start_time: "2026-09-23T05:00:00-05:00", end_time: "2026-09-23T08:00:00-05:00", label: "morning" },
  conditions: "78°F, partly sunny, SE wind 10 mph",
  lures: [
    { name: "Topwater lures", why: "Low light at dusk: bass come up and hit surface lures." },
    { name: "Spinnerbaits", why: "Wind chop and cloud cover hide your line." },
  ],
  baits: [{ name: "Large live shiners (8–9 in) under a bobber", why: "Fish it next to cover." }],
  lure_note: null,
  heads_up: [],
};

describe("lake time helpers", () => {
  it("reads the clock off the ISO string instead of converting to the viewer's zone", () => {
    expect(lakeClock("2026-09-23T05:00:00-05:00")).toBe("5 AM");
    expect(lakeClock("2026-09-22T18:30:00-05:00")).toBe("6:30 PM");
    expect(lakeClock("2026-09-22T00:00:00-05:00")).toBe("12 AM");
    expect(lakeClock("2026-09-22T12:00:00-05:00")).toBe("12 PM");
  });

  it("writes a window the way people say it", () => {
    expect(lakeRange("2026-09-22T18:00:00-05:00", "2026-09-22T21:00:00-05:00")).toBe("6–9 PM");
    expect(lakeRange("2026-09-22T11:00:00-05:00", "2026-09-22T14:00:00-05:00")).toBe("11 AM–2 PM");
  });

  it("labels days in lake time", () => {
    // 04:30 UTC on the 23rd is still 23:30 on the 22nd in Texas.
    const now = new Date("2026-09-23T04:30:00Z");
    expect(lakeDay("2026-09-22T18:00:00-05:00", now)).toBe("Today");
    expect(lakeDay("2026-09-23T05:00:00-05:00", now)).toBe("Tomorrow");
  });
});

describe("PlanCard", () => {
  it("says where, when, and what to use, each with its reason", () => {
    render(<PlanCard plan={plan} onSpeciesChange={() => {}} />);
    expect(screen.getByText(/Try the NW bank/)).toBeInTheDocument();
    expect(screen.getByText(/Evening bite, 6–9 PM/)).toBeInTheDocument();
    expect(screen.getByText(/or 5–8 AM/)).toBeInTheDocument();
    expect(screen.getByText("78°F, partly sunny, SE wind 10 mph")).toBeInTheDocument();
    expect(screen.getByText("Spinnerbaits")).toBeInTheDocument();
    expect(screen.getByText("Wind chop and cloud cover hide your line.")).toBeInTheDocument();
    expect(screen.getByText("Large live shiners (8–9 in) under a bobber")).toBeInTheDocument();
  });

  it("links to the chosen fish's guide", () => {
    render(<PlanCard plan={plan} onSpeciesChange={() => {}} />);
    expect(screen.getByRole("link", { name: /How to rig and fish for Largemouth Bass/ })).toHaveAttribute(
      "href",
      "/fish/largemouth-bass",
    );
  });

  it("puts nothing in a heads-up box on a normal day", () => {
    const { container } = render(<PlanCard plan={plan} onSpeciesChange={() => {}} />);
    expect(container.querySelector(".plan-heads-up")).toBeNull();
  });

  it("shows heads-up lines when something would change the trip", () => {
    render(<PlanCard plan={{ ...plan, heads_up: ["Wind up to 28 mph: hard to cast."] }} onSpeciesChange={() => {}} />);
    expect(screen.getByText("Wind up to 28 mph: hard to cast.")).toBeInTheDocument();
  });

  it("lets the angler switch fish", () => {
    const onSpeciesChange = vi.fn();
    render(<PlanCard plan={plan} onSpeciesChange={onSpeciesChange} />);
    fireEvent.change(screen.getByLabelText(/fishing for/i), { target: { value: "Bluegill" } });
    expect(onSpeciesChange).toHaveBeenCalledWith("Bluegill");
  });

  it("says when the fish isn't on record in this lake", () => {
    render(<PlanCard plan={{ ...plan, species_on_record: false }} onSpeciesChange={() => {}} />);
    expect(screen.getByText(/Not on record in this lake/)).toBeInTheDocument();
  });

  it("explains bait-only fish instead of leaving the lure row empty", () => {
    render(
      <PlanCard
        plan={{ ...plan, species: "Channel Catfish", lures: [], lure_note: "Catfish are caught on bait. No lure needed." }}
        onSpeciesChange={() => {}}
      />,
    );
    expect(screen.getByText("Catfish are caught on bait. No lure needed.")).toBeInTheDocument();
  });

  it("asks for a fish when none is picked yet", () => {
    render(<PlanCard plan={{ ...plan, species: null, lures: [], baits: [] }} onSpeciesChange={() => {}} />);
    expect(screen.getByText(/Pick a fish to see lures and bait/)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Pick a fish" })).toBeInTheDocument();
  });

  it("says so plainly when there's no live forecast", () => {
    render(<PlanCard plan={{ ...plan, where: null, when: null, also: null, conditions: null }} onSpeciesChange={() => {}} />);
    expect(screen.getByText(/No live forecast right now/)).toBeInTheDocument();
    expect(screen.getByText("Spinnerbaits")).toBeInTheDocument();
  });
});
