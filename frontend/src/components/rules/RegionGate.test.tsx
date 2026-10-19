import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Jurisdiction } from "@/lib/api/types";
import { StatePicker } from "@/components/ui/StatePicker";
import { LimitsNote, OtherStateRules, RegionGate } from "./RegionGate";

const STATES: Jurisdiction[] = [
  {
    code: "TX",
    name: "Texas",
    covered: true,
    agency: "Texas Parks and Wildlife Department",
    agency_short: "TPWD",
    limits_url: "https://tpwd.texas.gov/limits",
    license_url: "https://tpwd.texas.gov/license",
  },
  { code: "CO", name: "Colorado", covered: false, agency: null, agency_short: null, limits_url: null, license_url: null },
];

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listJurisdictions: vi.fn(async () => STATES) };
});

function setState(code: string | null) {
  if (code) window.localStorage.setItem("fisheye.state", code);
  else window.localStorage.clear();
}

describe("state-aware rules (backend ADR 0027)", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => window.localStorage.clear());

  describe("RegionGate", () => {
    const gate = (
      <RegionGate region="TX" fallback={<p>elsewhere</p>}>
        <p>Texas rules</p>
      </RegionGate>
    );

    it("shows the rules to someone who hasn't said where they are", () => {
      render(gate);
      expect(screen.getByText("Texas rules")).toBeInTheDocument();
    });

    it("shows them in that state", () => {
      setState("TX");
      render(gate);
      expect(screen.getByText("Texas rules")).toBeInTheDocument();
    });

    it("shows the fallback, never Texas's rules, in another state", () => {
      setState("CO");
      render(gate);
      expect(screen.queryByText("Texas rules")).not.toBeInTheDocument();
      expect(screen.getByText("elsewhere")).toBeInTheDocument();
    });

    it("follows the picker without a reload", () => {
      render(gate);
      act(() => {
        window.localStorage.setItem("fisheye.state", "CO");
        window.dispatchEvent(new Event("fisheye:state"));
      });
      expect(screen.queryByText("Texas rules")).not.toBeInTheDocument();
    });
  });

  describe("OtherStateRules", () => {
    it("names the state and points to its agency without inventing a link", async () => {
      setState("CO");
      const { container } = render(<OtherStateRules subject="Bait rules" />);
      expect(screen.getByRole("heading", { name: "Bait rules differ by state" })).toBeInTheDocument();
      await waitFor(() => expect(screen.getByText(/Colorado's rules yet/)).toBeInTheDocument());
      expect(container.querySelector("a")).toBeNull();
    });
  });

  describe("LimitsNote", () => {
    const TEXAS = "https://tpwd.texas.gov/limits";

    it("links TPWD for Texas", () => {
      setState("TX");
      render(<LimitsNote texasUrl={TEXAS} />);
      expect(screen.getByRole("link", { name: "Check TPWD's current limits" })).toHaveAttribute("href", TEXAS);
    });

    it("tells another state's reader to ask their own agency, with no link", async () => {
      setState("CO");
      const { container } = render(<LimitsNote texasUrl={TEXAS} />);
      // Before the state list arrives it says "your state's", never a bare code.
      expect(screen.getByText(/your state's fish and wildlife agency/)).toBeInTheDocument();
      await waitFor(() => expect(screen.getByText(/Colorado's fish and wildlife agency/)).toBeInTheDocument());
      expect(container.querySelector("a")).toBeNull();
    });

    it("says limits vary by state when none is chosen", () => {
      render(<LimitsNote texasUrl={TEXAS} />);
      expect(screen.getByText(/vary by state, species and lake/)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "TPWD" })).toHaveAttribute("href", TEXAS);
    });
  });

  describe("StatePicker", () => {
    it("lists the states with rules written first, and remembers the choice", async () => {
      render(<StatePicker />);
      const select = await screen.findByRole("combobox");
      expect(screen.getByRole("group", { name: "Rules written" })).toHaveTextContent("Texas");
      expect(screen.getByRole("group", { name: "Rules not written yet" })).toHaveTextContent("Colorado");

      fireEvent.change(select, { target: { value: "CO" } });
      expect(window.localStorage.getItem("fisheye.state")).toBe("CO");
      fireEvent.change(select, { target: { value: "" } });
      expect(window.localStorage.getItem("fisheye.state")).toBeNull();
    });
  });
});
