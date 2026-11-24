import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/i18n/client";
import type { AskLakes } from "@/lib/api/types";
import { LakeAnswer } from "./LakeAnswer";

const NEAR_ZIP: AskLakes = {
  kind: "list",
  lakes: [],
  same_name: [],
  place: "02467 (Boston, MA)",
  place_latitude: 42.31412,
  place_longitude: -71.15293,
  state: null,
  fish: [],
  fish_slugs: [],
  answers_it: true,
};

describe("Ask's answer near a place (a ZIP code or a town)", () => {
  it("links to the map there, even with no lake on record", () => {
    render(<LakeAnswer lakes={NEAR_ZIP} />);
    expect(screen.getByText("FishEye has no lake with fish on record near 02467 (Boston, MA) yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See lakes near 02467 (Boston, MA) on the map →" })).toHaveAttribute(
      "href",
      "/map?at=42.3141,-71.1529&place=02467%20(Boston%2C%20MA)",
    );
  });

  it("keeps the page's language in the link", () => {
    render(
      <I18nProvider locale="zh">
        <LakeAnswer lakes={NEAR_ZIP} />
      </I18nProvider>,
    );
    const link = screen.getByRole("link", { name: "在地图上查看02467 (Boston, MA)附近的水域 →" });
    expect(link.getAttribute("href")).toMatch(/^\/zh\/map\?at=42\.3141,-71\.1529&place=/);
  });

  it("lists the lakes on record and the map below them", () => {
    render(
      <LakeAnswer
        lakes={{
          ...NEAR_ZIP,
          lakes: [
            {
              id: 7, name: "Lake Fork", state_code: "TX", county: "Wood", data_tier: "verified",
              public_access_status: "open", species: [], reported: [], asked: [], access_points: 2,
              fish_attractors: 0, agency_url: null, credit: null,
            },
          ] as unknown as AskLakes["lakes"],
        }}
      />,
    );
    expect(screen.getByRole("link", { name: "Lake Fork" })).toHaveAttribute("href", "/map?lake=7");
    expect(screen.getByRole("link", { name: /See lakes near/ })).toBeInTheDocument();
  });

  it("has no map link for lakes in a state, which has no one point", () => {
    render(<LakeAnswer lakes={{ ...NEAR_ZIP, place: null, place_latitude: null, place_longitude: null, state: "TX" }} />);
    expect(screen.queryByRole("link")).toBeNull();
  });
});
