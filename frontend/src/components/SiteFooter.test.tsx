import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

let path = "/";
vi.mock("next/navigation", () => ({ usePathname: () => path }));

const { SiteFooter } = await import("./SiteFooter");

describe("SiteFooter", () => {
  it.each(["/fish", "/fish/bluegill", "/handbook", "/gear", "/community", "/rules/TX", "/account"])(
    "puts the terms at the bottom of %s",
    (p) => {
      path = p;
      render(<SiteFooter />);
      expect(screen.getByRole("link", { name: "Terms" })).toHaveAttribute("href", "/terms");
      expect(screen.getByRole("link", { name: "Privacy" })).toHaveAttribute("href", "/privacy");
    },
  );

  // Home has its own footer, the map fills the screen, Ask has a line under
  // its question box, the legal pages list the links already, and sign-in
  // has the agreement next to its buttons.
  it.each(["/", "/map", "/ask", "/terms", "/privacy", "/copyright", "/login", "/admin"])("leaves %s alone", (p) => {
    path = p;
    const { container } = render(<SiteFooter />);
    expect(container).toBeEmptyDOMElement();
  });
});
