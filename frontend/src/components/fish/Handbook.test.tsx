import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { HandbookTopic } from "@/lib/api/types";
import { Handbook } from "./Handbook";

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

  it("opens a collapsed category when an Ask citation links to a topic", () => {
    window.history.replaceState(null, "", "#bait-minnows");
    const scroll = vi.fn();
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scroll;
    try {
      const { container } = render(<Handbook topics={topics} />);
      expect(container.querySelector("#baits")).toHaveAttribute("open");
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
    expect(screen.getByRole("link", { name: "Live and natural bait" })).toHaveAttribute("href", "#baits");
    expect(container.querySelectorAll("#baits article")).toHaveLength(2);
  });

  it("names each topic's sources as links", () => {
    render(<Handbook topics={topics} />);
    expect(screen.getAllByRole("link", { name: "TPWD: catch and release tips" })[0]).toHaveAttribute(
      "href",
      "https://tpwd.texas.gov/cr",
    );
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

    it("is left out for someone in another state; every other topic stays", () => {
      window.localStorage.setItem("fisheye.state", "CO");
      const { container } = render(<Handbook topics={withRules} />);
      expect(container.querySelector("#rule-license")).toBeNull();
      expect(container.querySelector("#bait-worms")).not.toBeNull();
    });
  });
});
