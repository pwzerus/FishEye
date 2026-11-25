import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Jurisdiction, WaterbodyListItem } from "@/lib/api/types";
import { I18nProvider } from "@/i18n/client";
import { FirstTrip, KIT, kitText, LicenseLine } from "./FirstTrip";

const RULES = { bait_rules: [], bait_rules_sources: [], bait_rules_on_every_bait_question: false };
const GEORGIA: Jurisdiction = {
  ...RULES, code: "GA", name: "Georgia", covered: true, agency: "Georgia Wildlife Resources Division",
  agency_short: "Georgia WRD", limits_url: "https://example.com/ga-limits", license_url: "https://example.com/ga-license",
  license_from_age: 16, license_topic: "rule-license-ga", first_trip_topic: "start-first-trip-ga",
};
const COLORADO: Jurisdiction = {
  ...RULES, code: "CO", name: "Colorado", covered: false, agency: "Colorado Parks and Wildlife",
  agency_short: "CPW", limits_url: "https://example.com/co-regs", license_url: "https://example.com/co-license",
};

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listJurisdictions: vi.fn(async () => [GEORGIA, COLORADO]), listWaterbodies: vi.fn() };
});
const { listWaterbodies } = await import("@/lib/api/client");

function lake(id: number, name: string, latitude: number, status = "open"): WaterbodyListItem {
  return {
    id, name, latitude, longitude: -84.14, field_tested: false, public_access_status: status as WaterbodyListItem["public_access_status"],
    data_tier: "verified", water_type: "lake", reported_species_count: 0,
  };
}

describe("LicenseLine", () => {
  it("answers in a line where FishEye wrote the state's licence rules", () => {
    render(<LicenseLine state={GEORGIA} />);
    expect(screen.getByText("In Georgia you need one from age 16. Under 16, you don't.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get a license ↗" })).toHaveAttribute("href", GEORGIA.license_url);
    expect(screen.getByRole("link", { name: "Details" })).toHaveAttribute("href", "/handbook#rule-license-ga");
  });

  it("sends anywhere else to the agency, without guessing an age", () => {
    render(<LicenseLine state={COLORADO} />);
    expect(screen.getByText(/CPW sets who needs one/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "License page ↗" })).toHaveAttribute("href", COLORADO.license_url);
    expect(screen.queryByText(/from age/)).not.toBeInTheDocument();
  });

  it("asks for the state first", () => {
    render(<LicenseLine state={null} />);
    expect(screen.getByText(/pick yours above/)).toBeInTheDocument();
  });
});

describe("FirstTrip", () => {
  beforeEach(() => {
    window.localStorage.setItem("fisheye.state", "GA");
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition: (ok: PositionCallback) => ok({ coords: { latitude: 33.91, longitude: -84.14 } } as GeolocationPosition) },
    });
  });
  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("lists the nearest official lakes open to the public, nearest first", async () => {
    vi.mocked(listWaterbodies).mockResolvedValue([
      lake(1, "Far Lake", 34.2),
      lake(2, "Closed Lake", 33.912, "closed"),
      lake(3, "Near Lake", 33.93),
      lake(4, "Middle Lake", 34.0),
      lake(5, "Farthest Lake", 34.3),
    ]);
    render(<FirstTrip />);
    fireEvent.click(screen.getByRole("button", { name: "Find spots near me" }));
    const names = await waitFor(() => {
      const list = document.querySelector(".trip-spots");
      expect(list).not.toBeNull();
      return within(list as HTMLElement).getAllByRole("link").map((a) => a.textContent);
    });
    expect(names).toEqual(["Near Lake", "Middle Lake", "Far Lake"]);
    expect(vi.mocked(listWaterbodies)).toHaveBeenCalledWith(expect.objectContaining({ tier: "verified", lat: 33.91, lng: -84.14 }));
  });

  it("says so, and still offers the map, when none is near", async () => {
    vi.mocked(listWaterbodies).mockResolvedValue([]);
    render(<FirstTrip />);
    fireEvent.click(screen.getByRole("button", { name: "Find spots near me" }));
    expect(await screen.findByText("No official lakes within 25 miles yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open the map" })).toHaveAttribute("href", "/map");
  });

  it.each([
    [1, "Location is blocked for this site. Allow it in your browser settings, or find a lake on the map."],
    [2, "Your device couldn't find your location. Try again, or find a lake on the map."],
  ])("says why location failed (error code %i) and lets them try again", async (code, message) => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: (_ok: PositionCallback, fail: PositionErrorCallback) =>
          fail({ code, message: "" } as GeolocationPositionError),
      },
    });
    render(<FirstTrip />);
    fireEvent.click(screen.getByRole("button", { name: "Find spots near me" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "Open the map" })).toHaveAttribute("href", "/map");
  });

  it("doesn't blame location when the lakes fail to load", async () => {
    vi.mocked(listWaterbodies).mockRejectedValue(new Error("down"));
    render(<FirstTrip />);
    fireEvent.click(screen.getByRole("button", { name: "Find spots near me" }));
    expect(await screen.findByText("Couldn't load nearby lakes. Try again.")).toBeInTheDocument();
    expect(screen.queryByText(/your location/)).not.toBeInTheDocument();
  });

  it("remembers what was ticked off for the next visit", () => {
    const first = render(<FirstTrip />);
    fireEvent.click(screen.getAllByRole("checkbox")[0]);
    expect(screen.getAllByRole("checkbox")[0]).toBeChecked();
    first.unmount();
    render(<FirstTrip />);
    expect(screen.getAllByRole("checkbox")[0]).toBeChecked();
    expect(screen.getAllByRole("checkbox")[1]).not.toBeChecked();
    window.localStorage.removeItem("fisheye.kit");
  });

  // 2026-11-25: a friend's phone called the downloaded list corrupted. It was
  // a web page named .doc; now it's text, and it lists what isn't ticked yet.
  it("downloads what is left to buy as a text file any phone opens", () => {
    const blobs: Blob[] = [];
    vi.spyOn(URL, "createObjectURL").mockImplementation((b) => {
      blobs.push(b as Blob);
      return "blob:list";
    });
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const clicked: HTMLAnchorElement[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push(this);
    });
    render(<FirstTrip />);
    fireEvent.click(screen.getAllByRole("checkbox")[0]);
    fireEvent.click(screen.getByRole("button", { name: "Download the list" }));
    expect(blobs).toHaveLength(1);
    expect(blobs[0].type).toBe("text/plain;charset=utf-8");
    expect(clicked[0].download).toBe("fisheye-shopping-list.txt");
    window.localStorage.removeItem("fisheye.kit");
  });

  it("writes the list English first, the reader's language under each line", () => {
    const text = kitText(KIT.slice(1, 3), "购物清单", "zh");
    expect(text).toContain("☐ Small bobbers\r\n   小浮漂");
    expect(text).not.toContain("Rod and reel");
    expect(kitText(KIT, "Shopping list", "en")).not.toContain("小浮漂");
  });

  it("says everything is got instead of offering an empty list", () => {
    window.localStorage.setItem("fisheye.kit", JSON.stringify(KIT.map((item) => item.topic)));
    render(<FirstTrip />);
    expect(screen.queryByRole("button", { name: "Download the list" })).not.toBeInTheDocument();
    expect(screen.getByText("You have everything on the list.")).toBeInTheDocument();
    window.localStorage.removeItem("fisheye.kit");
  });

  it("names the kit in the chosen language, with the English the shop uses", async () => {
    const { unmount } = render(<FirstTrip />);
    expect(screen.queryByText("小浮漂")).not.toBeInTheDocument();
    unmount();
    render(
      <I18nProvider locale="zh">
        <FirstTrip />
      </I18nProvider>,
    );
    expect(await screen.findByText("小浮漂")).toBeInTheDocument();
    expect(screen.getByText("Small bobbers")).toBeInTheDocument();
    // The shop card: English for the clerk, the reader's language under it.
    fireEvent.click(screen.getByRole("button", { name: "到店出示给店员" }));
    expect(screen.getByRole("heading", { name: "购物清单" })).toBeInTheDocument();
  });
});
