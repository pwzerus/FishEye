import { act, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MESSAGES } from "@/i18n/messages";
import type { HandbookTopic, Jurisdiction, SpeciesGuide } from "@/lib/api/types";

import SourcesPage from "./page";

vi.mock("@/i18n/server", () => ({
  getT: async () => MESSAGES.en,
  getLocale: async () => "en",
}));

const agency = { label: "MDC: Walleye", url: "https://mdc.mo.gov/walleye", kind: "agency" as const };
const guideSite = { label: "Some guide", url: "https://guide.example/x", kind: "guide" as const };
const walleye = {
  slug: "walleye",
  common_name: "Walleye",
  sources: [agency, guideSite],
  setups: [{ name: "Jig and minnow", sources: [guideSite] }],
} as unknown as SpeciesGuide;
const topic = (id: string, region: string) =>
  ({ id, category: "baits", category_label: "Live and natural bait", title: id, body: [], region, sources: [agency] }) as HandbookTopic;
const alabama = { code: "AL", name: "Alabama", bait_rules_sources: [agency] } as unknown as Jurisdiction;
const montana = { code: "MT", name: "Montana", bait_rules_sources: [] } as unknown as Jurisdiction;

vi.mock("@/lib/api/client", () => ({
  listSpeciesGuides: async () => [walleye],
  listHandbook: async () => [topic("bait-worms", "all"), topic("rule-license-al", "AL")],
  listJurisdictions: async () => [alabama, montana],
  listSpeciesPhotos: async () => ({
    walleye: { url: "x", width: 1, height: 1, author: "USFWS", license: "Public domain", license_url: null, file_page: "https://commons.example/w", source: "wikimedia" },
  }),
}));

afterEach(() => {
  window.location.hash = "";
});

describe("/sources", () => {
  it("says what each source was used for", async () => {
    const { container } = render(await SourcesPage());
    const fish = within(container.querySelector<HTMLElement>("#fish-walleye")!);
    expect(fish.getByRole("link", { name: "Walleye" })).toHaveAttribute("href", "/fish/walleye");
    expect(fish.getByText("The guide")).toBeInTheDocument();
    expect(fish.getByText("Jig and minnow")).toBeInTheDocument();
    expect(fish.getByRole("link", { name: "MDC: Walleye" })).toHaveAttribute("href", "https://mdc.mo.gov/walleye");
    expect(fish.getAllByText(/fishing guide site/)).toHaveLength(2);
  });

  it("puts a state's rules under the state, and leaves out a state with none", async () => {
    const { container } = render(await SourcesPage());
    expect(container.querySelector("#topic-bait-worms")).not.toBeNull();
    expect(container.querySelector("#topic-rule-license-al")).toBeNull();
    const al = within(container.querySelector<HTMLElement>("#rules-al")!);
    expect(al.getByText("Bait rules")).toBeInTheDocument();
    expect(al.getByRole("link", { name: "rule-license-al" })).toHaveAttribute("href", "/fish#rule-license-al");
    expect(container.querySelector("#rules-mt")).toBeNull();
  });

  it("lists the datasets and the photo credits", async () => {
    const { container } = render(await SourcesPage());
    expect(screen.getByRole("link", { name: /OpenStreetMap contributors/ })).toHaveAttribute(
      "href",
      "https://www.openstreetmap.org/copyright",
    );
    expect(within(container.querySelector<HTMLElement>("#photos")!).getByText(/USFWS/)).toBeInTheDocument();
  });

  it("starts closed, and opens the part a link points at", async () => {
    const scrolled = vi.fn();
    Element.prototype.scrollIntoView = scrolled;
    const { container, unmount } = render(await SourcesPage());
    expect(container.querySelector<HTMLDetailsElement>("#fish")!.open).toBe(false);
    unmount();

    window.location.hash = "#fish-walleye";
    let opened: ReturnType<typeof render>;
    const page = await SourcesPage();
    await act(async () => {
      opened = render(page);
    });
    expect(opened!.container.querySelector<HTMLDetailsElement>("#fish")!.open).toBe(true);
    expect(opened!.container.querySelector<HTMLDetailsElement>("#handbook")!.open).toBe(false);
    expect(scrolled).toHaveBeenCalled();
  });
});
