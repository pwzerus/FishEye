import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, renderApp } from "@/test-utils";
import type { FishIdResult } from "@/lib/api/types";

vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn(), identifyFish: vi.fn() };
});
vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listJurisdictions: vi.fn().mockResolvedValue([]) };
});
const session = await import("@/lib/api/session");
const { ApiError } = await import("@/lib/api/client");
const { IdentifyFish } = await import("./IdentifyFish");

const result = (fish: number, candidates: FishIdResult["candidates"]): FishIdResult => ({
  available: true, model: "bioclip-2", fish_probability: fish, candidates, verdict: null,
});
const BASS = { slug: "largemouth-bass", label: "Largemouth Bass", probability: 0.91, in_guides: true };

function choose(container: HTMLElement) {
  const photo = new File(["x"], "fish.jpg", { type: "image/jpeg" });
  fireEvent.change(container.querySelector("input[type=file]") as HTMLInputElement, { target: { files: [photo] } });
}

beforeEach(() => {
  vi.mocked(session.getMe).mockResolvedValue(makeUser());
  vi.mocked(session.identifyFish).mockReset();
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});

describe("IdentifyFish", () => {
  it("lets a signed-out visitor try it, then asks them to sign up once the day's checks are used", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    vi.mocked(session.identifyFish).mockResolvedValueOnce(result(0.97, [BASS]));
    const { container } = renderApp(<IdentifyFish />);
    await screen.findByRole("button", { name: "Take or choose a photo" });
    expect(screen.getByText(/Signed out, you can check a few photos a day/)).toBeInTheDocument();
    choose(container);
    expect(await screen.findByText(/This looks like/)).toHaveTextContent("This looks like: Largemouth Bass.");

    vi.mocked(session.identifyFish).mockRejectedValueOnce(new ApiError("You've used today's free photo checks.", 429));
    choose(container);
    expect(await screen.findByRole("link", { name: "Create a free account" })).toHaveAttribute("href", "/login?mode=signup&next=/identify");
    expect(screen.getByText(/used today's free photo checks/)).toBeInTheDocument();
  });

  it("names a fish it is sure of, with its guide", async () => {
    vi.mocked(session.identifyFish).mockResolvedValue(result(0.97, [BASS, { ...BASS, slug: "spotted-bass", label: "Spotted Bass", probability: 0.06 }]));
    const { container } = renderApp(<IdentifyFish />);
    await screen.findByRole("button", { name: "Take or choose a photo" });
    choose(container);
    expect(await screen.findByText(/This looks like/)).toHaveTextContent("This looks like: Largemouth Bass.");
    expect(screen.getByRole("link", { name: /How to catch, handle and cook a largemouth bass/ })).toHaveAttribute("href", "/fish/largemouth-bass");
    expect(screen.getByText("91%")).toBeInTheDocument();
  });

  it("says when it isn't sure, and when the photo isn't of a fish", async () => {
    vi.mocked(session.identifyFish).mockResolvedValueOnce(
      result(0.9, [{ ...BASS, probability: 0.55 }, { slug: "spotted-bass", label: "Spotted Bass", probability: 0.4, in_guides: true }]),
    );
    const { container } = renderApp(<IdentifyFish />);
    await screen.findByRole("button", { name: "Take or choose a photo" });
    choose(container);
    // Over half: named as the best guess, the look-alike under it.
    expect(await screen.findByText(/Best guess/)).toHaveTextContent("Best guess: Largemouth Bass, but the photo doesn't settle it.");
    expect(screen.getByText("It could also be:")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Spotted Bass" })).toHaveAttribute("href", "/fish/spotted-bass");

    // Under half: no best guess, just the possibilities.
    vi.mocked(session.identifyFish).mockResolvedValueOnce(
      result(0.9, [{ ...BASS, probability: 0.45 }, { slug: "spotted-bass", label: "Spotted Bass", probability: 0.4, in_guides: true }]),
    );
    choose(container);
    expect(await screen.findByText(/Not sure/)).toBeInTheDocument();

    vi.mocked(session.identifyFish).mockResolvedValueOnce(result(0.1, [BASS]));
    choose(container);
    expect(await screen.findByText(/doesn't look like a photo of a fish/)).toBeInTheDocument();

    // A fish, but no species stands out: no "most likely" 6% guess.
    vi.mocked(session.identifyFish).mockResolvedValueOnce(
      result(0.7, [{ ...BASS, probability: 0.06 }, { slug: "spotted-bass", label: "Spotted Bass", probability: 0.05, in_guides: true }]),
    );
    choose(container);
    expect(await screen.findByText(/can't tell which fish this is/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Largemouth Bass" })).not.toBeInTheDocument();
    await waitFor(() => expect(session.identifyFish).toHaveBeenCalledTimes(4));
  });

  it("names the kind when the photo is sure of it but not of which one", async () => {
    const RAINBOW = { slug: "rainbow-trout", label: "Rainbow Trout", probability: 0.39, in_guides: true, guide_slug: "rainbow-trout" };
    const BROOK = { slug: "brook-trout", label: "Brook Trout", probability: 0.17, in_guides: true, guide_slug: "brook-trout" };
    vi.mocked(session.identifyFish).mockResolvedValue({ ...result(0.98, [RAINBOW, BROOK]), group: "trout", group_probability: 0.86 });
    const { container } = renderApp(<IdentifyFish />);
    await screen.findByRole("button", { name: "Take or choose a photo" });
    choose(container);
    expect(await screen.findByText(/This is a trout/)).toHaveTextContent("This is a trout. Which kind, the photo doesn't settle; most likely: Rainbow Trout.");
    expect(screen.queryByText(/Not sure/)).not.toBeInTheDocument();
  });

  it("names a steelhead as such, says it is a rainbow trout, and links that guide", async () => {
    const STEELHEAD = { slug: "steelhead", label: "Steelhead", probability: 0.5, in_guides: false, guide_slug: "rainbow-trout" };
    const RAINBOW = { slug: "rainbow-trout", label: "Rainbow Trout", probability: 0.35, in_guides: true, guide_slug: "rainbow-trout" };
    vi.mocked(session.identifyFish).mockResolvedValue(result(0.95, [STEELHEAD, RAINBOW]));
    const { container } = renderApp(<IdentifyFish />);
    await screen.findByRole("button", { name: "Take or choose a photo" });
    choose(container);
    // Together the two names of one fish are sure enough to say so.
    expect(await screen.findByText(/This looks like/)).toHaveTextContent("This looks like: Steelhead.");
    expect(screen.getByText(/A steelhead is a rainbow trout/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Steelhead" })).toHaveAttribute("href", "/fish/rainbow-trout");
    expect(screen.getByRole("link", { name: /How to catch, handle and cook a steelhead/ })).toHaveAttribute("href", "/fish/rainbow-trout");
  });
});
