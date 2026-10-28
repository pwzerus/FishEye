import { act, render } from "@testing-library/react";
import type L from "leaflet";
import { MapContainer } from "react-leaflet";
import { describe, expect, it } from "vitest";

import { YouAreHere } from "./LakeMap";

function draw(accuracy: number, zoom = 15) {
  let map: L.Map | null = null;
  const { container } = render(
    <MapContainer ref={(m) => { map = m; }} center={[33.9, -84.2]} zoom={zoom} style={{ height: 300, width: 300 }}>
      <YouAreHere at={{ latitude: 33.9, longitude: -84.2, accuracy }} />
    </MapContainer>,
  );
  return { container, map: () => map! };
}

// Shapes drawn on the map's SVG layer, not the attribution's flag icon.
const shapes = (map: HTMLElement) => map.querySelectorAll(".leaflet-overlay-pane path");
const dot = (map: HTMLElement) => map.querySelector(".leaflet-marker-pane .you-are-here-dot");

describe("YouAreHere", () => {
  it("labels the person's position and draws the fix's uncertainty", () => {
    const { container } = draw(40);
    expect(container.querySelector(".leaflet-tooltip.you-are-here")?.textContent).toBe("You are here");
    // The dot is a marker, which Leaflet keeps the same size while the map
    // zooms; only the accuracy circle is on the SVG layer it scales.
    expect(dot(container)).not.toBeNull();
    expect(shapes(container)).toHaveLength(1);
    // Neither takes clicks.
    expect(dot(container)?.classList.contains("leaflet-interactive")).toBe(false);
    expect(shapes(container)[0].classList.contains("leaflet-interactive")).toBe(false);
  });

  it("draws only the dot when the browser gives no accuracy", () => {
    const { container } = draw(0);
    expect(dot(container)).not.toBeNull();
    expect(shapes(container)).toHaveLength(0);
  });

  it("leaves out the accuracy circle until the map is close enough for it to show", () => {
    // 40 m is well under a pixel at state scale: a flight from there would
    // scale Leaflet's 1 px minimum up across the whole map.
    const { container, map } = draw(40, 6);
    expect(dot(container)).not.toBeNull();
    expect(shapes(container)).toHaveLength(0);

    act(() => {
      map().setZoom(15, { animate: false });
    });
    expect(shapes(container)).toHaveLength(1);
  });
});
