import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Jurisdiction } from "@/lib/api/types";
import { LakeRulesRow } from "./LakeRulesRow";

const CALIFORNIA: Jurisdiction = {
  code: "CA", name: "California", covered: true, agency: "California Department of Fish and Wildlife",
  agency_short: "CDFW", limits_url: "https://example.com/ca-limits", license_url: "https://example.com/ca-license",
  bait_rules: ["In most of California's inland waters, live or dead fin fish may not be used as bait."],
  bait_rules_sources: [], bait_rules_on_every_bait_question: true, license_from_age: 16,
};
const OHIO: Jurisdiction = {
  code: "OH", name: "Ohio", covered: false, agency: "Ohio Division of Wildlife", agency_short: "ODNR",
  limits_url: "https://example.com/oh-regs", license_url: "https://example.com/oh-license",
  bait_rules: [], bait_rules_sources: [], bait_rules_on_every_bait_question: false,
};

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listJurisdictions: vi.fn(async () => [CALIFORNIA, OHIO]) };
});

// The visiting angler of the 2026-10-29 persona doc: the rule that differs
// from home, where they are deciding where to fish.
describe("LakeRulesRow", () => {
  it("gives the licence age, the limits and the bait rules of the lake's state", async () => {
    render(<LakeRulesRow stateCode="CA" />);
    expect(await screen.findByRole("link", { name: "License from age 16 ↗" })).toHaveAttribute("href", CALIFORNIA.license_url);
    expect(screen.getByRole("link", { name: "Limits ↗" })).toHaveAttribute("href", CALIFORNIA.limits_url);
    expect(screen.queryByText(/fin fish may not be used/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Bait rules" }));
    expect(screen.getByText(/fin fish may not be used as bait/)).toBeInTheDocument();
  });

  it("links a state FishEye hasn't written rules for to its agency", async () => {
    render(<LakeRulesRow stateCode="OH" />);
    expect(await screen.findByRole("link", { name: "Regulations ↗" })).toHaveAttribute("href", OHIO.limits_url);
    expect(screen.getByRole("link", { name: "License ↗" })).toHaveAttribute("href", OHIO.license_url);
    expect(screen.queryByRole("button", { name: "Bait rules" })).not.toBeInTheDocument();
  });

  it("says nothing when the lake's state is unknown", () => {
    const { container } = render(<LakeRulesRow stateCode={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
