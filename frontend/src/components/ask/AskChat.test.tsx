import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AskResponse } from "@/lib/api/types";
import { AskChat } from "./AskChat";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, postAsk: vi.fn() };
});
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, postAskSummary: vi.fn() };
});
vi.mock("next/navigation", () => ({ usePathname: () => "/ask" }));
const { ApiError, postAsk } = await import("@/lib/api/client");
const { postAskSummary } = await import("@/lib/api/session");
const mockedAsk = vi.mocked(postAsk);
const mockedSummary = vi.mocked(postAskSummary);

const SIGNED_OUT = { signed_in: false, limit: null, remaining: null };

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
        region: "all",
        sources: [{ label: "TPWD: White Crappie", url: "https://tpwd.texas.gov/x", kind: "agency" }],
      },
      {
        id: "all-fish#bait_rules",
        species_slug: "all-fish",
        species_name: "",
        section: "bait_rules",
        title: "Texas bait rules",
        excerpt: "It is unlawful to use any game fish as bait.",
        region: "TX",
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
    ai: SIGNED_OUT,
    ...overrides,
  };
}

/** What POST /api/ask returns now: the guide passages, no model. */
function searchResult(overrides: Partial<AskResponse> = {}): AskResponse {
  const base = response();
  return {
    ...base,
    answer: "Here's what the FishEye guides say:",
    answer_source: "passages",
    trace: { ...base.trace, provider: "none", model: "none", prompt_tokens: 0, completion_tokens: 0, estimated_cost_usd: 0 },
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
    mockedSummary.mockReset();
  });

  it("does not submit Enter while a Chinese input method is composing", () => {
    render(<AskChat suggestions={SUGGESTIONS} />);
    const box = screen.getByRole("textbox", { name: "Your question" });
    fireEvent.change(box, { target: { value: "鲈鱼怎么钓" } });
    fireEvent.keyDown(box, { key: "Enter", isComposing: true });
    expect(mockedAsk).not.toHaveBeenCalled();
  });

  it("shows the guide's passages first, saying no model was involved", async () => {
    mockedAsk.mockResolvedValue(searchResult());
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");

    expect(await screen.findByText("From the guides")).toBeInTheDocument();
    expect(screen.getByText(/White Crappie · Live and natural bait/)).toBeInTheDocument();
    expect(mockedSummary).not.toHaveBeenCalled();
  });

  it("tells a signed-out visitor how to get an AI summary", async () => {
    mockedAsk.mockResolvedValue(searchResult());
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");

    const signIn = await screen.findByRole("link", { name: "Sign in" });
    expect(signIn).toHaveAttribute("href", "/login?next=%2Fask");
    expect(screen.queryByRole("button", { name: /Summarize with AI/ })).not.toBeInTheDocument();
  });

  it("writes an AI summary on request for a signed-in person and updates what's left", async () => {
    mockedAsk.mockResolvedValue(searchResult({ ai: { signed_in: true, limit: 3, remaining: 3 } }));
    mockedSummary.mockResolvedValue(response({ ai: { signed_in: true, limit: 3, remaining: 2 } }));
    render(<AskChat suggestions={SUGGESTIONS} speciesSlug="white-crappie" />);
    await askVia("what bait for crappie");
    await screen.findByRole("button", { name: "Summarize with AI (3 left today)" });
    await askVia("what bait for crappie");
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Summarize with AI (3 left today)" })).toHaveLength(2));

    fireEvent.click(screen.getAllByRole("button", { name: /Summarize with AI/ })[1]);
    expect(await screen.findByText("Use small live minnows.")).toBeInTheDocument();
    expect(screen.getByText("AI answer · checked")).toBeInTheDocument();
    expect(mockedSummary).toHaveBeenCalledWith({
      question: "what bait for crappie",
      species_slug: "white-crappie",
      state: null,
    });

    // The earlier answer's button now shows what the server says is left.
    expect(screen.getByRole("button", { name: "Summarize with AI (2 left today)" })).toBeInTheDocument();
  });

  it("says when today's summaries are used up instead of offering the button", async () => {
    mockedAsk.mockResolvedValue(searchResult({ ai: { signed_in: true, limit: 3, remaining: 0 } }));
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");
    expect(await screen.findByText(/used today's AI summaries/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Summarize with AI/ })).not.toBeInTheDocument();
  });

  it("shows the server's reason when a summary is refused", async () => {
    mockedAsk.mockResolvedValue(searchResult({ ai: { signed_in: true, limit: 3, remaining: 1 } }));
    mockedSummary.mockRejectedValue(new ApiError("You've used today's 3 AI summaries.", 429));
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");
    fireEvent.click(await screen.findByRole("button", { name: /Summarize with AI/ }));
    expect(await screen.findByText("You've used today's 3 AI summaries.")).toBeInTheDocument();
    expect(screen.getByText(/Searching the guides stays free/)).toBeInTheDocument();
  });

  it("offers no AI summary for a question the guides don't cover", async () => {
    mockedAsk.mockResolvedValue(
      searchResult({ answer_source: "no_match", citations: [], ai: { signed_in: true, limit: 3, remaining: 3 } }),
    );
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("how to tie a tie");
    expect(await screen.findByText("Not in the guides")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Summarize with AI/ })).not.toBeInTheDocument();
  });

  it("shows unlimited summaries without a count (admins)", async () => {
    mockedAsk.mockResolvedValue(searchResult({ ai: { signed_in: true, limit: null, remaining: null } }));
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");
    expect(await screen.findByRole("button", { name: "Summarize with AI" })).toBeInTheDocument();
  });

  it("shows the question, then a checked answer with citations that link into the guide", async () => {
    mockedAsk.mockResolvedValue(response());
    render(<AskChat suggestions={SUGGESTIONS} />);

    await askVia("what bait for crappie");

    expect(screen.getByText("what bait for crappie")).toBeInTheDocument();
    expect(await screen.findByText("Use small live minnows.")).toBeInTheDocument();
    expect(screen.getByText("AI answer · checked")).toBeInTheDocument();
    expect(mockedAsk).toHaveBeenCalledWith({ question: "what bait for crappie", species_slug: null, state: null });

    const fishLink = screen.getByText(/White Crappie · Live and natural bait/).closest("a");
    expect(fishLink).toHaveAttribute("href", "/fish/white-crappie#live_baits");
    const rulesLink = screen.getByText("Texas bait rules").closest("a");
    expect(rulesLink).toHaveAttribute("href", "/fish#bait_rules");
  });

  it("keeps how the answer was found to developers: no scores, model usage or trace id", async () => {
    mockedAsk.mockResolvedValue(response());
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");
    await screen.findByText("Use small live minnows.");

    expect(screen.queryByText("Sources & answer details")).not.toBeInTheDocument();
    expect(screen.queryByText("black-crappie#live_baits")).not.toBeInTheDocument();
    expect(screen.queryByText(/BM25|claude-haiku|tokens|abcdef12/)).not.toBeInTheDocument();
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

  it.each([
    ["off_topic", "Not a fishing question"],
    ["unguided_fish", "No guide for that fish"],
    ["no_match", "Not in the guides"],
  ])("says which kind of empty answer it is (%s)", async (outcome, label) => {
    // Three different admissions, from the trace's outcome (backend ADR 0026).
    const base = response({ answer_source: "no_match", citations: [] });
    mockedAsk.mockResolvedValue({ ...base, trace: { ...base.trace, outcome } });
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

  it("explains a rejected model answer in plain words, without the check's code name", async () => {
    const base = response({ answer_source: "fallback" });
    mockedAsk.mockResolvedValue({ ...base, trace: { ...base.trace, outcome: "ungrounded_number", validation_attempts: 2 } });
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("hook size?");
    const badge = await screen.findByText("Straight from the guides");
    expect(badge).toHaveAttribute("title", "The AI summary couldn't be used, so this is the guide's own text");
    expect(screen.queryByText(/ungrounded|attempts/)).not.toBeInTheDocument();
  });

  it("offers a retry when the backend can't be reached", async () => {
    mockedAsk.mockRejectedValueOnce(new Error("down")).mockResolvedValueOnce(response());
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");
    fireEvent.click(await screen.findByText("Try again"));
    expect(await screen.findByText("Use small live minnows.")).toBeInTheDocument();
    expect(mockedAsk).toHaveBeenCalledTimes(2);
  });

  it("shows the server's message when a request limit is hit, not 'can't reach'", async () => {
    mockedAsk.mockRejectedValueOnce(new ApiError("Please wait a moment and try again.", 429, "rate_limited"));
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("what bait for crappie");
    expect(await screen.findByText("Please wait a moment and try again.")).toBeInTheDocument();
    expect(screen.queryByText(/Couldn't reach/)).not.toBeInTheDocument();
  });

  it("asks a suggestion when it's clicked, and hides suggestions once a thread starts", async () => {
    mockedAsk.mockResolvedValue(response());
    render(<AskChat suggestions={SUGGESTIONS} />);
    fireEvent.click(screen.getByText("When do white bass run?"));
    await screen.findByText("Use small live minnows.");
    expect(mockedAsk).toHaveBeenCalledWith({ question: "When do white bass run?", species_slug: null, state: null });
    expect(screen.queryByText("What bait for crappie?")).not.toBeInTheDocument();
  });

  it("asks an initial question exactly once and sends the page's fish as context", async () => {
    mockedAsk.mockResolvedValue(response());
    render(<AskChat initialQuestion="what do they eat" speciesSlug="blue-catfish" suggestions={SUGGESTIONS} />);
    await screen.findByText("Use small live minnows.");
    expect(mockedAsk).toHaveBeenCalledTimes(1);
    expect(mockedAsk).toHaveBeenCalledWith({ question: "what do they eat", species_slug: "blue-catfish", state: null });
  });

  it("ignores questions shorter than the API accepts", async () => {
    render(<AskChat suggestions={SUGGESTIONS} />);
    await askVia("hi");
    await waitFor(() => expect(mockedAsk).not.toHaveBeenCalled());
    expect(screen.getByLabelText("Send")).toBeDisabled();
  });
  describe("states (backend ADR 0027)", () => {
    beforeEach(() => window.localStorage.clear());

    it("sends the remembered state with the question", async () => {
      window.localStorage.setItem("fisheye.state", "CO");
      mockedAsk.mockResolvedValue(searchResult());
      render(<AskChat suggestions={SUGGESTIONS} />);
      await askVia("what bait for crappie");
      await screen.findByText("From the guides");
      expect(mockedAsk).toHaveBeenCalledWith({ question: "what bait for crappie", species_slug: null, state: "CO" });
    });

    it("marks a passage that states one state's rules", async () => {
      mockedAsk.mockResolvedValue(searchResult());
      render(<AskChat suggestions={SUGGESTIONS} />);
      await askVia("can I use live bait");
      expect(await screen.findByText("TX rules")).toBeInTheDocument();
      // ... and only that one: the crappie passage is for every state.
      expect(document.querySelectorAll(".citation-region")).toHaveLength(1);
    });

    it("says the rules aren't written for the person's state, not that the question is bad", async () => {
      mockedAsk.mockResolvedValue(
        searchResult({
          answer: "That's a question about Colorado's fishing rules, and FishEye hasn't written those yet.",
          answer_source: "no_match",
          citations: [],
          trace: { ...searchResult().trace, outcome: "other_state" },
        }),
      );
      render(<AskChat suggestions={SUGGESTIONS} />);
      await askVia("do I need a licence");
      expect(await screen.findByText("Rules not written for your state")).toBeInTheDocument();
      expect(screen.getByText(/Colorado's fishing rules/)).toBeInTheDocument();
    });
  });
});
