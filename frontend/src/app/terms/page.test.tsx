import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/terms" }));

const { default: TermsPage } = await import("./page");

describe("Terms of use", () => {
  it("numbers its sections and lists them all in the contents", () => {
    render(<TermsPage />);
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent ?? "");
    const numbered = headings.filter((h) => /^\d+\. /.test(h));
    expect(numbered[0]).toBe("1. Agreeing to these terms");
    numbered.forEach((h, i) => expect(h.startsWith(`${i + 1}. `)).toBe(true));
    const contents = screen.getByRole("navigation", { name: "Contents" });
    expect(contents.querySelectorAll("a")).toHaveLength(numbered.length);
  });

  // Ask's AI answers link here (components/ask/AskChat.tsx).
  it("has the AI answers section that Ask links to, saying it is an AI", () => {
    const { container } = render(<TermsPage />);
    const ai = container.querySelector("#ai-answers");
    expect(ai?.textContent).toMatch(/It is an AI, not a person/);
    expect(ai?.textContent).toMatch(/Anthropic/);
  });

  it("points its cross-references at the right sections", () => {
    const { container } = render(<TermsPage />);
    const text = container.textContent ?? "";
    const number = (title: string) =>
      screen.getAllByRole("heading", { level: 2 }).find((h) => h.textContent?.endsWith(title))?.textContent?.split(".")[0];
    expect(text).toContain(`Please read Section ${number("Disputes and arbitration")}.`);
    expect(text).toContain(`Section ${number("FishEye Plus")} says what you get back`);
    expect(text).toContain(`Apple (Section ${number("Apps from the App Store or Google Play")})`);
  });
});
