import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InstallTip, offerInstallTip } from "./InstallTip";

describe("the home-screen tip after signing in", () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("isn't there for anyone who hasn't just signed in", () => {
    const { container } = render(<InstallTip />);
    expect(container).toBeEmptyDOMElement();
  });

  it("says how, the same way for Safari and for Chrome, and comes back at the next sign-in", () => {
    render(<InstallTip />);
    act(() => offerInstallTip());
    const tip = screen.getByRole("complementary", { name: "Put FishEye on your home screen" });
    expect(tip).toHaveTextContent("iPhone: open it in Safari, tap Share, then Add to Home Screen.");
    expect(tip).toHaveTextContent("Android: open it in Chrome, tap ⋮, then Add to Home screen or Install app.");

    fireEvent.click(screen.getByRole("button", { name: "Got it" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(window.localStorage.getItem("fisheye.installTip")).toBe("done");

    act(() => offerInstallTip());
    expect(screen.getByRole("complementary")).toBeInTheDocument();
  });

  // The product owner, 2026-11-13: a way to stop it for good.
  it("stays away once asked not to show again", () => {
    render(<InstallTip />);
    act(() => offerInstallTip());
    fireEvent.click(screen.getByRole("button", { name: "Don't show again" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(window.localStorage.getItem("fisheye.installTip")).toBe("never");

    act(() => offerInstallTip());
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("isn't shown on a computer", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({ matches: query === "(pointer: fine)" }));
    window.localStorage.setItem("fisheye.installTip", "show");
    const { container } = render(<InstallTip />);
    expect(container).toBeEmptyDOMElement();
  });

  it("isn't shown in FishEye opened from the home screen", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({ matches: query === "(display-mode: standalone)" }));
    window.localStorage.setItem("fisheye.installTip", "show");
    const { container } = render(<InstallTip />);
    expect(container).toBeEmptyDOMElement();
  });
});
