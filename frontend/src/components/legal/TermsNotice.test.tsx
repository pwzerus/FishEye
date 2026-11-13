import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

let path = "/fish";
let user: { created_at: string } | null = null;

vi.mock("next/navigation", () => ({ usePathname: () => path }));
vi.mock("@/components/auth/AuthProvider", () => ({ useAuth: () => ({ user }) }));

const { TermsNotice } = await import("./TermsNotice");

describe("TermsNotice", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-20T12:00:00Z"));
    window.localStorage.clear();
    path = "/fish";
    user = { created_at: "2026-10-01T00:00:00Z" };
  });
  afterEach(() => vi.useRealTimers());

  it("tells an account from before the change when the new terms apply to it", () => {
    render(<TermsNotice />);
    expect(screen.getByText("Our terms of use changed. The new ones apply to you from November 27, 2026.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Read them" })).toHaveAttribute("href", "/terms");
  });

  it("goes away for good once dismissed", () => {
    const { unmount } = render(<TermsNotice />);
    fireEvent.click(screen.getByRole("button", { name: "Got it" }));
    expect(screen.queryByText(/terms of use changed/)).not.toBeInTheDocument();
    unmount();
    render(<TermsNotice />);
    expect(screen.queryByText(/terms of use changed/)).not.toBeInTheDocument();
  });

  it.each([
    ["an account made after the change, which agreed to the new terms", () => (user = { created_at: "2026-11-14T09:00:00Z" })],
    ["a visitor who isn't signed in", () => (user = null)],
    ["the terms page itself", () => (path = "/terms")],
    ["a month after the change applies", () => vi.setSystemTime(new Date("2026-12-28T12:00:00Z"))],
  ])("shows nothing to %s", (_case, set) => {
    set();
    render(<TermsNotice />);
    expect(screen.queryByText(/terms of use changed/)).not.toBeInTheDocument();
  });
});
