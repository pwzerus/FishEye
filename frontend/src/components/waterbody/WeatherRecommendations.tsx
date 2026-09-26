"use client";

import { useEffect, useState } from "react";

import { ApiError, getWeather, postRecommendations } from "@/lib/api/client";
import type {
  RecommendationResponse,
  SpeciesSummary,
  SpotCandidate,
  TimeWindow,
  Weather,
} from "@/lib/api/types";

function WeatherAlertBanner({ warnings }: { warnings: RecommendationResponse["safety_warnings"] }) {
  if (warnings.length === 0) return null;
  // Deliberately rendered above the candidate list and styled to demand
  // attention: PRD §17 requires severe-weather warnings to take priority
  // over the recommendations themselves, not sit as a footnote under them.
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
        Weather data is temporarily unavailable. Recommendations below are
        scored without it rather than guessing.
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

function SunIcon({ rising }: { rising: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M3 18h18M6 18a6 6 0 0 1 12 0" />
      <path d="M12 4v3M4.9 8.9l2 2M19.1 8.9l-2 2" />
      {rising ? <path d="M12 14V11M10 12.5l2-2 2 2" /> : <path d="M12 10.5v3M10 12l2 2 2-2" />}
    </svg>
  );
}

export function BiteWindows({
  windows,
  fallbackWindow,
}: {
  windows: TimeWindow[];
  fallbackWindow: TimeWindow | null;
}) {
  if (windows.length === 0) {
    // Older backend, or a forecast with no complete morning/evening block.
    if (!fallbackWindow) return null;
    return (
      <div className="best-time-window">
        <strong>Best window:</strong> {lakeClock(fallbackWindow.start_time)}–{lakeClock(fallbackWindow.end_time)}
        <p className="muted">{fallbackWindow.reason}</p>
      </div>
    );
  }
  // Only call one "the better bet" when the difference is real.
  const scored = windows.filter((w) => typeof w.score === "number");
  const top = scored.length === 2 ? [...scored].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))[0] : null;
  const clearWinner =
    top && scored.length === 2 && Math.abs((scored[0].score ?? 0) - (scored[1].score ?? 0)) >= 0.03 ? top : null;

  return (
    <section className="bite-windows" aria-label="Best times to fish">
      <div className="bite-windows-head">
        <strong>Best times to fish</strong>
        <span className="bite-tz">lake time</span>
      </div>
      <div className="bite-grid">
        {windows.map((w) => {
          const morning = w.label === "morning";
          return (
            <div
              key={w.start_time}
              className={`bite-card ${morning ? "bite-morning" : "bite-evening"}${w === clearWinner ? " is-best" : ""}`}
            >
              <div className="bite-top">
                <SunIcon rising={morning} />
                <span>{morning ? "Morning bite" : "Evening bite"}</span>
                {w === clearWinner && <span className="bite-best">Better bet</span>}
              </div>
              <div className="bite-time">
                {lakeClock(w.start_time)} – {lakeClock(w.end_time)}
              </div>
              <div className="bite-day">{lakeDay(w.start_time)}</div>
              <p className="bite-reason">{w.reason}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  return (
    <div className="confidence-bar" title={`${pct}% of the intended signal was available`}>
      <div className="confidence-bar-fill" style={{ width: `${pct}%` }} />
      <span className="confidence-bar-label">{pct}% confidence</span>
    </div>
  );
}

function CandidateCard({ candidate }: { candidate: SpotCandidate }) {
  const [expanded, setExpanded] = useState(false);
  const scorePct = Math.round(candidate.score * 100);

  return (
    <li className="candidate-card">
      <button
        type="button"
        className="candidate-header"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div>
          <strong>{candidate.name}</strong>
          <span className="candidate-access-type"> · {candidate.access_type.replace("_", " ")}</span>
        </div>
        <span className="candidate-score">{scorePct}</span>
      </button>
      <ConfidenceBar confidence={candidate.confidence} />
      {expanded && (
        <ul className="factor-list">
          {candidate.factors.map((f) => (
            <li key={f.name} className={f.value === null ? "factor-missing" : undefined}>
              <div className="factor-row">
                <span className="factor-name">{f.name.replace("_", " ")}</span>
                <span className="factor-value">
                  {f.value === null ? "no data" : `${Math.round(f.value * 100)}`}
                </span>
              </div>
              <p className="factor-reason">{f.reason}</p>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function WeatherRecommendations({
  waterbodyId,
  latitude,
  longitude,
  species,
  targetSpecies,
  onTargetSpeciesChange,
}: {
  waterbodyId: number;
  latitude: number;
  longitude: number;
  species: SpeciesSummary[];
  // Lifted to WaterbodyPanel so the advisor panel below asks about the same
  // fish this ranking was computed for — two panels disagreeing about the
  // target species would be a quiet, plausible-looking bug.
  targetSpecies: string;
  onTargetSpeciesChange: (value: string) => void;
}) {
  const [weather, setWeather] = useState<Weather | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The request a completed fetch answered. Deriving `loading` from this
  // (rather than resetting state at the top of the effect) is what keeps
  // react-hooks/set-state-in-effect quiet — only the async callbacks below
  // ever call setState, same fix as WaterbodyPanel's own loading flag.
  const requestKey = `${waterbodyId}:${latitude}:${longitude}:${targetSpecies}`;
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const loading = loadedKey !== requestKey;

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      getWeather(latitude, longitude),
      postRecommendations({
        waterbody_id: waterbodyId,
        target_species: targetSpecies || undefined,
      }),
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
        setError(e instanceof ApiError ? e.message : "Could not load weather or recommendations.");
        setLoadedKey(requestKey);
      });

    return () => {
      cancelled = true;
    };
  }, [waterbodyId, latitude, longitude, targetSpecies, requestKey]);

  return (
    <div className="weather-recommendations">
      <h3>Weather &amp; recommended spots</h3>

      <label className="species-select-label">
        Target species
        <select
          value={targetSpecies}
          onChange={(e) => onTargetSpeciesChange(e.target.value)}
          className="species-select"
        >
          <option value="">Any species biting</option>
          {species.map((s) => (
            <option key={s.common_name} value={s.common_name}>
              {s.common_name}
            </option>
          ))}
        </select>
      </label>

      {error && !loading && <div className="panel-error">{error}</div>}
      {loading && <div className="muted">Loading weather and recommendations…</div>}

      {recommendations && <WeatherAlertBanner warnings={recommendations.safety_warnings} />}
      {weather && <CurrentWeather weather={weather} />}
      {recommendations && (
        <BiteWindows
          windows={recommendations.bite_windows ?? []}
          fallbackWindow={recommendations.best_time_window}
        />
      )}

      {recommendations && (
        <ul className="candidate-list">
          {recommendations.candidates.map((c) => (
            <CandidateCard key={c.access_point_id} candidate={c} />
          ))}
          {recommendations.candidates.length === 0 && (
            <li className="muted">No confirmed-public access points to rank yet.</li>
          )}
        </ul>
      )}
    </div>
  );
}
