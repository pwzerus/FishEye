import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TimeWindow } from "@/lib/api/types";
import { BiteWindows, lakeClock, lakeDay } from "./WeatherRecommendations";

const morning: TimeWindow = {
  start_time: "2026-09-23T05:00:00-05:00",
  end_time: "2026-09-23T08:00:00-05:00",
  reason: "dawn low light; sunny, wind 8 mph, rain chance up to 10%",
  label: "morning",
  score: 1.05,
};
const evening: TimeWindow = {
  start_time: "2026-09-22T18:00:00-05:00",
  end_time: "2026-09-22T21:00:00-05:00",
  reason: "dusk low light; sunny, wind 8 mph, rain chance up to 10%",
  label: "evening",
  score: 0.9,
};

describe("lake time helpers", () => {
  it("reads the clock off the ISO string instead of converting to the viewer's zone", () => {
    expect(lakeClock("2026-09-23T05:00:00-05:00")).toBe("5 AM");
    expect(lakeClock("2026-09-22T18:30:00-05:00")).toBe("6:30 PM");
    expect(lakeClock("2026-09-22T00:00:00-05:00")).toBe("12 AM");
    expect(lakeClock("2026-09-22T12:00:00-05:00")).toBe("12 PM");
  });

  it("labels days in lake time", () => {
    // 04:30 UTC on the 23rd is still 23:30 on the 22nd in Texas.
    const now = new Date("2026-09-23T04:30:00Z");
    expect(lakeDay("2026-09-22T18:00:00-05:00", now)).toBe("Today");
    expect(lakeDay("2026-09-23T05:00:00-05:00", now)).toBe("Tomorrow");
  });
});

describe("BiteWindows", () => {
  it("shows both bites and marks the clearly better one", () => {
    render(<BiteWindows windows={[evening, morning]} fallbackWindow={null} />);
    expect(screen.getByText("Evening bite")).toBeInTheDocument();
    expect(screen.getByText("Morning bite")).toBeInTheDocument();
    expect(screen.getByText("6 PM – 9 PM")).toBeInTheDocument();
    expect(screen.getByText("5 AM – 8 AM")).toBeInTheDocument();
    const best = screen.getByText("Better bet").closest(".bite-card");
    expect(best).toHaveClass("bite-morning");
  });

  it("doesn't pick a winner when the two are about even", () => {
    render(<BiteWindows windows={[{ ...evening, score: 1.04 }, morning]} fallbackWindow={null} />);
    expect(screen.queryByText("Better bet")).not.toBeInTheDocument();
  });

  it("falls back to the single best window from an older backend", () => {
    render(<BiteWindows windows={[]} fallbackWindow={{ ...evening, label: null }} />);
    expect(screen.getByText(/Best window:/)).toBeInTheDocument();
  });

  it("renders nothing without a forecast", () => {
    const { container } = render(<BiteWindows windows={[]} fallbackWindow={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
