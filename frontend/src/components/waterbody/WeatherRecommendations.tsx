"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ContentSkeleton } from "@/components/ui/ContentSkeleton";

import { useLocale, useT } from "@/i18n/client";
import type { Locale } from "@/i18n/config";
import { LOCALE_TAGS } from "@/i18n/config";
import { MESSAGES, type Messages } from "@/i18n/messages";
import { fishSlug, localFishName } from "@/i18n/names";
import { localDirection, localForecast, localWindSpeed } from "@/i18n/weather";
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
  const t = useT().plan;
  const locale = useLocale();
  if (weather.source === "fallback") {
    // Never present fallback placeholders (null temperature, empty hourly)
    // as real readings — say plainly that the service is unavailable.
    return <div className="weather-summary weather-unavailable">{t.weatherDown}</div>;
  }

  const { current } = weather;
  return (
    <div className="weather-summary">
      <div className="weather-now">
        <span className="weather-temp">
          {current.temperature !== null ? `${Math.round(current.temperature)}°${current.temperature_unit}` : "—"}
        </span>
        <span className="weather-forecast">{localForecast(current.short_forecast, locale)}</span>
      </div>
      <div className="weather-wind">{t.wind(localWindSpeed(current.wind_speed, locale), localDirection(current.wind_direction, locale))}</div>
    </div>
  );
}

/** The languages that write the clock 24-hour, and how each joins two
 * times into a range ("5:00〜8:00"). */
const H24: Partial<Record<Locale, string>> = { zh: "–", ja: "〜", ko: "~" };

/**
 * Clock time read straight off the ISO string, which carries the lake's own
 * UTC offset. Formatting through `Date` would convert to the viewer's zone:
 * someone in Michigan planning a Texas trip would see the dawn bite an hour
 * late. "6:30 PM" in English and Spanish ("p. m."), "18:30" in Chinese,
 * Japanese and Korean.
 */
export function lakeClock(iso: string, locale: Locale = "en"): string {
  const m = /T(\d{2}):(\d{2})/.exec(iso);
  if (!m) return iso;
  const h = Number(m[1]);
  if (H24[locale]) return `${h}:${m[2]}`;
  const h12 = h % 12 === 0 ? 12 : h % 12;
  const t = MESSAGES[locale].plan;
  return `${h12}${m[2] === "00" ? "" : `:${m[2]}`} ${h < 12 ? t.am : t.pm}`;
}

/** "Today" / "Tomorrow" / weekday, judged in lake time too. */
export function lakeDay(iso: string, now: Date = new Date(), locale: Locale = "en"): string {
  const off = /([+-])(\d{2}):(\d{2})$/.exec(iso);
  const offsetMin = off ? (off[1] === "-" ? -1 : 1) * (Number(off[2]) * 60 + Number(off[3])) : 0;
  const lakeToday = new Date(now.getTime() + offsetMin * 60_000).toISOString().slice(0, 10);
  const date = iso.slice(0, 10);
  const t = MESSAGES[locale].plan;
  const cap = (s: string) => (locale === "en" ? s.charAt(0).toUpperCase() + s.slice(1) : s);
  if (date === lakeToday) return cap(t.today);
  const tomorrow = new Date(Date.parse(`${lakeToday}T00:00:00Z`) + 86_400_000).toISOString().slice(0, 10);
  if (date === tomorrow) return cap(t.tomorrow);
  return new Date(`${date}T12:00:00Z`).toLocaleDateString(LOCALE_TAGS[locale], { weekday: "long", timeZone: "UTC" });
}

/** "6–9 PM", or "11 AM–2 PM" when the window crosses noon ("18:00–21:00"). */
export function lakeRange(startIso: string, endIso: string, locale: Locale = "en"): string {
  const start = lakeClock(startIso, locale);
  const end = lakeClock(endIso, locale);
  const sep = H24[locale];
  if (sep) return `${start}${sep}${end}`;
  const half = (s: string) => s.slice(s.indexOf(" ") + 1);
  const time = (s: string) => s.slice(0, s.indexOf(" "));
  return half(start) === half(end) ? `${time(start)}–${end}` : `${start}–${end}`;
}

function windowText(w: PlanWindow, t: Messages["plan"], locale: Locale): string {
  const bite = w.label === "morning" ? t.morningBite : w.label === "evening" ? t.eveningBite : t.bestWindow;
  const day = lakeDay(w.start_time, new Date(), locale);
  return t.window(bite, lakeRange(w.start_time, w.end_time, locale), locale === "en" ? day.toLowerCase() : day);
}

function shortWindowText(w: PlanWindow, t: Messages["plan"], locale: Locale): string {
  const day = lakeDay(w.start_time, new Date(), locale);
  return t.windowShort(lakeRange(w.start_time, w.end_time, locale), locale === "en" ? day.toLowerCase() : day);
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
  updating = false,
  selectedSpecies,
}: {
  plan: FishingPlan;
  onSpeciesChange: (species: string) => void;
  updating?: boolean;
  selectedSpecies?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const t = useT().plan;
  const locale = useLocale();
  const fish = (name: string) => localFishName(fishSlug(name), locale) ?? name;
  return (
    <section className={`plan-card${expanded ? " plan-expanded" : ""}`} aria-label={t.aria} aria-busy={updating}>
      <label className="plan-fish">
        <span>{t.fishingFor}</span>
        <select value={selectedSpecies ?? plan.species ?? ""} disabled={updating} onChange={(e) => onSpeciesChange(e.target.value)}>
          {plan.species === null && <option value="">{t.pickFish}</option>}
          {plan.species_options.map((name) => (
            <option key={name} value={name}>
              {fish(name) === name ? name : `${fish(name)} · ${name}`}
            </option>
          ))}
        </select>
      </label>
      {updating && <p className="plan-updating" role="status">{t.updating}</p>}
      {plan.species && plan.species_on_record === false && <p className="plan-note">{t.notOnRecord}</p>}

      {plan.heads_up.length > 0 && (
        <ul className="plan-heads-up">
          {plan.heads_up.map((h) => (
            <li key={h}>{h}</li>
          ))}
        </ul>
      )}

      <dl className="plan-rows" id="plan-contents">
        {plan.where && (
          <div>
            <dt>{t.where}</dt>
            <dd className="plan-where">{plan.where.text}</dd>
          </div>
        )}
        {plan.when && (
          <div>
            <dt>{t.when}</dt>
            <dd>
              <span className="plan-window-short">{shortWindowText(plan.when, t, locale)}</span><span className="plan-window-full">{windowText(plan.when, t, locale)}</span>
              {plan.also && <span className="plan-also">{t.or(shortWindowText(plan.also, t, locale))}</span>}
              {plan.conditions && <span className="plan-conditions">{plan.conditions}</span>}
            </dd>
          </div>
        )}
        {!plan.where && !plan.when && (
          <div>
            <dt>{t.when}</dt>
            <dd className="muted">{t.noForecast}</dd>
          </div>
        )}
        {plan.species ? (
          <>
            <div>
              <dt>{t.lures}</dt>
              <dd>{plan.lures.length > 0 ? <Picks picks={plan.lures} /> : plan.lure_note}</dd>
            </div>
            {plan.baits.length > 0 && (
              <div>
                <dt>{t.bait}</dt>
                <dd>
                  <Picks picks={plan.baits} />
                </dd>
              </div>
            )}
            {plan.species_slug && (
              <div>
                <dt>{t.guide}</dt>
                <dd>
                  <Link href={`/fish/${plan.species_slug}`} className="plan-guide-link">
                    {t.guideLink(fish(plan.species))} <span aria-hidden="true">→</span>
                  </Link>
                </dd>
              </div>
            )}
          </>
        ) : (
          <div>
            <dt>{t.tackle}</dt>
            <dd className="muted">{t.pickForTackle}</dd>
          </div>
        )}
      </dl>
      <button type="button" className="plan-expand" aria-expanded={expanded} aria-controls="plan-contents" onClick={() => setExpanded((value) => !value)}>{expanded ? t.less : t.more}</button>
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
  const all = useT();
  const t = all.plan;
  const locale = useLocale();
  const [weather, setWeather] = useState<Weather | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // "" = let the backend pick this lake's main fish.
  const [species, setSpecies] = useState("");
  const [attempt, setAttempt] = useState(0);
  // The request a completed fetch answered. Deriving `loading` from this
  // (rather than resetting state at the top of the effect) is what keeps
  // react-hooks/set-state-in-effect quiet — only the async callbacks below
  // ever call setState, same fix as WaterbodyPanel's own loading flag.
  const requestKey = `${waterbodyId}:${latitude}:${longitude}:${species}:${attempt}`;
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const loading = loadedKey !== requestKey;

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      getWeather(latitude, longitude),
      postRecommendations({ waterbody_id: waterbodyId, target_species: species || undefined, lang: locale }),
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
        setError(e instanceof ApiError ? e.message : t.loadError);
        setLoadedKey(requestKey);
      });

    return () => {
      cancelled = true;
    };
  }, [waterbodyId, latitude, longitude, species, requestKey, locale, t.loadError]);

  return (
    <div className="weather-recommendations">
      <h3>{t.title}</h3>

      {error && !loading && <div className="panel-error" role="alert"><p>{error}</p><button className="btn btn-ghost btn-sm" type="button" onClick={() => setAttempt((value) => value + 1)}>{all.common.tryAgain}</button></div>}
      {loading && !recommendations && <ContentSkeleton label={t.loading} />}

      {recommendations && <WeatherAlertBanner warnings={recommendations.safety_warnings} />}
      {recommendations?.plan && (!error || loading) && <PlanCard plan={recommendations.plan} onSpeciesChange={setSpecies} updating={loading} selectedSpecies={species || undefined} />}
      {weather && (
        <>
          <div className="plan-now-label">{t.rightNow}</div>
          <CurrentWeather weather={weather} />
        </>
      )}
    </div>
  );
}
