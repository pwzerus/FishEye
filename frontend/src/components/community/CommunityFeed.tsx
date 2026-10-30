"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useLocale, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import { getPinOptions, listPinPlaces, listPins, pinWhere, type PinScope } from "@/lib/api/session";
import type { PinOptions, PinPlaces, PinSummary } from "@/lib/api/types";
import { readState } from "@/lib/jurisdiction";
import { PinCard } from "./PinCard";
import { SpeciesOptions } from "./PinForm";
import { PlaceBrowser, readScope, rememberScope, scopeFromUrl, scopeTitle, scopeToSearch } from "./PlaceBrowser";

function locate(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) reject(new Error("unsupported"));
    else navigator.geolocation.getCurrentPosition(resolve, reject, { maximumAge: 10 * 60 * 1000, timeout: 15000 });
  });
}

/** Catches are browsed by place: a state, a county in it, a lake in that.
 * "Near me" opens the county you are in. Nothing is one nationwide pile. */
export function CommunityFeed() {
  const { user, loading: authLoading } = useAuth();
  const all = useT();
  const t = all.feed;
  const tc = all.catch;
  const locale = useLocale();
  // The catches for `feedKey`; anything else is still loading.
  const [feed, setFeed] = useState<{ key: string; pins: PinSummary[] } | null>(null);
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [species, setSpecies] = useState("");
  const [mine, setMine] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // null until the starting place is decided, so the page doesn't flash
  // "all states" before opening the angler's county.
  const [scope, setScopeState] = useState<PinScope | null>(null);
  const [places, setPlaces] = useState<PinPlaces | null>(null);
  const [locating, setLocating] = useState(false);
  const [locateError, setLocateError] = useState<string | null>(null);
  const feedKey = `${species}:${mine}:${user?.id ?? 'guest'}:${scopeToSearch(scope ?? {})}`;
  const [page, setPage] = useState({ key: '', count: 12 });
  const visibleCount = page.key === feedKey ? page.count : 12;

  const setScope = useCallback((next: PinScope) => {
    setScopeState(next);
    rememberScope(next);
    const url = `${window.location.pathname}${scopeToSearch(next)}`;
    if (url !== `${window.location.pathname}${window.location.search}`) window.history.pushState(null, "", url);
  }, []);

  const nearMe = useCallback(
    async (quiet = false) => {
      setLocating(true);
      setLocateError(null);
      try {
        const pos = await locate();
        const where = await pinWhere(pos.coords.latitude, pos.coords.longitude);
        if (where.state_code && where.county_geoid) {
          setScope({ state: where.state_code, county: where.county_geoid });
          return true;
        }
        if (!quiet) setLocateError(t.outsideUs);
      } catch {
        if (!quiet) setLocateError(t.locateFailed);
      } finally {
        setLocating(false);
      }
      return false;
    },
    [setScope, t.outsideUs, t.locateFailed],
  );

  // Where to start: the link's place, then the last place browsed, then the
  // state chosen on the map. With location already allowed, the county you
  // are in (never asks: a prompt on page load is the "Near me" button's job).
  useEffect(() => {
    // After mount (the server has no URL or storage to read), then once.
    void Promise.resolve().then(() => {
      const start = scopeFromUrl(window.location.search) ?? readScope();
      if (start) {
        setScopeState(start);
        return;
      }
      const state = readState();
      setScopeState(state ? { state } : {});
      navigator.permissions
        ?.query({ name: "geolocation" })
        .then((p) => p.state === "granted" && nearMe(true))
        .catch(() => undefined);
    });
  }, [nearMe]);

  useEffect(() => {
    const onPop = () => setScopeState(scopeFromUrl(window.location.search) ?? {});
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    getPinOptions().then(setOptions).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (authLoading || scope === null) return;
    let cancelled = false;
    listPinPlaces({ state: scope.state, county: scope.county, species: species || undefined, mine: mine && !!user })
      .then((p) => !cancelled && setPlaces(p))
      .catch(() => !cancelled && setPlaces(null));
    return () => {
      cancelled = true;
    };
  }, [scope, species, mine, user, authLoading]);

  // Everyone's catches always have a place; your own can be seen all at once.
  const pickFirst = scope !== null && !scope.state && !(mine && user);

  useEffect(() => {
    if (authLoading || scope === null || pickFirst) return;
    let cancelled = false;
    listPins({ ...scope, species: species || undefined, mine: mine && !!user, limit: 120 })
      .then((p) => {
        if (!cancelled) {
          setFeed({ key: feedKey, pins: p });
          setError(null);
        }
      })
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [scope, species, mine, user, authLoading, pickFirst, feedKey]);
  const pins = feed?.key === feedKey ? feed.pins : null;

  const names = {
    state: scope?.state && places?.state_name ? localStateName(scope.state, places.state_name, locale) : places?.state_name,
    county: places?.county_name,
    lake: scope?.lake ? places?.places.find((p) => p.id === scope.lake)?.name : null,
  };
  const where = scope ? scopeTitle(scope, names) : null;

  const addHref = user ? "/map?addPin=1" : `/login?next=${encodeURIComponent("/map?addPin=1")}`;

  return (
    <>
      <section className="page-intro community-intro">
        <div>
          <p className="eyebrow reveal" style={{ "--i": 0 } as React.CSSProperties}>
            {t.eyebrow}
          </p>
          <h1 className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
            {t.title}
          </h1>
          <p className="lede reveal" style={{ "--i": 2 } as React.CSSProperties}>
            {t.lede}
          </p>
        </div>
        <Link href={addHref} className="btn btn-primary reveal" style={{ "--i": 3 } as React.CSSProperties}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" />
          </svg>
          {tc.shareTitle}
        </Link>
      </section>

      <div className="fish-toolbar reveal" style={{ "--i": 4 } as React.CSSProperties}>
        <div className="segmented" role="tablist" aria-label={t.whose}>
          <button type="button" role="tab" aria-selected={!mine} className={!mine ? "segment active" : "segment"} onClick={() => setMine(false)}>
            {t.everyone}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mine}
            disabled={!user}
            title={user ? undefined : t.signInMine}
            className={mine ? "segment active" : "segment"}
            onClick={() => setMine(true)}
          >
            {t.mine}
          </button>
        </div>
        <label className="select-field">
          <span className="sr-only">{tc.fish}</span>
          <select value={species} onChange={(e) => setSpecies(e.target.value)}>
            <SpeciesOptions options={options} otherValue="" allLabel={t.allFish} />
          </select>
        </label>
      </div>

      {scope && (
        <PlaceBrowser
          scope={scope}
          names={names}
          places={places}
          onChange={setScope}
          onNearMe={() => nearMe()}
          locating={locating}
          locateError={locateError}
        />
      )}

      {where && !pickFirst && <h2 className="feed-heading">{t.catchesIn(where)}</h2>}

      {pickFirst ? null : error ? (
        <div className="backend-error">{error}</div>
      ) : pins === null ? (
        <ul className="pin-grid" aria-busy="true">
          {Array.from({ length: 6 }, (_, i) => (
            <li key={i} className="pin-card sk-card">
              <div className="sk" style={{ aspectRatio: "4 / 3", borderRadius: 0 }} />
              <div className="pin-card-body">
                <div className="sk sk-line" />
                <div className="sk sk-line short" />
              </div>
            </li>
          ))}
        </ul>
      ) : pins.length === 0 ? (
        <div className="empty-state reveal">
          <h2>{mine ? t.noneMine(where) : t.none(where)}</h2>
          <p className="muted">{t.beFirst}</p>
          <div className="empty-actions">
            <Link href={addHref} className="btn btn-primary btn-sm">
              {tc.shareTitle}
            </Link>
            {scope?.county && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setScope({ state: scope.state })}>
                {t.seeAllOf(names.state ?? scope.state ?? "")}
              </button>
            )}
          </div>
        </div>
      ) : (
        <><ul className="pin-grid" key={feedKey}>
          {pins.slice(0, visibleCount).map((p, i) => (
            <li key={p.id}>
              <PinCard pin={p} index={i} />
            </li>
          ))}
        </ul>{pins.length > visibleCount && <button type="button" className="btn btn-ghost feed-more" onClick={() => setPage({ key: feedKey, count: visibleCount + 12 })}>{t.showMore}</button>}</>
      )}

      <details className="rules-card community-rules">
        <summary>{t.guidelines}</summary>
        <ul>
          <li>{t.guide1}</li>
          <li>{t.guide2}</li>
          <li>{t.guide3}</li>
          <li>{t.guide4}</li>
        </ul>
      </details>
    </>
  );
}
