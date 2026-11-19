import { fireEvent, render, waitFor } from "@testing-library/react";
import { MapContainer } from "react-leaflet";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { MESSAGES } from "@/i18n/messages";
import type { CoastalSpot } from "@/lib/api/types";
import { CoastalSpotMarkers } from "./CoastalSpotLayer";

const SPOT: CoastalSpot = {
  id: 1,
  name: "Hanalei Pier",
  kind: "pier",
  coast: "hawaii",
  latitude: 22.2127,
  longitude: -159.4975,
  state_code: "HI",
  fishing_tagged: false,
  fee: null,
  opening_hours: null,
  lit: false,
  operator: null,
  website: null,
  no_license: false,
  license_note: null,
  source: "osm",
  source_url: "https://www.openstreetmap.org/way/1",
  osm_url: "https://www.openstreetmap.org/way/1",
};

// jsdom lays nothing out: give the map a size, or the clusterer sees a
// 0x0 view and draws no marker (as in LakeMapClusters.test.tsx).
const sizes = ["clientWidth", "clientHeight"] as const;
const saved = sizes.map((p) => Object.getOwnPropertyDescriptor(HTMLElement.prototype, p));
beforeEach(() => {
  sizes.forEach((p, i) =>
    Object.defineProperty(HTMLElement.prototype, p, {
      configurable: true,
      get(this: HTMLElement) {
        return this.classList.contains("leaflet-container") ? [800, 600][i] : 0;
      },
    }),
  );
});
afterEach(() => {
  sizes.forEach((p, i) => {
    const d = saved[i];
    if (d) Object.defineProperty(HTMLElement.prototype, p, d);
    else delete (HTMLElement.prototype as unknown as Record<string, unknown>)[p];
  });
});

describe("CoastalSpotMarkers", () => {
  it("marks each spot, named for screen readers, an unnamed one by its kind", () => {
    const { container } = render(
      <MapContainer center={[22.2, -159.5]} zoom={12} maxZoom={18} style={{ height: 300, width: 300 }}>
        <CoastalSpotMarkers spots={[SPOT, { ...SPOT, id: 2, name: null, kind: "boat_ramp" }]} />
      </MapContainer>,
    );
    const titles = [...container.querySelectorAll(".leaflet-marker-pane .coast-marker-wrap")].map((m) => m.getAttribute("title"));
    expect(titles.sort()).toEqual([MESSAGES.en.coast.boat_ramp, "Hanalei Pier, Fishing pier"]);
  });

  it("says a California public pier needs no license, and where next to it one is needed", async () => {
    const pier: CoastalSpot = {
      ...SPOT, name: "Newport Harbor North Jetty", kind: "jetty", coast: "pacific", state_code: "CA",
      latitude: 33.5933, longitude: -117.8811,
      no_license: true, license_note: "shore_wall", source: "cdfw",
      source_url: "https://data-cdfw.opendata.arcgis.com/datasets/CDFW::public-piers-and-jetties-r7-cdfw-ds3090",
      osm_url: null,
    };
    const { container } = render(
      <MapContainer center={[33.59, -117.88]} zoom={14} maxZoom={18} style={{ height: 300, width: 300 }}>
        <CoastalSpotMarkers spots={[pier]} />
      </MapContainer>,
    );
    fireEvent.click(container.querySelector(".coast-marker-wrap") as HTMLElement);
    const t = MESSAGES.en.coast;
    await waitFor(() => expect(document.querySelector(".coast-popup")?.textContent).toContain(t.noLicense));
    const popup = document.querySelector(".coast-popup") as HTMLElement;
    expect(popup.textContent).toContain(t.licenseNotes.shore_wall);
    expect(popup.textContent).not.toContain(t.checkRules);
    const links = [...popup.querySelectorAll("a.shop-pop-source")].map((a) => a.textContent);
    expect(links).toEqual([t.sourceCdfw]); // not on OpenStreetMap: no OSM credit
  });

  it("shows spots close together as one sea-blue count when zoomed out", () => {
    const near = [SPOT, { ...SPOT, id: 2, latitude: 22.2129 }, { ...SPOT, id: 3, longitude: -159.4971 }];
    const { container } = render(
      <MapContainer center={[22.2, -159.5]} zoom={9} maxZoom={18} style={{ height: 300, width: 300 }}>
        <CoastalSpotMarkers spots={near} />
      </MapContainer>,
    );
    expect(container.querySelectorAll(".leaflet-marker-pane .coast-marker-wrap")).toHaveLength(0);
    const cluster = container.querySelector(".leaflet-marker-pane .coast-cluster") as HTMLElement;
    expect(cluster.textContent).toBe(`3 ${MESSAGES.en.coast.cluster}`);
  });

  it("says a fee plainly", () => {
    const t = MESSAGES.en.coast;
    expect(t.fee("yes")).toBe("Fee to fish");
    expect(t.fee("no")).toBe("Free");
    expect(t.fee("$5")).toBe("Fee: $5");
  });
});
