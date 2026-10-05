import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { AdvisorResponse } from "@/lib/api/types";
import { AdvisorPanel } from "./AdvisorPanel";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, postAdvisorExplain: vi.fn() };
});

// Imported after the mock so we get the mocked reference.
const { postAdvisorExplain } = await import("@/lib/api/client");

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

// The panel is not mounted on the lake page right now (it explains a spot
// ranking the page no longer shows), but its behaviour is kept under test so
// it can be brought back, reworded, without being rediscovered.
describe("AdvisorPanel", () => {
  beforeEach(() => {
    vi.mocked(postAdvisorExplain).mockReset();
    vi.mocked(postAdvisorExplain).mockResolvedValue(mockAdvisor);
  });

  it("does not call the advisor until the user asks for an explanation", () => {
    render(<AdvisorPanel waterbodyId={1} />);
    // The written explanation costs tokens, so it waits to be asked for.
    expect(postAdvisorExplain).not.toHaveBeenCalled();
  });

  it("requests and renders an explanation when asked", async () => {
    render(<AdvisorPanel waterbodyId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /explain these picks/i }));

    await waitFor(() =>
      expect(screen.getByText(/Lake Fork Dam Bank Access is the strongest option/)).toBeInTheDocument(),
    );
    expect(postAdvisorExplain).toHaveBeenCalledWith({ waterbody_id: 1, target_species: undefined });
    expect(screen.getByText(/Work the NW shore/)).toBeInTheDocument();
  });

  it("passes the target species through", async () => {
    render(<AdvisorPanel waterbodyId={1} targetSpecies="Largemouth Bass" />);
    fireEvent.click(screen.getByRole("button", { name: /explain these picks/i }));

    await waitFor(() =>
      expect(postAdvisorExplain).toHaveBeenCalledWith({
        waterbody_id: 1,
        target_species: "Largemouth Bass",
      }),
    );
  });

  it("labels a mock-model answer as such", async () => {
    render(<AdvisorPanel waterbodyId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /explain these picks/i }));

    // Mock output must never be presented as a real model's, the same way
    // fallback weather is never presented as a real reading.
    await waitFor(() => expect(screen.getByText("mock model")).toBeInTheDocument());
  });

  it("says plainly when the answer is the fixed template, and why", async () => {
    vi.mocked(postAdvisorExplain).mockResolvedValue({
      ...mockAdvisor,
      answer_source: "fallback",
      trace: { ...mockAdvisor.trace, outcome: "ungrounded_source" },
    });
    render(<AdvisorPanel waterbodyId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /explain these picks/i }));

    await waitFor(() => expect(screen.getByText("plain summary")).toBeInTheDocument());
    // The reason is shown, not swallowed: a discarded answer is a fact
    // about this response the reader is entitled to.
    expect(screen.getByText(/cited a source the backend never supplied/i)).toBeInTheDocument();
  });

  it("exposes the request trace on demand", async () => {
    render(<AdvisorPanel waterbodyId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /explain these picks/i }));

    fireEvent.click(await screen.findByRole("button", { name: /show request trace/i }));

    expect(screen.getByText("trace-abc-123")).toBeInTheDocument();
    expect(screen.getByText("mock / mock-advisor-v1")).toBeInTheDocument();
    expect(screen.getByText("1014 / 227")).toBeInTheDocument();
  });

  it("surfaces an advisor error", async () => {
    vi.mocked(postAdvisorExplain).mockRejectedValue(new ApiError("advisor exploded", 500));
    render(<AdvisorPanel waterbodyId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /explain these picks/i }));

    await waitFor(() => expect(screen.getByText("advisor exploded")).toBeInTheDocument());
  });
});
