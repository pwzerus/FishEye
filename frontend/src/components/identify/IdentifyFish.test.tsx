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
  it("asks a signed-out visitor to sign in", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    renderApp(<IdentifyFish />);
    expect(await screen.findByRole("link", { name: "Create a free account" })).toHaveAttribute("href", "/login?mode=signup&next=/identify");
  });

  it("names a fish it is sure of, with its guide", async () => {
    vi.mocked(session.identifyFish).mockResolvedValue(result(0.97, [BASS, { ...BASS, slug: "spotted-bass", label: "Spotted Bass", probability: 0.06 }]));
    const { container } = renderApp(<IdentifyFish />);
    await screen.findByRole("button", { name: "Take or choose a photo" });
    choose(container);
    expect(await screen.findByText(/This looks like a/)).toHaveTextContent("This looks like a Largemouth Bass.");
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
    expect(await screen.findByText(/Not sure/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Spotted Bass" })).toHaveAttribute("href", "/fish/spotted-bass");

    vi.mocked(session.identifyFish).mockResolvedValueOnce(result(0.1, [BASS]));
    choose(container);
    expect(await screen.findByText(/doesn't look like a photo of a fish/)).toBeInTheDocument();
    await waitFor(() => expect(session.identifyFish).toHaveBeenCalledTimes(2));
  });
});
