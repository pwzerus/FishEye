"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import L from "leaflet";
import type { StyleSpecification } from "maplibre-gl";
import { useEffect, useState } from "react";
import { TileLayer, useMap } from "react-leaflet";

import { useBasemapChoice } from "@/lib/map/basemapChoice";
import { hideAirportIcons, styleAttribution, withLinkedAttributions } from "@/lib/map/basemapStyle";
import { MAP_STYLE_URL, PLAIN_STYLE_URL, TILE_ATTRIBUTION, TILE_URL } from "@/lib/map/tiles";

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
 * Two vector styles: the plain map (free, the default) and satellite
 * (MapTiler, billed per tile), picked with the map's satellite button
 * (lib/map/basemapChoice.ts). Only maps given `satellite` (a state's, a
 * lake's) follow that choice; the rest are always plain. If the picked one
 * fails, the other is tried.
 *
 * Falls back to raster, never to a blank map: when the browser has no WebGL,
 * or both styles or the renderer fail.
 *
 * MapLibre (≈270 KB gzipped) is imported only when it is about to be used, so
 * a raster-only deployment never downloads it. Version 5, not 6: 6 resolves
 * its web worker's URL relative to its own file at runtime, which a bundler
 * that moves the file breaks; 5 inlines the worker.
 */
export function BaseMap({ satellite = false }: { satellite?: boolean }) {
  const map = useMap();
  const picked = useBasemapChoice();
  const choice = satellite ? picked : "plain";
  const [mode, setMode] = useState<"vector" | "raster">(() => (hasWebGL() ? "vector" : "raster"));
  const styles = (choice === "satellite" ? [MAP_STYLE_URL, PLAIN_STYLE_URL] : [PLAIN_STYLE_URL, MAP_STYLE_URL]).filter(
    (url): url is string => Boolean(url),
  );
  const stylesKey = styles.join(" ");

  useEffect(() => {
    if (mode !== "vector") return;
    let layer: L.Layer | null = null;
    let cancelled = false;

    (async () => {
      const bridge = await import("@maplibre/maplibre-gl-leaflet").catch(() => null);
      for (const url of stylesKey.split(" ")) {
        if (cancelled || !bridge) break;
        try {
          const style = await fetch(url)
            .then((r) => {
              if (!r.ok) throw new Error(`basemap style: ${r.status}`);
              return r.json() as Promise<StyleSpecification>;
            })
            .then((s) => withLinkedAttributions(s));
          if (cancelled) return;
          layer = bridge.maplibreGL({
            style: hideAirportIcons(style),
            // One credit, computed from the style (see styleAttribution);
            // left to itself the bridge shows MapTiler's twice.
            attributionControl: { customAttribution: styleAttribution(style, TILE_ATTRIBUTION) },
          });
          layer.addTo(map);
          return;
        } catch (e) {
          console.error("vector basemap unavailable:", url.split("?")[0], e);
          if (layer) map.removeLayer(layer);
          layer = null;
        }
      }
      if (!cancelled) setMode("raster");
    })();

    return () => {
      cancelled = true;
      if (layer) map.removeLayer(layer);
    };
  }, [map, mode, stylesKey]);

  // No MapTiler logo: the site is on MapTiler's paid Flex plan (since
  // 2026-11-05), which requires the logo only on 3D maps. The text credit
  // "© MapTiler © OpenStreetMap contributors" in the attribution stays, as
  // every plan requires it.
  return mode === "raster" ? <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} /> : null;
}
