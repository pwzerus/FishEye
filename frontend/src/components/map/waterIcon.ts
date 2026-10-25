import L from "leaflet";

export function waterIcon(kind: "verified" | "reported" | "osm" | "access" = "verified") {
  return L.divIcon({
    className: `field-map-pin is-${kind}`,
    html: `<span><span>${kind === "access" ? "↗" : "≈"}</span></span>`,
    iconSize: [28, 32], iconAnchor: [14, 30], popupAnchor: [0, -30],
  });
}
