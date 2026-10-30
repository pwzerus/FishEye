"use client";

import { useLocale, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import type { PinScope } from "@/lib/api/session";
import type { PinPlaces } from "@/lib/api/types";

/** Where catches are browsed, as names for the breadcrumb. */
export interface ScopeNames {
  state?: string | null;
  county?: string | null;
  lake?: string | null;
}

const SCOPE_KEY = "fisheye.catchScope";

export function scopeFromUrl(search: string): PinScope | null {
  const q = new URLSearchParams(search);
  const state = q.get("state")?.toUpperCase();
  const county = q.get("county") ?? undefined;
  const lake = q.get("lake") ?? undefined;
  if (!state || !/^[A-Z]{2}$/.test(state)) return null;
  if (county && !/^\d{5}$/.test(county)) return { state };
  // A lake's id, or a river's as "r<id>" (backend /api/pins/places).
  return { state, county, lake: county && lake && /^r?\d+$/.test(lake) ? lake : undefined };
}

export function scopeToSearch(scope: PinScope): string {
  const q = new URLSearchParams();
  if (scope.state) q.set("state", scope.state);
  if (scope.county) q.set("county", scope.county);
  if (scope.lake) q.set("lake", scope.lake);
  const s = q.toString();
  return s ? `?${s}` : "";
}

export function readScope(): PinScope | null {
  try {
    return scopeFromUrl(window.localStorage.getItem(SCOPE_KEY) ?? "");
  } catch {
    return null;
  }
}

export function rememberScope(scope: PinScope): void {
  try {
    window.localStorage.setItem(SCOPE_KEY, scopeToSearch(scope));
  } catch {
    /* only remembered for this page */
  }
}

/** "Harris County, Texas", "Lake Fork", "Texas", or null for everywhere. */
export function scopeTitle(scope: PinScope, names: ScopeNames): string | null {
  if (scope.lake) return names.lake ?? null;
  if (scope.county) return names.county ? `${names.county}${names.state ? `, ${names.state}` : ""}` : null;
  if (scope.state) return names.state ?? scope.state;
  return null;
}


/** Breadcrumb (All states › Texas › Harris County › Lake) and the places one
 * level down, each with its number of catches. */
export function PlaceBrowser({
  scope,
  names,
  places,
  onChange,
  onNearMe,
  locating,
  locateError,
}: {
  scope: PinScope;
  names: ScopeNames;
  places: PinPlaces | null;
  onChange: (scope: PinScope) => void;
  onNearMe: () => void;
  locating: boolean;
  locateError: string | null;
}) {
  const all = useT();
  const t = all.feed;
  const locale = useLocale();
  const heading = {
    state: () => t.pickState,
    county: (n: ScopeNames) => t.countiesIn(n.state ?? null),
    lake: (n: ScopeNames) => t.watersIn(n.county ?? null),
  };
  const crumbs: { label: string; to: PinScope }[] = [{ label: t.allStates, to: {} }];
  if (scope.state) crumbs.push({ label: names.state ?? scope.state, to: { state: scope.state } });
  if (scope.county) crumbs.push({ label: names.county ?? t.county, to: { state: scope.state, county: scope.county } });
  if (scope.lake) crumbs.push({ label: names.lake ?? t.water, to: scope });

  const pick = (id: string): PinScope => {
    if (!places) return scope;
    if (places.level === "state") return { state: id };
    if (places.level === "county") return { state: scope.state, county: id };
    // A lake: choosing the one already open goes back to the whole county.
    return { state: scope.state, county: scope.county, lake: scope.lake === id ? undefined : id };
  };

  return (
    <section className="place-browser" aria-label={t.where}>
      <div className="place-browser-top">
        <nav aria-label={t.place} className="place-crumbs">
          <ol>
            {crumbs.map((c, i) => {
              const last = i === crumbs.length - 1;
              return (
                <li key={i}>
                  {last ? (
                    <span aria-current="page">{c.label}</span>
                  ) : (
                    <button type="button" className="text-link" onClick={() => onChange(c.to)}>
                      {c.label}
                    </button>
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
        <button type="button" className="btn btn-ghost btn-sm place-near-me" onClick={onNearMe} disabled={locating}>
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="3.5" />
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3" strokeLinecap="round" />
          </svg>
          {locating ? t.findingCounty : t.nearMe}
        </button>
      </div>
      {locateError && (
        <p className="place-locate-error muted" role="status">
          {locateError}
        </p>
      )}

      {places && (places.places.length > 0 || places.level === "state") && (
        <div className="place-level">
          <h2 className="place-level-heading">{heading[places.level](names)}</h2>
          {places.places.length === 0 ? (
            <p className="muted">{t.noneYet}</p>
          ) : (
            <ul className="place-chips">
              {places.places.map((p) => {
                const active = places.level === "lake" && scope.lake === p.id;
                return (
                  <li key={p.id}>
                    <button
                      type="button"
                      className={active ? "place-chip active" : "place-chip"}
                      aria-pressed={places.level === "lake" ? active : undefined}
                      onClick={() => onChange(pick(p.id))}
                    >
                      <span>
                        {places.level === "state"
                          ? localStateName(p.id, p.name, locale)
                          : p.id === "0" && places.level === "lake"
                            ? t.notOnWater
                            : p.name}
                      </span>
                      <span className="place-chip-count" aria-label={all.catch.count(p.count)}>
                        {p.count}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
