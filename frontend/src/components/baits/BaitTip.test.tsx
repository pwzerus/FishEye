import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BaitCard } from "@/lib/api/types";
import { findBaits } from "@/lib/baits";

const card = (id: string, topic: string, title: string, names: Record<string, string[]>, extra: Partial<BaitCard> = {}): BaitCard => ({
  id,
  topic,
  title,
  what: `${title}: what it is.`,
  why: "Why use them: fish eat them.",
  how: "How to hook: through the lips.",
  names,
  skip_on: [],
  fish: [],
  sources: [],
  ...extra,
});

const CARDS: BaitCard[] = [
  card("soft-plastics", "lure-soft-plastics", "Soft plastics and jigs", { en: ["plastic worm", "plastic worms"] }),
  card("worms", "bait-worms", "Worms and nightcrawlers", { en: ["worm", "worms", "nightcrawler", "nightcrawlers"], zh: ["蚯蚓"] }, {
    fish: [
      { slug: "bluegill", name: "Bluegill", why: "Adults eat insects, so a piece of worm wins." },
      { slug: "channel-catfish", name: "Channel Catfish", why: null },
    ],
  }),
  card("cut-bait", "bait-shad-cut", "Shad and cut bait", { en: ["cut bait", "shad"] }, { skip_on: ["gizzard-shad"] }),
];

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listBaits: vi.fn(async () => CARDS) };
});
const { BaitText } = await import("./BaitTip");

describe("findBaits", () => {
  it("finds each bait once, the longer name first", () => {
    const found = findBaits("Plastic worms work; so do nightcrawlers and a worm.", CARDS, "en");
    expect(found.map((m) => m.card.id)).toEqual(["soft-plastics", "worms"]);
    expect(found[1].start).toBe("Plastic worms work; so do ".length);
  });

  it("matches whole words only, and in the reader's language", () => {
    expect(findBaits("Shadow and wormwood", CARDS, "en")).toEqual([]);
    expect(findBaits("用蚯蚓钓", CARDS, "zh").map((m) => m.card.id)).toEqual(["worms"]);
    expect(findBaits("用蚯蚓钓", CARDS, "en")).toEqual([]);
  });

  it("leaves a fish's own page alone", () => {
    expect(findBaits("Shad school in open water", CARDS, "en", { fish: "gizzard-shad" })).toEqual([]);
    expect(findBaits("Shad school in open water", CARDS, "en", { fish: "blue-catfish" })).toHaveLength(1);
  });
});

describe("BaitText", () => {
  it("opens a card that says why this fish takes the bait", async () => {
    render(<BaitText text="A small piece of worm on a tiny hook" fish="bluegill" />);
    const word = await screen.findByRole("button", { name: "worm" });
    fireEvent.click(word);
    const tip = screen.getByRole("dialog", { name: "Worms and nightcrawlers" });
    expect(tip).toHaveTextContent("Why Bluegill takes it");
    expect(tip).toHaveTextContent("a piece of worm wins");
    expect(tip).toHaveTextContent("through the lips");
    expect(screen.getByRole("link", { name: "Channel Catfish" })).toHaveAttribute("href", "/fish/channel-catfish");
    expect(screen.getByRole("link", { name: "Ask about it →" }).getAttribute("href")).toContain("/ask?q=");
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(word).toHaveFocus();
  });

  it("keeps one card open at a time", async () => {
    render(
      <p>
        <BaitText text="worm" />
        <BaitText text="cut bait" />
      </p>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "worm" }));
    fireEvent.click(screen.getByRole("button", { name: "cut bait" }));
    await waitFor(() => expect(screen.getAllByRole("dialog")).toHaveLength(1));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Shad and cut bait");
  });
});
