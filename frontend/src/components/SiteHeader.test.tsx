import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { nav, renderApp } from "@/test-utils";

// vi.mock is hoisted above imports, so the factory imports what it needs itself.
vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn().mockResolvedValue(null) };
});

const { SiteHeader } = await import("./SiteHeader");

describe("SiteHeader", () => {
  it.each([
    ["/", "Home"],
    ["/map", "Map"],
    ["/fish", "Fish guide"],
    ["/fish/bluegill", "Fish guide"],
    ["/community", "Community"],
    ["/community/12", "Community"],
    ["/ask", "Ask"],
  ])("on %s marks %s as the current page", async (path, label) => {
    nav.pathname = path;
    renderApp(<SiteHeader />);
    await screen.findByText("Sign in");
    const current = screen.getAllByRole("link").filter((a) => a.getAttribute("aria-current") === "page");
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent(label);
  });
});
