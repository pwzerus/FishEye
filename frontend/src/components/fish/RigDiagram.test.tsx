import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/i18n/client";
import { LOCALES } from "@/i18n/config";
import { MESSAGES } from "@/i18n/messages";
import { HANDBOOK_TITLES } from "@/i18n/names";
import { RELATED, RigDiagram } from "./RigDiagram";
import { RIG_DIAGRAMS, rigKeys } from "./rigTopics";
import { STEP_DRAWINGS } from "./StepDrawings";

describe("RigDiagram", () => {
  it("draws only for handbook topics that exist", () => {
    for (const topic of Object.keys(RIG_DIAGRAMS)) expect(HANDBOOK_TITLES.zh[topic], topic).toBeTruthy();
    const { container } = render(<RigDiagram topic="bait-stink" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("links the sliding sinker rig to the swivel, the knot, hook sizes and circle hooks", () => {
    for (const ids of Object.values(RELATED)) for (const id of ids ?? []) expect(RIG_DIAGRAMS[id], id).toBeTruthy();
    const { container } = render(
      <I18nProvider locale="zh">
        <RigDiagram topic="rig-bottom" />
      </I18nProvider>,
    );
    const links = [...container.querySelectorAll(".rig-related a")].map((a) => [a.getAttribute("href"), a.textContent]);
    expect(links).toEqual([
      ["#tackle-leaders", MESSAGES.zh.rigs.swivel.title],
      ["#knot-improved-clinch", MESSAGES.zh.rigs.clinch.title],
      ["#tackle-hooks", MESSAGES.zh.rigs.sizes.title],
      ["#tackle-circle-hooks", MESSAGES.zh.rigs.circle.title],
    ]);
  });

  // A number in the drawing is only as good as the line under it that says
  // what it points at: the two have to agree in every language.
  it.each(LOCALES)("numbers each drawing's parts 1 to n and names every one in %s", (locale) => {
    for (const [topic, key] of Object.entries(RIG_DIAGRAMS)) {
      if (typeof key !== "string" || key in STEP_DRAWINGS) continue;
      const words = MESSAGES[locale].rigs[key];
      expect(words.parts.length, `${locale} ${key}`).toBe(MESSAGES.en.rigs[key].parts.length);
      const { container, unmount } = render(
        <I18nProvider locale={locale}>
          <RigDiagram topic={topic} />
        </I18nProvider>,
      );
      const marks = [...container.querySelectorAll("svg .rig-mark text")].map((m) => m.textContent);
      const listed = [...container.querySelectorAll("ol > li")].map((li) => li.textContent);
      expect(marks, `${locale} ${key}`).toEqual(words.parts.map((_, i) => String(i + 1)));
      expect(listed).toEqual(words.parts.map((part, i) => `${i + 1}${part}`));
      expect(container.querySelector("svg title")?.textContent).toBe(words.title);
      expect(container.querySelector("svg")?.getAttribute("role")).toBe("img");
      unmount();
    }
  });

  // A step drawing: a picture per step, and under each its own words.
  it.each(LOCALES)("gives every step of a step drawing a picture and its words in %s", (locale) => {
    for (const topic of Object.keys(RIG_DIAGRAMS)) {
      const keys = rigKeys(topic).filter((k) => k in STEP_DRAWINGS) as (keyof typeof STEP_DRAWINGS)[];
      if (keys.length === 0) continue;
      const { container, unmount } = render(
        <I18nProvider locale={locale}>
          <RigDiagram topic={topic} />
        </I18nProvider>,
      );
      const figures = [...container.querySelectorAll("figure.rig-steps")];
      expect(figures.length, topic).toBe(keys.length);
      keys.forEach((k, n) => {
        const words = MESSAGES[locale].rigs[k];
        expect(words.parts.length, `${locale} ${k}`).toBe(STEP_DRAWINGS[k].length);
        const steps = [...figures[n].querySelectorAll("ol > li")];
        expect(steps.map((li) => li.querySelector("svg") !== null)).toEqual(words.parts.map(() => true));
        // Every picture draws something.
        for (const li of steps) expect(li.querySelector("svg")!.querySelectorAll("path, circle, rect, ellipse, line").length, k).toBeGreaterThan(0);
        expect(steps.map((li) => li.querySelector("p")?.textContent)).toEqual(words.parts.map((part, i) => `${i + 1}${part}`));
        expect(figures[n].querySelector(".rig-steps-title")?.textContent).toBe(words.title);
      });
      unmount();
    }
  });
});
