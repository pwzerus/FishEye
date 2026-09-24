// What each pin colour means. The swatches are the real marker image with
// the same CSS classes LakeMap.tsx gives its icons, so they can't drift.
const PIN = "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png";

const ROWS = [
  { className: "", label: "Verified: official fish and access data" },
  { className: "osm-marker-reported", label: "Fish on record, not verified" },
  { className: "osm-marker", label: "On the map only, nothing verified" },
];

export function MapLegend() {
  return (
    <div className="map-legend" aria-label="Map legend">
      {ROWS.map((row) => (
        <div key={row.label} className="map-legend-row">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={PIN} alt="" width={10} height={16} className={row.className} />
          <span>{row.label}</span>
        </div>
      ))}
    </div>
  );
}
