"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import L from "leaflet";
import type { StyleSpecification } from "maplibre-gl";
import { useEffect, useState } from "react";
import { TileLayer, useMap } from "react-leaflet";

import { hideAirportIcons, styleAttribution } from "@/lib/map/basemapStyle";
import { MAP_STYLE_URL, TILE_ATTRIBUTION, TILE_URL } from "@/lib/map/tiles";

function hasWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

/**
 * The background under every map in the app: a vector basemap when one is
 * configured, the raster tiles otherwise.
 *
 * Vector is preferred because its layers can be edited before drawing — it
 * is how the airstrip icons that litter rural Texas are removed while roads
 * stay readable (src/lib/map/basemapStyle.ts); no stock raster style does
 * both. It is drawn by MapLibre inside Leaflet's tile pane, so every marker,
 * cluster and the states layer stay ordinary Leaflet layers above it.
 *
 * Falls back to raster, never to a blank map: when NEXT_PUBLIC_MAP_STYLE_URL
 * is unset, the browser has no WebGL, or the style or the renderer fails.
 *
 * MapLibre (≈270 KB gzipped) is imported only when it is about to be used, so
 * a raster-only deployment never downloads it. Version 5, not 6: 6 resolves
 * its web worker's URL relative to its own file at runtime, which a bundler
 * that moves the file breaks; 5 inlines the worker.
 */
export function BaseMap() {
  const map = useMap();
  const [mode, setMode] = useState<"vector" | "raster">(() =>
    MAP_STYLE_URL && hasWebGL() ? "vector" : "raster",
  );

  useEffect(() => {
    if (mode !== "vector" || !MAP_STYLE_URL) return;
    let layer: L.Layer | null = null;
    let cancelled = false;

    (async () => {
      try {
        const [style, bridge] = await Promise.all([
          fetch(MAP_STYLE_URL).then((r) => {
            if (!r.ok) throw new Error(`basemap style: ${r.status}`);
            return r.json() as Promise<StyleSpecification>;
          }),
          import("@maplibre/maplibre-gl-leaflet"),
        ]);
        if (cancelled) return;
        layer = bridge.maplibreGL({
          style: hideAirportIcons(style),
          // One credit, computed from the style (see styleAttribution);
          // left to itself the bridge shows MapTiler's twice.
          attributionControl: { customAttribution: styleAttribution(style, TILE_ATTRIBUTION) },
        });
        layer.addTo(map);
      } catch (e) {
        console.error("vector basemap unavailable, using raster tiles:", e);
        if (layer) map.removeLayer(layer);
        layer = null;
        if (!cancelled) setMode("raster");
      }
    })();

    return () => {
      cancelled = true;
      if (layer) map.removeLayer(layer);
    };
  }, [map, mode]);

  return mode === "raster" ? <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} /> : null;
}
