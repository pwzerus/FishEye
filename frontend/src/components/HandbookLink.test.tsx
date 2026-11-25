import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const at = vi.hoisted(() => ({ path: "/zh/handbook" }));
vi.mock("next/navigation", () => ({ usePathname: () => at.path }));

import { HandbookLink } from "./HandbookLink";

describe("HandbookLink", () => {
  // 2026-11-25: a term card's "see the drawing" did nothing on the handbook,
  // which hears a new hash only through hashchange.
  it("on the handbook, changes only the hash, so the handbook opens the topic's chapter", () => {
    at.path = "/zh/handbook";
    render(<HandbookLink topic="tackle-hooks">Hooks</HandbookLink>);
    expect(screen.getByRole("link", { name: "Hooks" })).toHaveAttribute("href", "#tackle-hooks");
  });

  it("elsewhere, opens the handbook at the topic", () => {
    at.path = "/gear";
    render(<HandbookLink topic="tackle-hooks">Hooks</HandbookLink>);
    expect(screen.getByRole("link", { name: "Hooks" })).toHaveAttribute("href", "/handbook#tackle-hooks");
  });
});
