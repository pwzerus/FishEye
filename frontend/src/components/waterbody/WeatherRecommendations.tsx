"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, getWeather, postRecommendations } from "@/lib/api/client";
import type { FishingPlan, PlanPick, PlanWindow, RecommendationResponse, Weather } from "@/lib/api/types";

function WeatherAlertBanner({ warnings }: { warnings: RecommendationResponse["safety_warnings"] }) {
  if (warnings.length === 0) return null;
  // Deliberately rendered first and styled to demand
  // attention: PRD §17 requires severe-weather warnings to take priority
  // over everything else on the panel, not sit as a footnote under it.
  return (
    <div className="weather-alert-banner">
      {warnings.map((w, i) => (
        <p key={i}>
          <strong>{w.event}</strong>
          {w.headline ? ` — ${w.headline}` : ""}
        </p>
      ))}
    </div>
  );
}

function CurrentWeather({ weather }: { weather: Weather }) {
  if (weather.source === "fallback") {
    // Never present fallback placeholders (null temperature, empty hourly)
    // as real readings — say plainly that the service is unavailable.
    return (
      <div className="weather-summary weather-unavailable">
        Weather data is temporarily unavailable, so no readings are shown rather than
        guessing.
      </div>
    );
  }

  const { current } = weather;
  return (
    <div className="weather-summary">
      <div className="weather-now">
        <span className="weather-temp">
          {current.temperature !== null ? `${Math.round(current.temperature)}°${current.temperature_unit}` : "—"}
        </span>
        <span className="weather-forecast">{current.short_forecast}</span>
      </div>
      <div className="weather-wind">
        Wind {current.wind_speed ?? "unknown"}
        {current.wind_direction ? ` from the ${current.wind_direction}` : ""}
      </div>
    </div>
  );
}

/**
 * Clock time read straight off the ISO string, which carries the lake's own
 * UTC offset. Formatting through `Date` would convert to the viewer's zone:
 * someone in Michigan planning a Texas trip would see the dawn bite an hour
 * late.
 */
export function lakeClock(iso: string): string {
  const m = /T(\d{2}):(\d{2})/.exec(iso);
  if (!m) return iso;
  const h = Number(m[1]);
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}${m[2] === "00" ? "" : `:${m[2]}`} ${h < 12 ? "AM" : "PM"}`;
}

/** "Today" / "Tomorrow" / weekday, judged in lake time too. */
export function lakeDay(iso: string, now: Date = new Date()): string {
  const off = /([+-])(\d{2}):(\d{2})$/.exec(iso);
  const offsetMin = off ? (off[1] === "-" ? -1 : 1) * (Number(off[2]) * 60 + Number(off[3])) : 0;
  const lakeToday = new Date(now.getTime() + offsetMin * 60_000).toISOString().slice(0, 10);
  const date = iso.slice(0, 10);
  if (date === lakeToday) return "Today";
  const tomorrow = new Date(Date.parse(`${lakeToday}T00:00:00Z`) + 86_400_000).toISOString().slice(0, 10);
  if (date === tomorrow) return "Tomorrow";
  return new Date(`${date}T12:00:00Z`).toLocaleDateString(undefined, { weekday: "long", timeZone: "UTC" });
}

/** "6–9 PM", or "11 AM–2 PM" when the window crosses noon. */
export function lakeRange(startIso: string, endIso: string): string {
  const start = lakeClock(startIso);
  const end = lakeClock(endIso);
  const [startTime, startHalf] = start.split(" ");
  return startHalf === end.split(" ")[1] ? `${startTime}–${end}` : `${start}–${end}`;
}

function windowText(w: PlanWindow): string {
  const bite = w.label === "morning" ? "Morning bite" : w.label === "evening" ? "Evening bite" : "Best window";
  return `${bite}, ${lakeRange(w.start_time, w.end_time)} ${lakeDay(w.start_time).toLowerCase()}`;
}

function shortWindowText(w: PlanWindow): string {
  return `${lakeRange(w.start_time, w.end_time)} ${lakeDay(w.start_time).toLowerCase()}`;
}

function Picks({ picks }: { picks: PlanPick[] }) {
  return (
    <ul className="plan-picks">
      {picks.map((p) => (
        <li key={p.name}>
          <strong>{p.name}</strong>
          <span className="plan-why">{p.why}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * Today's plan for one lake: where, when, and what to fish with. Every line
 * is something an angler can act on; the reasons are in plain words, and
 * nothing is scored. The plan is for the whole lake: it never ranks access
 * points or community pins.
 */
export function PlanCard({
  plan,
  onSpeciesChange,
}: {
  plan: FishingPlan;
  onSpeciesChange: (species: string) => void;
}) {
  return (
    <section className="plan-card" aria-label="Today's plan">
      <label className="plan-fish">
        <span>Fishing for</span>
        <select value={plan.species ?? ""} onChange={(e) => onSpeciesChange(e.target.value)}>
          {plan.species === null && <option value="">Pick a fish</option>}
          {plan.species_options.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      {plan.species && plan.species_on_record === false && (
        <p className="plan-note">Not on record in this lake, so this is general advice for the fish.</p>
      )}

      {plan.heads_up.length > 0 && (
        <ul className="plan-heads-up">
          {plan.heads_up.map((h) => (
            <li key={h}>{h}</li>
          ))}
        </ul>
      )}

      <dl className="plan-rows">
        {plan.where && (
          <div>
            <dt>Where</dt>
            <dd>{plan.where.text}</dd>
          </div>
        )}
        {plan.when && (
          <div>
            <dt>When</dt>
            <dd>
              {windowText(plan.when)}
              {plan.also && <span className="plan-also"> · or {shortWindowText(plan.also)}</span>}
              {plan.conditions && <span className="plan-conditions">{plan.conditions}</span>}
            </dd>
          </div>
        )}
        {!plan.where && !plan.when && (
          <div>
            <dt>When</dt>
            <dd className="muted">No live forecast right now, so no bank or time to suggest.</dd>
          </div>
        )}
        {plan.species ? (
          <>
            <div>
              <dt>Lures</dt>
              <dd>{plan.lures.length > 0 ? <Picks picks={plan.lures} /> : plan.lure_note}</dd>
            </div>
            {plan.baits.length > 0 && (
              <div>
                <dt>Bait</dt>
                <dd>
                  <Picks picks={plan.baits} />
                </dd>
              </div>
            )}
            {plan.species_slug && (
              <div>
                <dt>Guide</dt>
                <dd>
                  <Link href={`/fish/${plan.species_slug}`} className="plan-guide-link">
                    How to rig and fish for {plan.species}, with photos <span aria-hidden="true">→</span>
                  </Link>
                </dd>
              </div>
            )}
          </>
        ) : (
          <div>
            <dt>Tackle</dt>
            <dd className="muted">Pick a fish to see lures and bait for today.</dd>
          </div>
        )}
      </dl>
    </section>
  );
}

/**
 * Today's plan, severe-weather warnings and the weather right now for a
 * lake. Deliberately no ranked list of spots: the access points are listed
 * (and confirmed or not) by the lake panel, and a ranking would read as the
 * app's own pick among them — including, one day, among community pins that
 * anglers placed themselves.
 */
export function WeatherRecommendations({
  waterbodyId,
  latitude,
  longitude,
}: {
  waterbodyId: number;
  latitude: number;
  longitude: number;
}) {
  const [weather, setWeather] = useState<Weather | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // "" = let the backend pick this lake's main fish.
  const [species, setSpecies] = useState("");
  // The request a completed fetch answered. Deriving `loading` from this
  // (rather than resetting state at the top of the effect) is what keeps
  // react-hooks/set-state-in-effect quiet — only the async callbacks below
  // ever call setState, same fix as WaterbodyPanel's own loading flag.
  const requestKey = `${waterbodyId}:${latitude}:${longitude}:${species}`;
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const loading = loadedKey !== requestKey;

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      getWeather(latitude, longitude),
      postRecommendations({ waterbody_id: waterbodyId, target_species: species || undefined }),
    ])
      .then(([w, r]) => {
        if (cancelled) return;
        setWeather(w);
        setRecommendations(r);
        setError(null);
        setLoadedKey(requestKey);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : "Could not load today's plan.");
        setLoadedKey(requestKey);
      });

    return () => {
      cancelled = true;
    };
  }, [waterbodyId, latitude, longitude, species, requestKey]);

  return (
    <div className="weather-recommendations">
      <h3>Today&apos;s plan</h3>

      {error && !loading && <div className="panel-error">{error}</div>}
      {loading && !recommendations && <div className="muted">Loading today&apos;s plan…</div>}

      {recommendations && <WeatherAlertBanner warnings={recommendations.safety_warnings} />}
      {recommendations?.plan && <PlanCard plan={recommendations.plan} onSpeciesChange={setSpecies} />}
      {weather && (
        <>
          <div className="plan-now-label">Right now</div>
          <CurrentWeather weather={weather} />
        </>
      )}
    </div>
  );
}
