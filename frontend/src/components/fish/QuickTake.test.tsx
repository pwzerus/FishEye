import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/baits", () => ({ useBaitCards: () => null, findBaits: () => [] }));

import { I18nProvider } from "@/i18n/client";
import { LOCALES } from "@/i18n/config";
import { MESSAGES } from "@/i18n/messages";
import { QUICK_DRAWINGS } from "./QuickDrawings";
import { MovingSteps, QuickTake } from "./QuickTake";
import { MOVING_STEPS } from "./quickTopics";

const moving = (root: Element) => root.getElementsByTagName("animate").length + root.getElementsByTagName("animateTransform").length;

const landing = {
  lead: "线一直绷紧，慢慢把鱼带近，再让鱼头朝前进网。",
  points: ["线一松，鱼就容易跑。", "搏鱼中途不要拧紧卸力。"],
  lang: "zh",
};

describe("QuickTake", () => {
  // A few words a picture: the owner wanted fewer words (2026-11-25).
  it.each(LOCALES)("gives every moving picture a few words in %s", (locale) => {
    for (const k of Object.values(MOVING_STEPS)) {
      const steps = MESSAGES[locale].quick.steps[k];
      expect(steps).toHaveLength(QUICK_DRAWINGS[k].length);
      // Spanish runs longest: "Sin red: agárralo del labio inferior (lobina, crappie)".
      const most = locale === "en" || locale === "es" ? 56 : 26;
      for (const step of steps) expect(step.length, step).toBeLessThanOrEqual(most);
    }
  });

  it("shows the line, then the picture, then the points, in the text's language", () => {
    const { container } = render(
      <I18nProvider locale="zh">
        <QuickTake topic="technique-landing" quick={landing}>
          <MovingSteps topic="technique-landing" />
        </QuickTake>
      </I18nProvider>,
    );
    const qt = container.querySelector(".qt") as HTMLElement;
    expect([...qt.children].map((c) => c.className)).toEqual(["qt-lead", "qt-steps", "qt-points"]);
    expect(qt.querySelector(".qt-lead")).toHaveTextContent(landing.lead);
    expect(qt.querySelector(".qt-lead")).toHaveAttribute("lang", "zh");
    const steps = container.querySelectorAll(".qt-steps li");
    expect(steps).toHaveLength(MESSAGES.zh.quick.steps.landing.length);
    steps.forEach((li, i) => {
      expect(li).toHaveTextContent(MESSAGES.zh.quick.steps.landing[i]);
      // Its words, then its picture (the owner, 2026-11-25).
      expect([...li.children].map((c) => c.tagName.toLowerCase())).toEqual(["p", "svg"]);
    });
    expect(moving(container)).toBeGreaterThan(0);
    expect(container.querySelectorAll(".qt-points li")).toHaveLength(landing.points.length);
  });

  it("marks text still in English as English", () => {
    const { container } = render(<QuickTake topic="bait-worms" quick={{ lead: "Hook it well.", points: ["Keep them cool."] }} />);
    expect(container.querySelector(".qt-lead")).toHaveAttribute("lang", "en");
    expect(container.querySelector(".qt-points li")).toHaveAttribute("lang", "en");
  });

  it("links a reference in its line, and underlines terms only in its points", () => {
    const quick = { lead: "Check the ice first (see Ice safety), then set the drag.", points: ["Set the drag before you cast."] };
    const { container } = render(<QuickTake topic="method-ice" quick={quick} refs={[{ id: "safe-ice", title: "Ice safety" }]} />);
    const lead = container.querySelector(".qt-lead") as HTMLElement;
    expect(lead.querySelector("a.hb-ref")).toHaveAttribute("href", "/handbook#safe-ice");
    expect(lead.querySelector(".term")).toBeNull();
    expect(container.querySelector(".qt-points .term")).toHaveTextContent("drag");
  });

  it("has moving steps only for a topic that has them", () => {
    const { container } = render(<MovingSteps topic="bait-worms" />);
    expect(container.innerHTML).toBe("");
  });

  it("stands still for a reader who asked for less motion", () => {
    const original = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: query.includes("reduce"),
      addEventListener: () => {},
      removeEventListener: () => {},
    })) as unknown as typeof window.matchMedia;
    try {
      const { container } = render(<MovingSteps topic="technique-landing" />);
      expect(container.querySelectorAll(".qt-steps svg")).toHaveLength(QUICK_DRAWINGS.landing.length);
      expect(moving(container)).toBe(0);
    } finally {
      window.matchMedia = original;
    }
  });
});
