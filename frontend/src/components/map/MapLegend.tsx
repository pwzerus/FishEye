"use client";

import { useT } from "@/i18n/client";

// What each pin colour means. The swatches are the real marker image with
// the same CSS classes LakeMap.tsx gives its icons, so they can't drift.

const ROWS = [
  { className: "", label: "legendOfficial" },
  { className: "is-reported", label: "legendReported" },
  { className: "is-osm", label: "legendOsm" },
] as const;

export function MapLegend({ showPins = false, showShops = false }: { showPins?: boolean; showShops?: boolean }) {
  const t = useT().map;
  return (
    <div className="map-legend" aria-label={t.legend}>
      {ROWS.map((row) => (
        <div key={row.label} className="map-legend-row">
          <span aria-hidden="true" className={`legend-water-dot ${row.className}`} />
          <span>{t[row.label]}</span>
        </div>
      ))}
      {showPins && (
        <div className="map-legend-row">
          <span className="legend-catch" aria-hidden="true" />
          <span>{t.legendCatch}</span>
        </div>
      )}
      {showShops && (
        <div className="map-legend-row">
          <span className="legend-shop" aria-hidden="true" />
          <span>{t.legendShop}</span>
        </div>
      )}
    </div>
  );
}
