"use client";

import type { Feature, FeatureCollection, Geometry } from "geojson";
import L from "leaflet";
import { useEffect, useState } from "react";
import { GeoJSON, useMap } from "react-leaflet";

type StateProps = { code: string; name: string };
type StatesFile = FeatureCollection<Geometry, StateProps>;

// Census state boundaries, built once from us-atlas (see the file's
// "source" field). A static file rather than a dependency: 55 KB gzipped,
// fetched only by the map page, cached across remounts of the map.
let statesFile: Promise<StatesFile> | null = null;
function loadStates(): Promise<StatesFile> {
  statesFile ??= fetch("/geo/us-states.json").then((r) => {
    if (!r.ok) throw new Error(`us-states.json: ${r.status}`);
    return r.json() as Promise<StatesFile>;
  });
  return statesFile;
}

/**
 * The way into the map at country scale: every state as a shape. Clicking a
 * state FishEye has lakes for reports it through `onEnter`; MapView then
 * switches the map into exploring mode and fits it to the state
 * (zoomPolicy.ts). After that it's the ordinary map — pan anywhere, across
 * state lines too. The state is an entrance, not a filter: someone north of
 * Dallas may be closest to a lake on the Oklahoma side, and that should just
 * show up.
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
  onEnter: (bounds: L.LatLngBounds) => void;
}) {
  const map = useMap();
  const [data, setData] = useState<StatesFile | null>(null);

  useEffect(() => {
    let live = true;
    loadStates()
      .then((d) => live && setData(d))
      .catch((e: unknown) => {
        statesFile = null; // let a later mount retry
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
        onEnter((layer as L.Polygon).getBounds());
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
