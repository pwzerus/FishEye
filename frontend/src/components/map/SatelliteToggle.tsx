"use client";

import { useT } from "@/i18n/client";
import { setBasemapChoice, useBasemapChoice } from "@/lib/map/basemapChoice";
import { MAP_STYLE_URL } from "@/lib/map/tiles";

/**
 * The satellite button: on a state's map and a lake's map only. The country
 * map is always the plain map (the product owner, 2026-11-12), so its state
 * borders stay readable and it never draws billed tiles.
 */
export function SatelliteToggle() {
  const t = useT().map;
  const basemap = useBasemapChoice();
  if (!MAP_STYLE_URL) return null;
  const on = basemap === "satellite";
  return (
    <button
      type="button"
      className={on ? "map-toggle active" : "map-toggle"}
      aria-pressed={on}
      aria-label={t.satellite}
      onClick={() => setBasemapChoice(on ? "plain" : "satellite")}
    >
      <svg className="map-toggle-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M4 10l6-6 4 4-6 6zM14 20l6-6-4-4-6 6zM11 13l2-2M5 19a4 4 0 0 1 0-5M2 21a8 8 0 0 1 0-10" strokeLinecap="round" strokeLinejoin="round" />
      </svg>{" "}
      <span className="fab-label">{t.satellite}</span>
    </button>
  );
}
