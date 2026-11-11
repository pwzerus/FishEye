import { act, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { HandbookTopic, Jurisdiction } from "@/lib/api/types";
import { rememberState } from "@/lib/jurisdiction";
import { Handbook, cardKind } from "./Handbook";

function state(code: string, name: string): Jurisdiction {
  return {
    code, name, covered: code !== "MI", agency: null, agency_short: null, limits_url: null, license_url: null,
    bait_rules: [], bait_rules_sources: [], bait_rules_on_every_bait_question: false,
  };
}
const STATES = [state("TX", "Texas"), state("GA", "Georgia"), state("MI", "Michigan")];

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listJurisdictions: vi.fn(async () => STATES) };
});

const source = { label: "TPWD: catch and release tips", url: "https://tpwd.texas.gov/cr", kind: "agency" as const };

function topic(id: string, category: string, label: string, title: string, region = "all"): HandbookTopic {
  return { id, category, category_label: label, title, body: [`${title} body.`], region, sources: [source] };
}

describe("Handbook", () => {
  const topics = [
    topic("bait-worms", "baits", "Live and natural bait", "Worms and nightcrawlers"),
    topic("bait-minnows", "baits", "Live and natural bait", "Minnows and shiners"),
    topic("care-release", "care", "Releasing, keeping and cleaning fish", "Catch and release"),
  ];

  it("opens the chapter when an Ask citation links to a topic", () => {
    window.history.replaceState(null, "", "#bait-minnows");
    const scroll = vi.fn();
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scroll;
    try {
      const { container } = render(<Handbook topics={topics} />);
      expect(container.querySelector("#baits")).not.toHaveAttribute("hidden");
      expect(container.querySelector("#care")).toHaveAttribute("hidden");
      expect(scroll).toHaveBeenCalled();
    } finally {
      Element.prototype.scrollIntoView = original;
      window.history.replaceState(null, "", "/");
    }
  });

  it("puts every topic under its own anchor, where Ask citations link", () => {
    const { container } = render(<Handbook topics={topics} />);
    for (const t of topics) {
      expect(container.querySelector(`#${t.id}`)).not.toBeNull();
    }
  });

  it("groups topics by category, each with an anchor and a nav link", () => {
    const { container } = render(<Handbook topics={topics} />);
    expect(container.querySelector("#baits")).not.toBeNull();
    expect(container.querySelector("#care")).not.toBeNull();
    expect(screen.getByRole("link", { name: /Live and natural bait/ })).toHaveAttribute("href", "#baits");
    expect(container.querySelectorAll("#baits article")).toHaveLength(2);
  });

  it("has one link to the sources page instead of a list under each topic", () => {
    render(<Handbook topics={topics} />);
    expect(screen.queryByRole("link", { name: "TPWD: catch and release tips" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sources" })).toHaveAttribute("href", "/sources#handbook");
  });

  it("renders nothing without topics", () => {
    const { container } = render(<Handbook topics={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  describe("a topic that states one state's rules", () => {
    const withRules = [
      ...topics,
      topic("rule-license", "rules", "Licence, and rules that follow you home", "Do I need a fishing licence?", "TX"),
    ];
    afterEach(() => window.localStorage.clear());

    it("shows to someone who hasn't said where they are, and to someone in that state", () => {
      const first = render(<Handbook topics={withRules} />);
      expect(first.container.querySelector("#rule-license")).not.toBeNull();
      first.unmount();
      window.localStorage.setItem("fisheye.state", "TX");
      expect(render(<Handbook topics={withRules} />).container.querySelector("#rule-license")).not.toBeNull();
    });

    it("counts only what the chosen state will see", () => {
      window.localStorage.setItem("fisheye.state", "CO");
      const { container } = render(<Handbook topics={[...withRules, topic("rule-a", "rules", "Rules", "All", "all")]} />);
      expect(container.querySelector('a[href="#rules"]')).toHaveTextContent("1 topic");
    });

    it("is left out for someone in another state; every other topic stays", () => {
      window.localStorage.setItem("fisheye.state", "CO");
      const { container } = render(<Handbook topics={withRules} />);
      expect(container.querySelector("#rule-license")).toBeNull();
      expect(container.querySelector("#bait-worms")).not.toBeNull();
    });
  });

  describe("a link to one state's card, read with another state picked", () => {
    const trips = [
      ...topics,
      topic("start-first-trip", "technique", "Technique", "Your first trip in Texas", "TX"),
      topic("start-first-trip-ga", "technique", "Technique", "Your first trip in Georgia", "GA"),
    ];
    afterEach(() => {
      window.localStorage.clear();
      window.history.replaceState(null, "", "/");
    });

    it("opens the picked state's card of the same kind", async () => {
      window.localStorage.setItem("fisheye.state", "GA");
      window.history.replaceState(null, "", "#start-first-trip");
      const { container } = render(<Handbook topics={trips} />);
      await waitFor(() => expect(window.location.hash).toBe("#start-first-trip-ga"));
      expect(container.querySelector("#start-first-trip-ga")).not.toBeNull();
      expect(container.querySelector("#technique")).not.toHaveAttribute("hidden");
    });

    it("says so where the card was when that state has none, with its rules a tap away", async () => {
      window.localStorage.setItem("fisheye.state", "MI");
      window.history.replaceState(null, "", "#start-first-trip");
      render(<Handbook topics={trips} />);
      const note = await screen.findByRole("note");
      // The note takes the card's place and its anchor, so the link lands on it.
      expect(note).toHaveAttribute("id", "start-first-trip");
      expect(note).toHaveTextContent("This card is for Texas. Michigan's isn't written yet.");
      expect(within(note).getByRole("link", { name: "All of Michigan's fishing rules →" })).toHaveAttribute("href", "/rules/michigan");
      expect(within(note).getByRole("link", { name: "How to get ready for a first trip" })).toHaveAttribute("href", "/start");
    });

    it("follows the picker both ways without a reload", async () => {
      window.localStorage.setItem("fisheye.state", "TX");
      window.history.replaceState(null, "", "#start-first-trip");
      const { container } = render(<Handbook topics={trips} />);
      expect(container.querySelector("article#start-first-trip")).not.toBeNull();

      act(() => rememberState("MI"));
      expect(await screen.findByRole("note")).toHaveTextContent("Michigan's isn't written yet.");
      expect(container.querySelector("article#start-first-trip")).toBeNull();

      act(() => rememberState("TX"));
      await waitFor(() => expect(container.querySelector("article#start-first-trip")).not.toBeNull());
      expect(screen.queryByRole("note")).not.toBeInTheDocument();
    });
  });

  it("knows one state's card from another's of the same kind", () => {
    expect(cardKind({ id: "start-first-trip", region: "TX" })).toBe("start-first-trip");
    expect(cardKind({ id: "start-first-trip-ga", region: "GA" })).toBe("start-first-trip");
    expect(cardKind({ id: "safe-lifejacket-tx", region: "TX" })).toBe("safe-lifejacket");
    expect(cardKind({ id: "rule-license-mi", region: "MI" })).toBe("rule-license");
    expect(cardKind({ id: "bait-worms", region: "all" })).toBe("bait-worms");
  });
});
