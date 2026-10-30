"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Marker, Popup, Tooltip, useMapEvents } from "react-leaflet";
import L, { type Marker as LeafletMarker } from "leaflet";

import { checkedGroup, formatDay, placeText, speciesCheckShort } from "@/components/community/PinCard";
import { useLocale, useLocaleTag, useT } from "@/i18n/client";
import { fishSlug, localFishName } from "@/i18n/names";
import { listPins, type PinScope } from "@/lib/api/session";
import type { PinSummary, WaterGroup } from "@/lib/api/types";
import { catchIcon } from "./catchIcon";
import { MIN_PLACE_ZOOM } from "./zoomPolicy";

// Keeps a popup clear of what floats over the map's top (the search bar and
// the buttons) when Leaflet pans to show it.
const POPUP_PAD = { autoPanPaddingTopLeft: [12, 150] as [number, number], autoPanPaddingBottomRight: [12, 40] as [number, number] };

/** A catch's fish in the chosen language: its guide name when it has one. */
function useFishLabel() {
  const locale = useLocale();
  return (slug: string | null | undefined, label: string | null | undefined): string | null =>
    (slug ? localFishName(slug, locale) : label ? localFishName(fishSlug(label), locale) : null) ?? label ?? null;
}

/** Catches drawn one by one: your own, at their real spots, with a small
 * preview popup. Everyone else's are WaterGroupMarkers. */
export function PinMarkers({ pins }: { pins: PinSummary[] }) {
  const t = useT();
  const locale = useLocale();
  const tag = useLocaleTag();
  const fish = useFishLabel();
  return (
    <>
      {pins.map((p) => (
        <Marker
          key={p.id}
          position={[p.latitude, p.longitude]}
          icon={catchIcon({ private: p.visibility === "private", mine: p.is_mine, approx: p.location_shown !== "exact" })}
          // The marker's name for a screen reader (a div icon has no alt).
          title={t.catch.by(p.title, p.is_mine ? t.common.you : p.author.display_name)}
          zIndexOffset={500}
        >
          <Popup className="catch-popup" {...POPUP_PAD}>
            <div className="catch-pop">
              {p.thumb_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={p.thumb_url} alt="" />
              )}
              <strong>{p.title}</strong>
              <span>
                {fish(p.species_slug, p.species_label) ?? t.catch.catch}
                {p.species_check && (
                  <span className="catch-pop-check" title={speciesCheckShort(t, p, locale)}>
                    {" "}✓ {p.species_check === "confirmed" ? t.catch.photoCheckedShort : t.catch.photoShowsShort(checkedGroup(t, p, locale))}
                  </span>
                )}
                {" · "}
                {p.is_mine ? t.common.you : p.author.display_name}
                {p.visibility === "private" ? ` · ${t.catch.onlyYouShort}` : ""}
              </span>
              <span className="muted">
                {p.water ? p.water.name : placeText(t, p, p.location_shown)}
                {" · "}
                {formatDay(p.caught_on ?? p.created_at, tag)}
              </span>
              <Link href={`/community/${p.id}`}>{t.catch.open}</Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

function groupIcon(count: number, label: string) {
  const size = count < 10 ? "s" : count < 100 ? "m" : "l";
  return L.divIcon({
    className: "water-group-wrap",
    html:
      `<span class="water-group is-${size}"><svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">` +
      `<path d="M3 12c3-5 9-6 13-3l5-3v12l-5-3c-4 3-10 2-13-3z" fill="currentColor"/></svg>` +
      `<b>${count}</b><span class="sr-only"> ${label}</span></span>`,
    iconSize: [52, 30],
    iconAnchor: [26, 15],
    popupAnchor: [0, -14],
  });
}

/** Where a group's catches are listed: its lake, its river in its county,
 * or (old catches on no water) the few metres around its point. */
function groupScope(g: WaterGroup): PinScope & { bbox?: string } {
  if (g.kind === "lake" && g.id !== null) return { lake: String(g.id) };
  if (g.kind === "river" && g.id !== null) return { river: String(g.id), county: g.county_geoid ?? undefined };
  const d = 0.0005;
  return { bbox: `${g.longitude - d},${g.latitude - d},${g.longitude + d},${g.latitude + d}` };
}

/** The catches page, at this water. */
export function groupHref(g: WaterGroup): string | null {
  if (!g.state_code || !g.county_geoid) return null;
  const q = new URLSearchParams({ state: g.state_code, county: g.county_geoid });
  if (g.id !== null && g.kind !== "place") q.set("lake", g.kind === "river" ? `r${g.id}` : String(g.id));
  return `/community?${q}`;
}

function WaterGroupMarker({ group }: { group: WaterGroup }) {
  const t = useT();
  const tag = useLocaleTag();
  const fish = useFishLabel();
  const [pins, setPins] = useState<PinSummary[] | null>(null);
  const icon = useMemo(() => groupIcon(group.count, t.catch.count(group.count)), [group.count, t]);
  const name = group.name ?? t.catch.groupNoWater;
  const href = groupHref(group);

  function load() {
    if (pins !== null) return;
    listPins({ ...groupScope(group), limit: 5 })
      .then(setPins)
      .catch(() => setPins([]));
  }

  return (
    <Marker
      position={[group.latitude, group.longitude]}
      icon={icon}
      title={`${name}: ${t.catch.count(group.count)}`}
      zIndexOffset={400}
      eventHandlers={{ popupopen: load }}
    >
      <Popup className="catch-popup" {...POPUP_PAD}>
        <div className="group-pop">
          <strong>{name}</strong>
          {group.kind === "river" && group.county_name && <span className="muted">{group.county_name}</span>}
          <span>
            {t.catch.groupTitle(group.count)} · {t.catch.groupLatest(formatDay(group.latest_at, tag) ?? "")}
          </span>
          {group.species.length > 0 && (
            <span className="group-pop-species">{group.species.map((s) => fish(null, s)).join(" · ")}</span>
          )}
          {pins === null ? (
            <span className="muted">{t.catch.groupLoading}</span>
          ) : (
            <ul className="group-pop-list">
              {pins.map((p) => (
                <li key={p.id}>
                  <Link href={`/community/${p.id}`}>
                    {p.thumb_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={p.thumb_url} alt="" />
                    ) : (
                      <span className="group-pop-noimg" aria-hidden="true" />
                    )}
                    <span>
                      <b>{fish(p.species_slug, p.species_label) ?? p.title}</b>
                      <small>
                        {p.is_mine ? t.common.you : p.author.display_name} · {formatDay(p.caught_on ?? p.created_at, tag)}
                      </small>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {href && group.count > 5 && <Link href={href}>{t.catch.seeAll}</Link>}
        </div>
      </Popup>
    </Marker>
  );
}

/** Other people's catches, one bubble per water with how many (backend ADR
 * 0040): "12 at Lake Lanier", never where on it. */
export function WaterGroupMarkers({ groups }: { groups: WaterGroup[] }) {
  return (
    <>
      {groups.map((g) => (
        <WaterGroupMarker key={`${g.kind}-${g.id}-${g.county_geoid}-${g.latitude}-${g.longitude}`} group={g} />
      ))}
    </>
  );
}

/** Tap where you fished. From further out than MIN_PLACE_ZOOM a tap zooms in
 * toward that spot instead of dropping the pin there. */
export function PlaceOnClick({ onPlace }: { onPlace: (lat: number, lng: number) => void }) {
  const map = useMapEvents({
    click: (e) => {
      if (map.getZoom() < MIN_PLACE_ZOOM) {
        map.flyTo(e.latlng, Math.min(MIN_PLACE_ZOOM, map.getZoom() + 5));
        return;
      }
      onPlace(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

/** The pin being placed: draggable, so it can be nudged onto the water, and
 * labelled with the water it is on (or that it is on none). */
export function DraftMarker({
  point,
  onMove,
  label,
  off = false,
}: {
  point: { latitude: number; longitude: number };
  onMove: (lat: number, lng: number) => void;
  label?: string | null;
  off?: boolean;
}) {
  const ref = useRef<LeafletMarker>(null);
  useEffect(() => {
    ref.current?.getElement()?.classList.add("draft-drop");
  }, []);
  return (
    <Marker
      ref={ref}
      position={[point.latitude, point.longitude]}
      icon={catchIcon({ draft: true })}
      draggable
      zIndexOffset={1000}
      eventHandlers={{
        dragend: () => {
          const ll = ref.current?.getLatLng();
          if (ll) onMove(ll.lat, ll.lng);
        },
      }}
    >
      {label && (
        <Tooltip permanent direction="top" offset={[0, -38]} className={off ? "draft-water is-off" : "draft-water"}>
          {label}
        </Tooltip>
      )}
    </Marker>
  );
}
