import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { SpeciesGuide } from "@/lib/api/types";
import { SpeciesGuideBody } from "./SpeciesGuideBody";
import { SpeciesHowTo } from "./SpeciesHowTo";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, getSpeciesGuide: vi.fn() };
});
const { getSpeciesGuide, speciesSlug } = await import("@/lib/api/client");

const bass: SpeciesGuide = {
  slug: "largemouth-bass",
  common_name: "Largemouth Bass",
  scientific_name: "Micropterus salmoides",
  role: "sport",
  difficulty: "beginner",
  summary: "Texas's most sought-after freshwater fish.",
  diet: "Other fish and crayfish.",
  diet_type: "carnivore",
  where_and_when: ["Near cover."],
  live_baits: ["Large live shiners"],
  lures: ["Plastic worms"],
  setups: [
    {
      name: "Beginner spinning",
      use_when: "Your first bass setup.",
      method: "lure",
      rod: "Medium-action spinning rod",
      reel: "Spinning reel",
      line: "6–8 lb",
      terminal: "Plastic grub on a 1/8–1/4 oz jighead.",
      sources: [{ label: "MDC", url: "https://mdc.mo.gov/x", kind: "agency" }],
    },
    {
      name: "Live shad drift",
      use_when: "Drifting.",
      method: "bait",
      rod: "Medium rod",
      reel: "Spinning reel",
      line: "8–14 lb",
      terminal: "Circle hook.",
      sources: [{ label: "Some guide", url: "https://guide.example/x", kind: "guide" }],
    },
  ],
  tips: ["Retrieve slowly."],
  identification: [],
  how_to_get: [],
  bait_for: [],
  legal_notes: ["It is unlawful to use any game fish as bait."],
  limits_url: "https://tpwd.texas.gov/limits",
  sources: [{ label: "TPWD", url: "https://tpwd.texas.gov/x", kind: "agency" }],
};

const shad: SpeciesGuide = {
  ...bass,
  slug: "gizzard-shad",
  common_name: "Gizzard Shad",
  role: "forage",
  difficulty: null,
  diet_type: "filter_feeder",
  setups: [],
  live_baits: [],
  lures: [],
  identification: ["Usually 9–14 in long."],
  how_to_get: ["A cast net."],
  bait_for: ["Blue catfish, as cut bait"],
};

describe("speciesSlug", () => {
  it("matches the backend's slug rule", () => {
    expect(speciesSlug("Hybrid Striped Bass")).toBe("hybrid-striped-bass");
    expect(speciesSlug("  White Crappie ")).toBe("white-crappie");
  });
});

describe("SpeciesGuideBody", () => {
  it("shows every setup with its rod, line and hook", () => {
    render(<SpeciesGuideBody guide={bass} />);
    expect(screen.getByText("Beginner spinning")).toBeInTheDocument();
    expect(screen.getByText("Medium-action spinning rod")).toBeInTheDocument();
    expect(screen.getByText("Plastic grub on a 1/8–1/4 oz jighead.")).toBeInTheDocument();
  });

  it("labels a fishing-guide source so it isn't mistaken for an agency", () => {
    render(<SpeciesGuideBody guide={bass} />);
    expect(screen.getAllByText(/fishing guide site/)).toHaveLength(1);
  });

  it("always links to TPWD's limits instead of stating them", () => {
    render(<SpeciesGuideBody guide={bass} compact />);
    expect(screen.getByRole("link", { name: /check tpwd's current limits/i })).toHaveAttribute(
      "href",
      "https://tpwd.texas.gov/limits",
    );
  });

  it("shows a bait fish's cast-net and bait-for sections, and no rod setups", () => {
    render(<SpeciesGuideBody guide={shad} />);
    expect(screen.getByText("How to get it")).toBeInTheDocument();
    expect(screen.getByText("Blue catfish, as cut bait")).toBeInTheDocument();
    expect(screen.queryByText("Lure fishing")).not.toBeInTheDocument();
    expect(screen.queryByText("Bait fishing")).not.toBeInTheDocument();
  });

  it("groups setups into a lure-fishing and a bait-fishing section", () => {
    render(<SpeciesGuideBody guide={bass} />);
    const lureHeading = screen.getByText("Lure fishing");
    const baitHeading = screen.getByText("Bait fishing");
    expect(lureHeading.closest("section")).toHaveTextContent("Beginner spinning");
    expect(lureHeading.closest("section")).not.toHaveTextContent("Live shad drift");
    expect(baitHeading.closest("section")).toHaveTextContent("Live shad drift");
    expect(baitHeading.closest("section")).not.toHaveTextContent("Beginner spinning");
  });

  it("shows a carnivore/omnivore/filter-feeder tag next to what it eats", () => {
    render(<SpeciesGuideBody guide={bass} />);
    expect(screen.getByText("Carnivore")).toBeInTheDocument();
  });

  it("keeps the compact version short", () => {
    render(<SpeciesGuideBody guide={bass} compact />);
    expect(screen.queryByText("What it eats")).not.toBeInTheDocument();
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
    expect(screen.getByText("Lure fishing")).toBeInTheDocument();
    expect(screen.getByText("Bait fishing")).toBeInTheDocument();
  });
});

describe("SpeciesHowTo", () => {
  // Braces matter: a function returned from beforeEach is run by Vitest as
  // an after-test cleanup, and mockReset() returns the mock itself.
  beforeEach(() => {
    vi.mocked(getSpeciesGuide).mockReset();
  });

  it("loads nothing until opened, then fetches the guide once", async () => {
    vi.mocked(getSpeciesGuide).mockResolvedValue(bass);
    render(<SpeciesHowTo commonName="Largemouth Bass" />);
    expect(getSpeciesGuide).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "How to catch it" }));
    await waitFor(() => expect(screen.getByText("Beginner spinning")).toBeInTheDocument());
    expect(getSpeciesGuide).toHaveBeenCalledWith("largemouth-bass");
    expect(screen.getByRole("link", { name: /full largemouth bass guide/i })).toHaveAttribute(
      "href",
      "/fish/largemouth-bass",
    );

    fireEvent.click(screen.getByRole("button", { name: "Hide how to catch it" }));
    fireEvent.click(screen.getByRole("button", { name: "How to catch it" }));
    expect(getSpeciesGuide).toHaveBeenCalledTimes(1);
  });

  it("says so plainly when there's no guide", async () => {
    vi.mocked(getSpeciesGuide).mockRejectedValue(new ApiError("nope", 404));
    render(<SpeciesHowTo commonName="Peacock Bass" />);
    fireEvent.click(screen.getByRole("button", { name: "How to catch it" }));
    await waitFor(() => expect(screen.getByText("No guide for this species yet.")).toBeInTheDocument());
  });
});
