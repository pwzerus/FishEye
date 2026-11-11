"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type CSSProperties } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { FishArt } from "@/components/fish/FishArt";
import { Segmented } from "@/components/ui/Segmented";
import { useLocale, useT } from "@/i18n/client";
import { localSpecies, localStateName } from "@/i18n/names";
import { getPinOptions, listPinPlaces, listPins, pinWhere, type PinScope } from "@/lib/api/session";
import type { PinOptions, PinPlaces, PinSummary } from "@/lib/api/types";
import { readState } from "@/lib/jurisdiction";
import { Leaderboard } from "./Leaderboard";
import { PinCard } from "./PinCard";
import { SpeciesOptions } from "./PinForm";
import { PlaceBrowser, readScope, rememberScope, scopeFromUrl, scopeTitle, scopeToSearch } from "./PlaceBrowser";

function locate(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) reject(new Error("unsupported"));
    else navigator.geolocation.getCurrentPosition(resolve, reject, { maximumAge: 10 * 60 * 1000, timeout: 15000 });
  });
}

const ICON = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;

/** The three steps under the share button: sign in, the water, a photo. */
const STEP_ICONS = [
  <svg key="in" {...ICON}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21a8 8 0 0 1 16 0" />
  </svg>,
  <svg key="water" {...ICON}>
    <path d="M12 21s-6-5.3-6-10a6 6 0 0 1 12 0c0 4.7-6 10-6 10z" />
    <circle cx="12" cy="11" r="2.2" />
  </svg>,
  <svg key="photo" {...ICON}>
    <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
    <circle cx="12" cy="13" r="3.5" />
  </svg>,
];

const vars = (v: Record<string, string | number>) => v as CSSProperties;

/** Catches are browsed by place: a state, a county in it, a lake in that.
 * "Near me" opens the county you are in. Nothing is one nationwide pile. */
export function CommunityFeed() {
  const { user, loading: authLoading } = useAuth();
  const all = useT();
  const t = all.feed;
  const tc = all.catch;
  const ts = all.social;
  const locale = useLocale();
  // The catches for `feedKey`; anything else is still loading.
  const [feed, setFeed] = useState<{ key: string; pins: PinSummary[] } | null>(null);
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [species, setSpecies] = useState("");
  const [mine, setMine] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [placesError, setPlacesError] = useState<string | null>(null);
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
      .then((p) => {
        if (!cancelled) {
          setPlaces(p);
          setPlacesError(null);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) {
          setPlaces(null);
          setPlacesError(e.message);
        }
      });
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
  // The fish being filtered to, so "none here" says which fish.
  const fishName = species ? localSpecies(species, options?.species.find((s) => s.slug === species)?.label, locale) : null;

  const addHref = user ? "/map?addPin=1" : `/login?next=${encodeURIComponent("/map?addPin=1")}`;
  // Nothing shared anywhere yet: one invitation, no empty lists or boards.
  const nothingAnywhere = pickFirst && places !== null && places.places.length === 0;
  const nothingHere = !pickFirst && pins !== null && pins.length === 0;
  const showBoard = scope !== null && !nothingAnywhere && !nothingHere;

  const shareLink = (className: string, style?: CSSProperties) => (
    <Link href={addHref} className={className} style={style}>
      <svg {...ICON} strokeWidth={2.4}>
        <path d="M12 5v14M5 12h14" />
      </svg>
      <span>{tc.shareTitle}</span>
    </Link>
  );

  return (
    <div className="cf">
      <section className="cf-hero">
        <div className="cf-hero-text">
          <h1 className="cf-in" style={vars({ "--i": 0 })}>
            {t.title}
          </h1>
          <p className="cf-lede cf-in" style={vars({ "--i": 1 })}>
            {t.lede}
          </p>
        </div>
        <ol className="cf-steps" aria-label={ts.stepsTitle}>
          {[ts.step1, ts.step2, ts.step3].map((step, i) => (
            <li key={i} className="cf-step" style={vars({ "--i": i })}>
              <span className="cf-step-dot">
                {STEP_ICONS[i]}
                <span className="cf-step-n" aria-hidden="true">
                  {i + 1}
                </span>
              </span>
              <span className="cf-step-text">{step}</span>
            </li>
          ))}
        </ol>
        {shareLink("cf-share cf-in", vars({ "--i": 2 }))}
        <span className="cf-bubbles" aria-hidden="true">
          {Array.from({ length: 6 }, (_, i) => (
            <i key={i} />
          ))}
        </span>
        <span className="cf-wave" aria-hidden="true" />
      </section>

      <div className="cf-bar">
        <Segmented
          className="cf-whose"
          label={t.whose}
          value={mine ? "mine" : "all"}
          onChange={(v) => setMine(v === "mine")}
          options={[
            { value: "all", label: t.everyone },
            { value: "mine", label: t.mine, disabled: !user, title: user ? undefined : t.signInMine },
          ]}
        />
        <label className="cf-select">
          <span className="sr-only">{tc.fish}</span>
          <select value={species} onChange={(e) => setSpecies(e.target.value)}>
            <SpeciesOptions options={options} otherValue="" allLabel={t.allFish} />
          </select>
          <svg {...ICON}>
            <path d="m6 9 6 6 6-6" />
          </svg>
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

      <div className={pickFirst ? "feed-layout is-solo" : "feed-layout"}>
        <div className="feed-main">
          {where && !pickFirst && !nothingHere && <h2 className="feed-heading">{t.catchesIn(where)}</h2>}

          {pickFirst ? (
            placesError ? (
              <div className="backend-error">{placesError}</div>
            ) : (
              nothingAnywhere && (
                <div className="cf-empty">
                  <div className="cf-empty-art" aria-hidden="true">
                    <FishArt slug="largemouth-bass" uid="cf-empty" />
                  </div>
                  <h2>{fishName ? t.noneFish(fishName, null) : t.noneYet}</h2>
                  <p>{t.beFirst}</p>
                  <div className="cf-empty-actions">{shareLink("btn btn-primary")}</div>
                </div>
              )
            )
          ) : error ? (
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
            <div className="cf-empty">
              <div className="cf-empty-art" aria-hidden="true">
                <FishArt slug={species || "largemouth-bass"} uid="cf-empty" />
              </div>
              <h2>{mine ? t.noneMine(where) : fishName ? t.noneFish(fishName, where) : t.none(where)}</h2>
              <p>{t.beFirst}</p>
              <div className="cf-empty-actions">
                {shareLink("btn btn-primary")}
                {scope?.county && (
                  <button type="button" className="btn btn-ghost" onClick={() => setScope({ state: scope.state })}>
                    {t.seeAllOf(names.state ?? scope.state ?? "")}
                  </button>
                )}
              </div>
            </div>
          ) : (
            <>
              <ul className="pin-grid" key={feedKey}>
                {pins.slice(0, visibleCount).map((p, i) => (
                  <li key={p.id}>
                    <PinCard pin={p} index={i % 12} />
                  </li>
                ))}
              </ul>
              {pins.length > visibleCount && (
                <button type="button" className="btn btn-ghost feed-more" onClick={() => setPage({ key: feedKey, count: visibleCount + 12 })}>
                  {t.showMore}
                </button>
              )}
            </>
          )}
        </div>
        {showBoard && (
          <aside className="feed-side">
            <Leaderboard state={scope.state} county={scope.county} where={where} />
          </aside>
        )}
      </div>

      <details className="cf-rules">
        <summary>
          <svg {...ICON}>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 11v5M12 8h.01" />
          </svg>
          {t.guidelines}
        </summary>
        <ul>
          <li>{t.guideChecks}</li>
          <li>{t.guide1}</li>
          <li>{t.guide2}</li>
          <li>{t.guide3}</li>
          <li>{t.guideRespect}</li>
          <li>{t.guide4}</li>
        </ul>
      </details>
    </div>
  );
}
