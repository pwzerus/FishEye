// Builds public/geo/us-states.json — the state shapes the map shows at
// country scale (src/components/map/StatesLayer.tsx) — from us-atlas: U.S.
// Census Bureau cartographic boundaries, public domain; packaging ISC.
//
// The app ships the output, not these packages: it is a one-off conversion,
// so there is no reason for topojson-client to be a dependency. To rebuild:
//
//   npm install --no-save us-atlas@3.0.1 topojson-client@3.1.0
//   node scripts/build-us-states.cjs
//
// 2 decimals (~1 km) because the layer is only drawn below zoom 5, where one
// screen pixel is already ~10 km. Output is ~217 KB, ~55 KB gzipped.
const fs = require("fs");
const path = require("path");
const topo = require("us-atlas/states-10m.json");
const { feature } = require("topojson-client");

const OUT = process.argv[2] || path.join(__dirname, "..", "public", "geo", "us-states.json");
const DECIMALS = Number(process.argv[3] || 2);

// FIPS -> postal code. 50 states + DC; territories are left out on purpose
// (see the note in the output file's "source").
const POSTAL = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
  "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
  "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
  "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
  "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
  "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
  "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
  "55": "WI", "56": "WY",
};

const f = 10 ** DECIMALS;
const round = (v) => Math.round(v * f) / f;

function cleanRing(ring, shiftEast) {
  const out = [];
  for (let [lng, lat] of ring) {
    // Alaska's Aleutians cross the antimeridian into positive longitudes.
    // Shifting them by -360 keeps the state one continuous shape, so its
    // bounds are the real state and not the whole globe.
    if (shiftEast && lng > 0) lng -= 360;
    const p = [round(lng), round(lat)];
    const last = out[out.length - 1];
    if (!last || last[0] !== p[0] || last[1] !== p[1]) out.push(p);
  }
  // A ring needs 4 positions (closed triangle). Islands smaller than the
  // rounding grid collapse; they are invisible at the zooms this layer shows.
  return out.length >= 4 ? out : null;
}

const all = feature(topo, topo.objects.states).features;
const kept = [];
let droppedRings = 0;
for (const feat of all) {
  const code = POSTAL[feat.id];
  if (!code) continue;
  const shift = code === "AK";
  const polys = feat.geometry.type === "Polygon" ? [feat.geometry.coordinates] : feat.geometry.coordinates;
  const cleaned = [];
  for (const poly of polys) {
    const rings = poly.map((r) => cleanRing(r, shift));
    if (!rings[0]) { droppedRings += poly.length; continue; }
    const holes = rings.slice(1).filter(Boolean);
    droppedRings += rings.length - 1 - holes.length;
    cleaned.push([rings[0], ...holes]);
  }
  kept.push({
    type: "Feature",
    id: code,
    properties: { code, name: feat.properties.name },
    geometry: cleaned.length === 1
      ? { type: "Polygon", coordinates: cleaned[0] }
      : { type: "MultiPolygon", coordinates: cleaned },
  });
}
kept.sort((a, b) => a.id.localeCompare(b.id));

const fc = {
  type: "FeatureCollection",
  source:
    "U.S. Census Bureau cartographic boundaries (public domain), via us-atlas 3.0.1 " +
    "states-10m. 50 states + DC; territories omitted. Coordinates rounded to " +
    `${DECIMALS} decimals; Alaska's Aleutians shifted west of -180 so it is one shape.`,
  features: kept,
};
fs.writeFileSync(OUT, JSON.stringify(fc));
const size = fs.statSync(OUT).size;
console.log(`${kept.length} features, ${droppedRings} sub-grid rings dropped, ${(size / 1024).toFixed(0)} KB`);
