import L from "leaflet";

/**
 * The community-pin marker: a round badge with a fish, distinct from the
 * lake pins' teardrop shape so a report never reads as survey data.
 * Private pins get a dashed ring, your own pins a teal ring, and the pin
 * being placed pulses.
 */
export const catchIcon = (opts: { private?: boolean; draft?: boolean; mine?: boolean } = {}) =>
  L.divIcon({
    className: "catch-marker-wrap",
    html: `<span class="catch-marker${opts.private ? " is-private" : ""}${opts.draft ? " is-draft" : ""}${opts.mine ? " is-mine" : ""}"><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M3 12c3-5 9-6 13-3l5-3v12l-5-3c-4 3-10 2-13-3z" fill="currentColor"/></svg></span>`,
    iconSize: [34, 42],
    iconAnchor: [17, 40],
    popupAnchor: [0, -36],
  });
