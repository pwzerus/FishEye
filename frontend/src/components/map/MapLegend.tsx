// What each pin colour means. The swatches are the real marker image with
// the same CSS classes LakeMap.tsx gives its icons, so they can't drift.

const ROWS = [
  { className: "", label: "Official lake information" },
  { className: "is-reported", label: "Species reported · not verified" },
  { className: "is-osm", label: "Mapped water · access unknown" },
];

export function MapLegend({ showPins = false }: { showPins?: boolean }) {
  return (
    <div className="map-legend" aria-label="Map legend">
      {ROWS.map((row) => (
        <div key={row.label} className="map-legend-row">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <span aria-hidden="true" className={`legend-water-dot ${row.className}`} />
          <span>{row.label}</span>
        </div>
      ))}
      {showPins && (
        <div className="map-legend-row">
          <span className="legend-catch" aria-hidden="true" />
          <span>Community pin (an angler&apos;s report)</span>
        </div>
      )}
    </div>
  );
}
