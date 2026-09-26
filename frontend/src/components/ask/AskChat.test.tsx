import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AskResponse } from "@/lib/api/types";
import { AskChat } from "./AskChat";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, postAsk: vi.fn() };
});
const { postAsk } = await import("@/lib/api/client");
const mockedAsk = vi.mocked(postAsk);

function response(overrides: Partial<AskResponse> = {}): AskResponse {
  return {
    question: "what bait for crappie",
    answer: "Use small live minnows.",
    answer_source: "llm",
    citations: [
      {
        id: "white-crappie#live_baits",
        species_slug: "white-crappie",
        species_name: "White Crappie",
        section: "live_baits",
        title: "Live and natural bait",
        excerpt: "1½–2½ in minnows.",
        sources: [{ label: "TPWD: White Crappie", url: "https://tpwd.texas.gov/x", kind: "agency" }],
      },
      {
        id: "all-fish#bait_rules",
        species_slug: "all-fish",
        species_name: "",
        section: "bait_rules",
        title: "Texas bait rules",
        excerpt: "It is unlawful to use any game fish as bait.",
        sources: [],
      },
    ],
    trace: {
      trace_id: "abcdef12-0000",
      retriever: "bm25",
      routed_species: ["white-crappie", "black-crappie"],
      retrieved: [
        { id: "white-crappie#live_baits", score: 2.2 },
        { id: "black-crappie#live_baits", score: 1.9 },
        { id: "all-fish#bait_rules", score: 1.1 },
      ],
      provider: "anthropic",
      model: "claude-haiku-4-5",
      latency_ms: 812,
      prompt_tokens: 600,
      completion_tokens: 80,
      estimated_cost_usd: 0.001,
      validation_attempts: 1,
      outcome: "ok",
      cache_hit: false,
    },
    ...overrides,
  };
}

const SUGGESTIONS = ["What bait for crappie?", "When do white bass run?"];

async function askVia(text: string) {
  const box = screen.getByLabelText("Your question");
  fireEvent.change(box, { target: { value: text } });
  fireEvent.keyDown(box, { key: "Enter" });
}

describe("AskChat", () => {
  beforeEach(() => {
    mockedAsk.mockReset();
  });

  it("shows the question, then a checked answer with citations that link into the guide", async () => {
    mockedAsk.mockResolvedValue(response());
    render(<AskChat suggestions={SUGGESTIONS} />);

    await askVia("what bait for crappie");

    expect(screen.getByText("what bait for crappie")).toBeInTheDocument();
    expect(await screen.findByText("Use small live minnows.")).toBeInTheDocument();
    expect(screen.getByText("AI answer · checked")).toBeInTheDocument();
    expect(mockedAsk).toHaveBeenCalledWith({ question: "what bait for crappie", species_slug: null });

    const fishLink = screen.getByText(/White Crappie · Live and natural bait/).closest("a");
    expect(fishLink).toHaveAttribute("href", "/fish/white-crappie#live_baits");
    const rulesLink = screen.getByText("Texas bait rules").closest("a");
    expect(rulesLink).toHaveAttribute("href", "/fish#bait_rules");
  });

  it("opens a trace showing what was retrieved, what was cited and how it was checked", async () => {
    mockedAsk.mockResolvedValue(response());
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");
    await screen.findByText("Use small live minnows.");

    expect(screen.getByText("How this answer was checked")).toBeInTheDocument();
    expect(screen.getByText("black-crappie#live_baits")).toBeInTheDocument();
    expect(screen.getAllByText("cited")).toHaveLength(2);
    expect(screen.getByText("Passed every check")).toBeInTheDocument();
    expect(screen.getByText(/routed to white-crappie, black-crappie/)).toBeInTheDocument();
  });

  it.each([
    [{ answer_source: "fallback" as const }, "Straight from the guides"],
    [{ answer_source: "no_match" as const, citations: [] }, "Not in the guides"],
  ])("labels where the answer came from (%o)", async (overrides, label) => {
    mockedAsk.mockResolvedValue(response(overrides));
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("anything at all");
    expect(await screen.findByText(label)).toBeInTheDocument();
  });

  it("labels the no-key mock provider as a demo model, not as AI", async () => {
    const base = response();
    mockedAsk.mockResolvedValue({ ...base, trace: { ...base.trace, provider: "mock" } });
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("crappie bait");
    expect(await screen.findByText("Demo model")).toBeInTheDocument();
    expect(screen.queryByText("AI answer · checked")).not.toBeInTheDocument();
  });

  it("explains a rejected model answer in the trace", async () => {
    const base = response({ answer_source: "fallback" });
    mockedAsk.mockResolvedValue({ ...base, trace: { ...base.trace, outcome: "ungrounded_number", validation_attempts: 2 } });
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("hook size?");
    expect(await screen.findByText(/used a number the passages don't give/)).toBeInTheDocument();
    expect(screen.getByText("(2 attempts)")).toBeInTheDocument();
  });

  it("offers a retry when the backend can't be reached", async () => {
    mockedAsk.mockRejectedValueOnce(new Error("down")).mockResolvedValueOnce(response());
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");
    fireEvent.click(await screen.findByText("Try again"));
    expect(await screen.findByText("Use small live minnows.")).toBeInTheDocument();
    expect(mockedAsk).toHaveBeenCalledTimes(2);
  });

  it("asks a suggestion when it's clicked, and hides suggestions once a thread starts", async () => {
    mockedAsk.mockResolvedValue(response());
    render(<AskChat suggestions={SUGGESTIONS} />);
    fireEvent.click(screen.getByText("When do white bass run?"));
    await screen.findByText("Use small live minnows.");
    expect(mockedAsk).toHaveBeenCalledWith({ question: "When do white bass run?", species_slug: null });
    expect(screen.queryByText("What bait for crappie?")).not.toBeInTheDocument();
  });

  it("asks an initial question exactly once and sends the page's fish as context", async () => {
    mockedAsk.mockResolvedValue(response());
    render(<AskChat initialQuestion="what do they eat" speciesSlug="blue-catfish" suggestions={SUGGESTIONS} />);
    await screen.findByText("Use small live minnows.");
    expect(mockedAsk).toHaveBeenCalledTimes(1);
    expect(mockedAsk).toHaveBeenCalledWith({ question: "what do they eat", species_slug: "blue-catfish" });
  });

  it("ignores questions shorter than the API accepts", async () => {
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("hi");
    await waitFor(() => expect(mockedAsk).not.toHaveBeenCalled());
    expect(screen.getByLabelText("Send")).toBeDisabled();
  });
});
