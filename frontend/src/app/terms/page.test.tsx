import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/i18n/client";
import type { Locale } from "@/i18n/config";

vi.mock("next/navigation", () => ({ usePathname: () => "/terms" }));
let locale: Locale = "en";
vi.mock("@/i18n/server", () => ({ getLocale: async () => locale }));

const { default: TermsPage } = await import("./page");

/** The page as the server renders it for a reader of `lang`. */
async function page(lang: Locale = "en") {
  locale = lang;
  return render(<I18nProvider locale={lang}>{await TermsPage()}</I18nProvider>);
}

describe("Terms of use", () => {
  it("numbers its sections and lists them all in the contents", async () => {
    await page();
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent ?? "");
    const numbered = headings.filter((h) => /^\d+\. /.test(h));
    expect(numbered[0]).toBe("1. Agreeing to these terms");
    numbered.forEach((h, i) => expect(h.startsWith(`${i + 1}. `)).toBe(true));
    const contents = screen.getByRole("navigation", { name: "Contents" });
    expect(contents.querySelectorAll("a")).toHaveLength(numbered.length);
  });

  // Ask's AI answers link here (components/ask/AskChat.tsx).
  it("has the AI answers section that Ask links to, saying it is an AI", async () => {
    const { container } = await page();
    const ai = container.querySelector("#ai-answers");
    expect(ai?.textContent).toMatch(/It is an AI, not a person/);
    expect(ai?.textContent).toMatch(/Anthropic/);
  });

  it("points its cross-references at the right sections", async () => {
    const { container } = await page();
    const text = container.textContent ?? "";
    const number = (title: string) =>
      screen.getAllByRole("heading", { level: 2 }).find((h) => h.textContent?.endsWith(title))?.textContent?.split(".")[0];
    expect(text).toContain(`Please read Section ${number("Disputes and arbitration")}.`);
    expect(text).toContain(`Section ${number("FishEye Plus")} says what you get back`);
    expect(text).toContain(`Apple (Section ${number("Apps from the App Store or Google Play")})`);
  });

  // The product owner, 2026-11-13: the terms in every language, not only English.
  it("comes in the reader's language, saying the English version is the one that applies", async () => {
    await page("zh");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("使用条款");
    expect(screen.getByText("最后更新：2026年11月13日")).toBeInTheDocument();
    expect(screen.getByText(/如与英文版本不一致，以英文版本为准/)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "目录" })).toBeInTheDocument();
  });

  it("says nothing about translations in English", async () => {
    await page("en");
    expect(screen.getByText("Last updated November 13, 2026")).toBeInTheDocument();
    expect(screen.queryByText(/translation/i, { selector: ".hint" })).toBeNull();
  });
});
