"use client";

import { useState } from "react";

import { useLocale, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import { ApiError, geocodePlace, searchLakes } from "@/lib/api/client";
import type { LakeMatch } from "@/lib/api/types";
import { kmApart } from "@/lib/geo";
import { useJurisdictions } from "@/lib/jurisdiction";

// A search for water, which FishEye may have by name ("Freeman Lake"). A
// town or a ZIP goes straight to the place geocoder.
const WATER = /\b(lake|lakes|pond|reservoir|res|creek|river|lagoon|bayou|slough|tank)\b/i;

// The lake names are OpenStreetMap's, in English: "Lago Lanier" is searched
// as "Lake Lanier", "Río Grande" as "River Grande" (the search matches each
// word anywhere in the name, so the order doesn't matter).
const SPANISH_WATER: [RegExp, string][] = [
  [/\b(lago|laguna)\b/gi, "lake"],
  [/\b(r[ií]o)\b/gi, "river"],
  [/\b(arroyo)\b/gi, "creek"],
  [/\b(estanque)\b/gi, "pond"],
  [/\b(presa|embalse|represa)\b/gi, "reservoir"],
];

export function inEnglish(query: string): string {
  return SPANISH_WATER.reduce((q, [re, word]) => q.replace(re, word), query);
}

const words = (text: string) => (text.toLowerCase().match(/[a-z0-9']+/g) ?? []).sort().join(" ");

/** "Freeman Lake, GA" → the name and the state: a state's name at the end,
 * or its two-letter code after a comma or in capitals. */
export function splitState(query: string, states: { code: string; name: string }[]): { name: string; state: string | null } {
  const text = query.trim();
  // Longest first: "…, West Virginia" is not "…, West" in Virginia.
  for (const s of [...states].sort((a, b) => b.name.length - a.name.length)) {
    const byName = text.match(new RegExp(`^(.*\\S)[,\\s]+${s.name.replace(/\s+/g, "\\s+")}$`, "i"));
    const byCode = text.match(new RegExp(`^(.*\\S)(?:,\\s*${s.code}|\\s+${s.code})$`, "i"));
    const m = byName ?? (byCode && (text.includes(",") || text.endsWith(s.code)) ? byCode : null);
    if (m) return { name: m[1].replace(/,$/, "").trim(), state: s.code };
  }
  return { name: text, state: null };
}

// A lake this close to where the map is looking is the one meant, even if
// the state has others of that name.
const NEAR_KM = 30;

/** The lake a search clearly meant: the only one of that name in the state
 * being looked at (or anywhere, when no state is), or the only one of them
 * near where the map is. Otherwise the person picks. */
export function clearPick(
  found: LakeMatch[],
  name: string,
  state: string | null,
  near: { latitude: number; longitude: number } | null = null,
): LakeMatch | null {
  const same = found.filter((m) => words(m.name) === words(name));
  const here = state ? same.filter((m) => m.state_code === state) : same;
  if (here.length === 1) return here[0];
  const close = near ? here.filter((m) => kmApart(near, m) <= NEAR_KM) : [];
  return close.length === 1 ? close[0] : null;
}

export interface LocatedPoint {
  latitude: number;
  longitude: number;
  label: string;
  // Set only for "use my location": the browser's estimate of how far off
  // the point may be, in metres. The map zooms to street level and marks it.
  own?: { accuracy: number };
  // How close to fly in, when not the usual town scale (a lake found by name
  // while placing a catch: close enough to tap its shore).
  zoom?: number;
}

/**
 * The address search box + "use my location" button, styled like a
 * familiar map app's search bar. Both paths end the same way — calling
 * onLocate with a point — so the map only has to know how to react to
 * "the user is now interested in this point", not which path got there.
 *
 * Neither path talks to a third-party geocoder directly: text search goes
 * through this app's own /api/geocode (see backend/app/services/geocoding.py
 * for why — Nominatim's usage policy doesn't allow many independent
 * browsers hitting its public endpoint), and "use my location" is the
 * browser's own Geolocation API, which needs no geocoding at all.
 */
export function LocationSearchBar({
  onLocate,
  onLake,
  stateCode = null,
  near = null,
}: {
  onLocate: (point: LocatedPoint) => void;
  // A lake FishEye has, found by name: opened rather than flown near.
  onLake?: (lake: LakeMatch) => void;
  // The state being looked at: its lakes win a name several states share.
  stateCode?: string | null;
  // Where the map is looking: of lakes sharing a name, the nearest leads.
  near?: { latitude: number; longitude: number } | null;
}) {
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Lakes of that name in several places: the person says which.
  const [choices, setChoices] = useState<LakeMatch[] | null>(null);
  const states = useJurisdictions();
  const all = useT();
  const t = all.search;
  const useTLabel = { current: all.map.yourLocation };
  const locale = useLocale();

  function pickLake(lake: LakeMatch) {
    setChoices(null);
    onLake?.(lake);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const typed = query.trim();
    if (typed.length < 2) return;
    const trimmed = inEnglish(typed);

    setSearching(true);
    setError(null);
    setChoices(null);
    if (onLake && WATER.test(trimmed)) {
      const { name, state } = splitState(trimmed, states ?? []);
      const found = await searchLakes(name, state ?? stateCode, near).catch(() => [] as LakeMatch[]);
      const pick = clearPick(found, name, state ?? stateCode, near);
      if (pick || found.length > 0) {
        setSearching(false);
        if (pick) pickLake(pick);
        else setChoices(found);
        return;
      }
    }
    searchPlaces(typed);
  }

  function searchPlaces(trimmed: string) {
    setChoices(null);
    setSearching(true);
    geocodePlace(trimmed)
      .then((result) => {
        onLocate({
          latitude: result.latitude,
          longitude: result.longitude,
          label: result.display_name,
        });
      })
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 404) {
          setError(t.notFound(trimmed));
        } else if (e instanceof ApiError && e.code === "rate_limited") {
          setError(e.message);
        } else {
          setError(t.unavailable);
        }
      })
      .finally(() => setSearching(false));
  }

  function handleUseMyLocation() {
    if (!("geolocation" in navigator)) {
      setError(t.noGeolocation);
      return;
    }
    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        onLocate({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          label: useTLabel.current,
          own: { accuracy: position.coords.accuracy },
        });
      },
      (geoError) => {
        setLocating(false);
        // PERMISSION_DENIED (1) is the common case — the person said no
        // to the browser's own permission prompt, not a bug here.
        setError(
          geoError.code === geoError.PERMISSION_DENIED
            ? t.denied
            : t.noFix,
        );
      },
      { enableHighAccuracy: false, timeout: 10_000 },
    );
  }

  return (
    <div className="location-search-bar">
      <form onSubmit={handleSubmit} className="location-search-form">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t.placeholder}
          autoComplete="off"
          enterKeyHint="search"
          className="location-search-input"
          aria-label={t.label}
        />
        <button type="submit" className="location-search-button" disabled={searching}>
          {searching ? t.searching : t.search}
        </button>
      </form>
      <button
        type="button"
        className="locate-me-button"
        onClick={handleUseMyLocation}
        disabled={locating}
        title={t.useLocationTitle}
      >
        {locating ? t.locating : t.useLocation}
      </button>
      {error && <div className="location-search-error">{error}</div>}
      {choices && (
        <div className="location-search-choices">
          <ul aria-label={t.lakesNamed}>
            {choices.map((lake) => (
              <li key={lake.id}>
                <button type="button" onClick={() => pickLake(lake)}>
                  {lake.name}{" "}
                  <span>
                    {lake.county ? `${lake.county}, ` : ""}
                    {localStateName(lake.state_code, lake.state_name ?? "", locale)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="link-btn" onClick={() => searchPlaces(query.trim())}>
            {t.placesInstead}
          </button>
        </div>
      )}
    </div>
  );
}
