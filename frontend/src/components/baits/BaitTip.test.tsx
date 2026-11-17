import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BaitCard } from "@/lib/api/types";
import { findBaits } from "@/lib/baits";

const card = (id: string, topic: string, title: string, names: Record<string, string[]>, extra: Partial<BaitCard> = {}): BaitCard => ({
  id,
  topic,
  title,
  what: `${title}: what it is.`,
  why: "Fish eat them.",
  how: "Through the lips.",
  names,
  skip_on: [],
  fish: [],
  sources: [],
  lang: "en",
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

// The cards in Chinese, as /api/baits?lang=zh returns them.
const ZH_CARDS: BaitCard[] = CARDS.map((c) =>
  c.id === "worms"
    ? { ...c, what: "最好用的万能饵。", why: "便宜，容易找。", how: "钩穿过蚯蚓。", lang: "zh", fish: [{ slug: "bluegill", name: "Bluegill", why: "成鱼吃昆虫，一小段蚯蚓就够。" }] }
    : c,
);
const listBaits = vi.fn(async (locale?: string) => (locale === "zh" ? ZH_CARDS : CARDS));
vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listBaits: (locale?: string) => listBaits(locale) };
});
const { BaitText } = await import("./BaitTip");
const { I18nProvider } = await import("@/i18n/client");

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
    expect(tip).toHaveTextContent("Through the lips");
    expect(screen.getByRole("link", { name: "Channel Catfish" })).toHaveAttribute("href", "/fish/channel-catfish");
    expect(screen.getByRole("link", { name: "Ask about it →" }).getAttribute("href")).toContain("/ask?q=");
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(word).toHaveFocus();
  });

  it("shows the card in the reader's language", async () => {
    // 2026-11-16, the owner: a Chinese fish page opened an English card.
    render(
      <I18nProvider locale="zh">
        <BaitText text="用一小段蚯蚓" fish="bluegill" />
      </I18nProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "蚯蚓" }));
    const tip = screen.getByRole("dialog");
    expect(listBaits).toHaveBeenCalledWith("zh");
    expect(tip).toHaveTextContent("最好用的万能饵");
    expect(tip).toHaveTextContent("一小段蚯蚓就够");
    expect(tip).toHaveTextContent("钩穿过蚯蚓");
    expect(tip.textContent).not.toMatch(/[A-Za-z]{4,} [a-z]{3,}/);
    expect(tip.querySelector("[lang=en]")).toBeNull();
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
