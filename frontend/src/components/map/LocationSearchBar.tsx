"use client";

import { useEffect, useRef, useState } from "react";

import { useLocale, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import { ApiError, geocodePlace, searchLakes } from "@/lib/api/client";
import type { LakeMatch } from "@/lib/api/types";
import { kmApart } from "@/lib/geo";
import { useJurisdictions } from "@/lib/jurisdiction";
import { suggestPlaces } from "@/lib/usCities";

// A search for water, which FishEye may have by name ("Freeman Lake"). A
// town or a ZIP goes to the place geocoder, unless a lake FishEye verified
// has the very name typed (see handleSubmit).
const WATER = /\b(lake|lakes|pond|reservoir|res|creek|river|lagoon|bayou|slough|tank)\b/i;
const ZIP = /^\d{5}(-\d{4})?$/;

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

// A name without the word for the water: "lanier" is Lake Lanier's.
const GENERIC = new Set(["lake", "lakes", "reservoir", "pond", "the", "of"]);
const core = (text: string) =>
  (text.toLowerCase().match(/[a-z0-9']+/g) ?? []).filter((w) => !GENERIC.has(w)).sort().join(" ");

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
// A place this close to a lake of its name shows that lake once the map is
// there (Waco and Lake Waco), so the place search answers for both.
const PLACE_SHOWS_LAKE_KM = 40;

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

// What the box offers as you type: lakes come from FishEye's own search, a
// moment after the typing stops; places from a list in the page (lib/usCities).
const LAKE_HINTS = 4;
const LAKE_HINT_DELAY_MS = 250;
type Hint = { kind: "place"; label: string } | { kind: "lake"; lake: LakeMatch };

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
  const [places, setPlaces] = useState<string[]>([]);
  const [lakeHints, setLakeHints] = useState<LakeMatch[]>([]);
  const [activeHint, setActiveHint] = useState(-1);
  // Only the newest typing's lake answer is shown.
  const hintRun = useRef(0);
  const hintTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (hintTimer.current) clearTimeout(hintTimer.current);
    },
    [],
  );
  const states = useJurisdictions();
  const all = useT();
  const t = all.search;
  const useTLabel = { current: all.map.yourLocation };
  const locale = useLocale();

  function pickLake(lake: LakeMatch) {
    setChoices(null);
    closeHints();
    onLake?.(lake);
  }

  function closeHints() {
    hintRun.current += 1;
    if (hintTimer.current) clearTimeout(hintTimer.current);
    setPlaces([]);
    setLakeHints([]);
    setActiveHint(-1);
  }

  function changeQuery(value: string) {
    setQuery(value);
    setError(null);
    setChoices(null);
    setActiveHint(-1);
    const stateNames = (states ?? []).map((s) => s.name);
    // Typed in another language: its name for the state, offered in English for the geocoder.
    const typedLocal = value.trim();
    const localStates = /[^\x00-\x7f]/.test(typedLocal)
      ? (states ?? []).filter((s) => localStateName(s.code, s.name, locale).includes(typedLocal)).map((s) => s.name).slice(0, 2)
      : [];
    setPlaces([...new Set([...localStates, ...suggestPlaces(value, stateNames, 2), ...suggestPlaces(value)])]);
    const run = ++hintRun.current;
    if (hintTimer.current) clearTimeout(hintTimer.current);
    const typed = inEnglish(value.trim());
    if (!onLake || typed.length < 3) {
      setLakeHints([]);
      return;
    }
    hintTimer.current = setTimeout(() => {
      const { name, state } = splitState(typed, states ?? []);
      searchLakes(name, state ?? stateCode, near)
        .then((found) => {
          if (run === hintRun.current) setLakeHints(found.slice(0, LAKE_HINTS));
        })
        .catch(() => {
          if (run === hintRun.current) setLakeHints([]);
        });
    }, LAKE_HINT_DELAY_MS);
  }

  const hints: Hint[] = [
    ...places.map((label): Hint => ({ kind: "place", label })),
    ...lakeHints.map((lake): Hint => ({ kind: "lake", lake })),
  ];

  function takeHint(hint: Hint) {
    if (hint.kind === "lake") {
      setQuery(hint.lake.name);
      pickLake(hint.lake);
      return;
    }
    setQuery(hint.label);
    closeHints();
    setError(null);
    searchPlaces(hint.label);
  }

  function hintKeys(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      closeHints();
      return;
    }
    if (hints.length === 0) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActiveHint((i) => {
        const next = i + step;
        if (next >= hints.length) return -1;
        return next < -1 ? hints.length - 1 : next;
      });
    } else if (e.key === "Enter" && activeHint >= 0 && activeHint < hints.length) {
      e.preventDefault();
      takeHint(hints[activeHint]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const typed = query.trim();
    closeHints();
    // Nothing to look for, so the last search's lakes shouldn't stay up.
    if (typed.length < 2 || !/[\p{L}\p{N}]/u.test(typed)) {
      setChoices(null);
      return;
    }
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
    } else if (onLake && !ZIP.test(trimmed)) {
      // "lanier" means Lake Lanier, but the place search sent it to Lanier
      // County, 300 km away. A lake FishEye verified by that very name is
      // offered (the place a click away) when the place found is far from
      // it. "waco" still goes to Waco: Lake Waco is on the map right there.
      const { name, state } = splitState(trimmed, states ?? []);
      const placeRequest = geocodePlace(typed);
      const [found, place] = await Promise.all([
        searchLakes(name, state ?? stateCode, near).catch(() => [] as LakeMatch[]),
        placeRequest.catch(() => null),
      ]);
      const named = found.filter((m) => core(m.name) === core(name));
      const verified = named.filter((m) => m.data_tier === "verified");
      if (verified.length > 0 && !(place && verified.some((m) => kmApart(place, m) <= PLACE_SHOWS_LAKE_KM))) {
        setSearching(false);
        setChoices(named);
        return;
      }
      // The place search has already answered (or failed): no second request.
      searchPlaces(typed, placeRequest);
      return;
    }
    searchPlaces(typed);
  }

  function searchPlaces(trimmed: string, request = geocodePlace(trimmed)) {
    setChoices(null);
    setSearching(true);
    request
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
          onChange={(e) => changeQuery(e.target.value)}
          onKeyDown={hintKeys}
          onBlur={() => {
            // After a tap on a suggestion has landed.
            setTimeout(closeHints, 150);
          }}
          placeholder={t.placeholder}
          autoComplete="off"
          enterKeyHint="search"
          className="location-search-input"
          aria-label={t.label}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={hints.length > 0}
          aria-controls="location-hints"
          aria-activedescendant={activeHint >= 0 && activeHint < hints.length ? `location-hint-${activeHint}` : undefined}
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
      {hints.length > 0 && (
        <div className="location-search-choices location-search-hints">
          <ul id="location-hints" role="listbox" aria-label={t.suggestions}>
            {hints.map((hint, i) => (
              <li key={hint.kind === "lake" ? `lake-${hint.lake.id}` : hint.label} role="presentation">
                <button
                  type="button"
                  id={`location-hint-${i}`}
                  role="option"
                  aria-selected={i === activeHint}
                  className={i === activeHint ? "is-active" : undefined}
                  // Before the input's blur, so the tap isn't lost when the list closes.
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => takeHint(hint)}
                >
                  {hint.kind === "lake" ? (
                    <>
                      {hint.lake.name}{" "}
                      <span>
                        {hint.lake.county ? `${hint.lake.county}, ` : ""}
                        {localStateName(hint.lake.state_code, hint.lake.state_name ?? "", locale)}
                      </span>
                    </>
                  ) : (
                    hint.label
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
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
