import { act, render } from "@testing-library/react";
import { MapContainer } from "react-leaflet";
import { describe, expect, it, vi } from "vitest";

import { ZoomOutLimit } from "./LakeMap";

// Leaflet clamps a refused zoom-out before any zoom event fires, so the
// prompt depends on watching raw input at the zoom floor.
function setup(zoom: number) {
  const onBlocked = vi.fn();
  const { container } = render(
    <MapContainer center={[31, -97]} zoom={zoom} minZoom={5} maxZoom={18} style={{ height: 300, width: 300 }}>
      <ZoomOutLimit onBlocked={onBlocked} />
    </MapContainer>,
  );
  const map = container.querySelector(".leaflet-container") as HTMLElement;
  return { onBlocked, map };
}

describe("ZoomOutLimit", () => {
  it("asks when the wheel zooms out at the floor", () => {
    const { onBlocked, map } = setup(5);
    act(() => {
      map.dispatchEvent(new WheelEvent("wheel", { deltaY: 100 }));
    });
    expect(onBlocked).toHaveBeenCalledTimes(1);
  });

  it("asks when the minus key is pressed at the floor", () => {
    const { onBlocked, map } = setup(5);
    act(() => {
      map.dispatchEvent(new KeyboardEvent("keydown", { key: "-" }));
    });
    expect(onBlocked).toHaveBeenCalledTimes(1);
  });

  it("does not ask when there is room to zoom out", () => {
    const { onBlocked, map } = setup(8);
    act(() => {
      map.dispatchEvent(new WheelEvent("wheel", { deltaY: 100 }));
      map.dispatchEvent(new KeyboardEvent("keydown", { key: "-" }));
    });
    expect(onBlocked).not.toHaveBeenCalled();
  });

  it("does not ask when zooming in at the floor", () => {
    const { onBlocked, map } = setup(5);
    act(() => {
      map.dispatchEvent(new WheelEvent("wheel", { deltaY: -100 }));
      map.dispatchEvent(new KeyboardEvent("keydown", { key: "+" }));
    });
    expect(onBlocked).not.toHaveBeenCalled();
  });

  it("asks once for a burst of wheel events", () => {
    const { onBlocked, map } = setup(5);
    act(() => {
      for (let i = 0; i < 6; i += 1) map.dispatchEvent(new WheelEvent("wheel", { deltaY: 100 }));
    });
    expect(onBlocked).toHaveBeenCalledTimes(1);
  });
});
