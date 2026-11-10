import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, renderApp } from "@/test-utils";
import type { GearIdResult, GearItem } from "@/lib/api/types";

vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn(), identifyGear: vi.fn() };
});
const session = await import("@/lib/api/session");
const { ApiError } = await import("@/lib/api/client");
const { IdentifyGear } = await import("./IdentifyGear");

const item = (id: string, name: string, photo = true): GearItem => ({
  id, name, category: "rods-reels", what: "", tip: "", topic: null, fish: [], first_kit: false,
  photo: photo ? { url: `https://example.org/${id}.jpg`, width: 960, height: 640, author: "A", license: "CC0", license_url: null, file_page: "" } : null,
});
const ITEMS = [item("reel-spinning", "Spinning reel"), item("reel-baitcasting", "Baitcasting reel"), item("combo-spincast", "Spincast rod and reel (push-button)", false)];
const result = (over: Partial<GearIdResult>): GearIdResult => ({
  available: true, model: "PE-Core-L-14-336", gear_probability: 0.95, sure: true, not_gear: null, message: null,
  candidates: [
    { id: "reel-spinning", name: "Spinning reel", category: "rods-reels", probability: 0.82 },
    { id: "reel-baitcasting", name: "Baitcasting reel", category: "rods-reels", probability: 0.12 },
    { id: "combo-spincast", name: "Spincast rod and reel (push-button)", category: "rods-reels", probability: 0.06 },
  ],
  ...over,
});

function choose(container: HTMLElement) {
  const photo = new File(["x"], "reel.jpg", { type: "image/jpeg" });
  fireEvent.change(container.querySelector("input[type=file]") as HTMLInputElement, { target: { files: [photo] } });
}

beforeEach(() => {
  vi.mocked(session.getMe).mockResolvedValue(makeUser());
  vi.mocked(session.identifyGear).mockReset();
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});

describe("IdentifyGear", () => {
  it("names gear it is sure of and links down to its card", async () => {
    vi.mocked(session.identifyGear).mockResolvedValue(result({}));
    const { container } = renderApp(<IdentifyGear items={ITEMS} />);
    choose(container);
    expect(await screen.findByText(/This looks like:/)).toHaveTextContent("This looks like: Spinning reel");
    expect(screen.getByRole("link", { name: "What it's for ↓" })).toHaveAttribute("href", "#reel-spinning");
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("offers the likeliest few to compare when unsure", async () => {
    vi.mocked(session.identifyGear).mockResolvedValue(result({ sure: false }));
    const { container } = renderApp(<IdentifyGear items={ITEMS} />);
    choose(container);
    expect(await screen.findByText(/It could be one of these/)).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Baitcasting reel" })).toHaveAttribute("href", "#reel-baitcasting");
  });

  it("says when a photo shows a fish, not gear, and where to name the fish", async () => {
    vi.mocked(session.identifyGear).mockResolvedValue(result({ candidates: [], gear_probability: 0.1, not_gear: "fish" }));
    const { container } = renderApp(<IdentifyGear items={ITEMS} />);
    choose(container);
    expect(await screen.findByText("That looks like a fish, not gear.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Name a fish from a photo/ })).toHaveAttribute("href", "/identify");
  });

  it("asks a signed-out visitor to sign up once the day's photos are used", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    vi.mocked(session.identifyGear).mockRejectedValueOnce(new ApiError("You've used today's free gear photos.", 429));
    const { container } = renderApp(<IdentifyGear items={ITEMS} />);
    expect(await screen.findByText(/Signed out, you can check a few photos a day/)).toBeInTheDocument();
    choose(container);
    expect(await screen.findByRole("link", { name: "Create a free account" })).toHaveAttribute("href", "/login?mode=signup&next=/gear");
  });
});

describe("IdentifyGear, unclear photos", () => {
  it("asks for a closer photo when it can't tell which gear", async () => {
    vi.mocked(session.identifyGear).mockResolvedValue(result({ candidates: [], gear_probability: 0.7, sure: false }));
    const { container } = renderApp(<IdentifyGear items={ITEMS} />);
    choose(container);
    expect(await screen.findByText(/We couldn't tell what gear this is/)).toBeInTheDocument();
  });
});
