"use client";

import { useEffect, useState } from "react";

import { ApiError, getWeather, postRecommendations } from "@/lib/api/client";
import type {
  RecommendationResponse,
  SpeciesSummary,
  SpotCandidate,
  Weather,
} from "@/lib/api/types";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

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

function BestTimeWindow({ window }: { window: RecommendationResponse["best_time_window"] }) {
  if (window === null) return null;
  return (
    <div className="best-time-window">
      <strong>Best window:</strong> {formatTime(window.start_time)}–{formatTime(window.end_time)}
      <p className="muted">{window.reason}</p>
    </div>
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
}: {
  waterbodyId: number;
  latitude: number;
  longitude: number;
  species: SpeciesSummary[];
}) {
  const [targetSpecies, setTargetSpecies] = useState<string>("");
  const [weather, setWeather] = useState<Weather | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // No separate loading flag, same reasoning as WaterbodyPanel: derive it
  // from whether the data in hand matches the current request.
  const loading = weather === null && error === null;

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setWeather(null);
    setRecommendations(null);

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
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : "Could not load weather or recommendations.");
      });

    return () => {
      cancelled = true;
    };
  }, [waterbodyId, latitude, longitude, targetSpecies]);

  return (
    <div className="weather-recommendations">
      <h3>Weather &amp; recommended spots</h3>

      <label className="species-select-label">
        Target species
        <select
          value={targetSpecies}
          onChange={(e) => setTargetSpecies(e.target.value)}
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

      {error && <div className="panel-error">{error}</div>}
      {loading && !error && <div className="muted">Loading weather and recommendations…</div>}

      {recommendations && <WeatherAlertBanner warnings={recommendations.safety_warnings} />}
      {weather && <CurrentWeather weather={weather} />}
      {recommendations && <BestTimeWindow window={recommendations.best_time_window} />}

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
