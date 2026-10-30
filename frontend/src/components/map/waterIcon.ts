import L from "leaflet";

export function waterIcon(kind: "verified" | "reported" | "osm" | "access" = "verified") {
  return L.divIcon({
    className: `field-map-pin is-${kind}`,
    // The glyph is decoration: hidden, so a screen reader names the marker by
    // its title (set where the marker is made) rather than "≈".
    html: `<span aria-hidden="true"><span>${kind === "access" ? "↗" : "≈"}</span></span>`,
    iconSize: [28, 32], iconAnchor: [14, 30], popupAnchor: [0, -30],
  });
}
