import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/baits", () => ({ useBaitCards: () => null, findBaits: () => [] }));

import { I18nProvider } from "@/i18n/client";
import { LOCALES } from "@/i18n/config";
import { MESSAGES } from "@/i18n/messages";
import { QUICK_DRAWINGS } from "./QuickDrawings";
import { QuickTake } from "./QuickTake";
import { QUICK_TAKES } from "./quickTopics";

const moving = (root: Element) => root.getElementsByTagName("animate").length + root.getElementsByTagName("animateTransform").length;

describe("QuickTake", () => {
  // A few words a picture: the owner wanted fewer words (2026-11-25).
  it.each(LOCALES)("gives every picture a few words, and a line and points to remember, in %s", (locale) => {
    for (const k of Object.values(QUICK_TAKES)) {
      const words = MESSAGES[locale].quick.takes[k];
      expect(words.steps).toHaveLength(QUICK_DRAWINGS[k].length);
      expect(words.lead.trim()).not.toBe("");
      expect(words.points.length).toBeGreaterThan(0);
      // Spanish runs longest: "Sin red: agárralo del labio inferior (lobina, crappie)".
      const most = locale === "en" || locale === "es" ? 56 : 26;
      for (const step of words.steps) expect(step.length, step).toBeLessThanOrEqual(most);
    }
  });

  it("shows the line, the steps as moving pictures, and the points", () => {
    const words = MESSAGES.zh.quick.takes.landing;
    const { container } = render(
      <I18nProvider locale="zh">
        <QuickTake k="landing" topic="technique-landing" />
      </I18nProvider>,
    );
    expect(container.querySelector(".qt-lead")).toHaveTextContent(words.lead);
    const steps = container.querySelectorAll(".qt-steps li");
    expect(steps).toHaveLength(words.steps.length);
    steps.forEach((li, i) => {
      expect(li).toHaveTextContent(words.steps[i]);
      // Its words, then its picture (the owner, 2026-11-25).
      expect([...li.children].map((c) => c.tagName.toLowerCase())).toEqual(["p", "svg"]);
    });
    expect(moving(container)).toBeGreaterThan(0);
    expect(container.querySelectorAll(".qt-points li")).toHaveLength(words.points.length);
  });

  it("stands still for a reader who asked for less motion", () => {
    const original = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: query.includes("reduce"),
      addEventListener: () => {},
      removeEventListener: () => {},
    })) as unknown as typeof window.matchMedia;
    try {
      const { container } = render(<QuickTake k="landing" topic="technique-landing" />);
      expect(container.querySelectorAll(".qt-steps svg")).toHaveLength(QUICK_DRAWINGS.landing.length);
      expect(moving(container)).toBe(0);
    } finally {
      window.matchMedia = original;
    }
  });
});
