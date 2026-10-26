"use client";

import type { Feature, Geometry } from "geojson";
import L from "leaflet";
import { useEffect, useState } from "react";
import { GeoJSON, useMap } from "react-leaflet";

import { type StateProps, type StatesFile, loadStates } from "./usStates";

/**
 * The way into the map at country scale: every state as a shape. Clicking a
 * state FishEye has lakes for reports it through `onEnter`; MapView then
 * switches the map into exploring mode and fits it to the state
 * (zoomPolicy.ts). From then on the map is that state alone: only its lakes,
 * and it can't be zoomed or panned out past the state. The way to another
 * state is back through this map.
 *
 * A state with nothing on file says so and stays put, rather than flying the
 * person to an empty map.
 *
 * `covered` is null while coverage is loading or if it failed. Every state
 * is then treated as open: greying out the whole country because one request
 * failed would say "nothing here" when the truth is "don't know".
 */
export function StatesLayer({
  covered,
  onEnter,
}: {
  covered: Set<string> | null;
  onEnter: (bounds: L.LatLngBounds, code: string) => void;
}) {
  const map = useMap();
  const [data, setData] = useState<StatesFile | null>(null);

  useEffect(() => {
    let live = true;
    loadStates()
      .then((d) => live && setData(d))
      .catch((e: unknown) => {
        console.error("state boundaries failed to load:", e);
      });
    return () => {
      live = false;
    };
  }, []);

  if (!data) return null;

  const isOpen = (code: string) => covered === null || covered.has(code);

  function onEachFeature(feature: Feature<Geometry, StateProps>, layer: L.Layer) {
    const { code, name } = feature.properties;
    const open = isOpen(code);
    layer.bindTooltip(open ? name : `${name} · coming soon`, {
      sticky: true,
      direction: "top",
      className: "state-tooltip",
    });
    layer.on("click", (e: L.LeafletMouseEvent) => {
      if (open) {
        layer.closeTooltip();
        onEnter((layer as L.Polygon).getBounds(), code);
        return;
      }
      // The hover tooltip says the same thing; don't leave it under the popup.
      layer.closeTooltip();
      const body = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = name;
      body.append(title, document.createElement("br"), "Not on FishEye yet — coming soon.");
      L.popup({ className: "state-popup", closeButton: false, autoPan: false })
        .setLatLng(e.latlng)
        .setContent(body)
        .openOn(map);
    });
  }

  return (
    <GeoJSON
      // GeoJSON's data, style and handlers are read once; remount when the
      // coverage answer arrives so states pick up their lit or grey state.
      key={covered === null ? "unknown" : [...covered].sort().join(",")}
      data={data}
      style={(feature) => ({
        className: `state-shape ${isOpen(feature?.properties.code ?? "") ? "is-open" : "is-soon"}`,
      })}
      onEachFeature={onEachFeature}
    />
  );
}
