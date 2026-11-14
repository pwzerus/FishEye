import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { COPYRIGHT } from "@/app/copyright/text";
import { PRIVACY } from "@/app/privacy/text";
import { TERMS } from "@/app/terms/text";
import { SECTION_IDS, sec } from "@/app/terms/text/shared";
import { LOCALES } from "@/i18n/config";
import type { LegalText } from "@/lib/legal";

vi.mock("next/navigation", () => ({ usePathname: () => "/terms" }));

/** What a page is made of: a translation has as many sections, headings,
 * paragraphs, list items, bold warnings and links as the English it
 * translates, so nothing was left out or run together. */
function shape(text: LegalText) {
  const { Body } = text;
  const { container, unmount } = render(<Body />);
  const count = (selector: string) => container.querySelectorAll(selector).length;
  const found = {
    sections: count("section"),
    headings: count("h2"),
    paragraphs: count("p"),
    items: count("li"),
    warnings: count(".legal-conspicuous"),
    links: count("a"),
    strong: count("strong"),
  };
  unmount();
  return found;
}

const OTHERS = LOCALES.filter((l) => l !== "en");

describe.each([
  ["terms", TERMS],
  ["privacy policy", PRIVACY],
  ["copyright page", COPYRIGHT],
])("the %s", (_, pages) => {
  it.each(OTHERS)("in %s has everything the English has", (lang) => {
    expect(shape(pages[lang])).toEqual(shape(pages.en));
    expect(pages[lang].title).not.toBe(pages.en.title);
  });
});

describe.each(OTHERS)("the terms in %s", (lang) => {
  it("keep the English sections, in order and numbered alike", () => {
    const { Body } = TERMS[lang];
    const { container } = render(<Body />);
    expect([...container.querySelectorAll("section[id]")].map((s) => s.id)).toEqual([...SECTION_IDS]);
    const headings = [...container.querySelectorAll("section[id] > h2")].map((h) => h.textContent ?? "");
    headings.forEach((h, i) => expect(h.startsWith(`${i + 1}. `)).toBe(true));
    expect(container.querySelectorAll(".legal-toc a")).toHaveLength(SECTION_IDS.length);
  });

  it("say an AI answer comes from an AI, name Anthropic, and point to the disputes section", () => {
    const { Body } = TERMS[lang];
    const { container } = render(<Body />);
    const ai = container.querySelector("#ai-answers")?.textContent ?? "";
    expect(ai).toMatch(/AI|IA/);
    expect(ai).toContain("Anthropic");
    expect(container.querySelector("#agreeing .legal-conspicuous")?.textContent).toContain(String(sec("disputes")));
  });
});
