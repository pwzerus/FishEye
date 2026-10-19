import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { HandbookTopic } from "@/lib/api/types";
import { Handbook } from "./Handbook";

const source = { label: "TPWD: catch and release tips", url: "https://tpwd.texas.gov/cr", kind: "agency" as const };

function topic(id: string, category: string, label: string, title: string): HandbookTopic {
  return { id, category, category_label: label, title, body: [`${title} body.`], sources: [source] };
}

describe("Handbook", () => {
  const topics = [
    topic("bait-worms", "baits", "Live and natural bait", "Worms and nightcrawlers"),
    topic("bait-minnows", "baits", "Live and natural bait", "Minnows and shiners"),
    topic("care-release", "care", "Releasing, keeping and cleaning fish", "Catch and release"),
  ];

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
});
