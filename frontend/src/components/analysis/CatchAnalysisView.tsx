"use client";

import Link from "@/components/LocaleLink";
import { useRouter } from "next/navigation";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { SkyIcon } from "@/components/community/catchWhen";
import { formatDay } from "@/components/community/PinCard";
import { useLocale, useLocaleTag, useT } from "@/i18n/client";
import { localGearName, localSpecies } from "@/i18n/names";
import { ApiError } from "@/lib/api/client";
import { getCatchAnalysis } from "@/lib/api/session";
import type { CatchAnalysis, CatchAnalysisCount, CatchAnalysisFish, Sky } from "@/lib/api/types";

/** "My catch analysis" (the business plan's log analysis, free in beta):
 * the angler's own catches counted by fish, bait, time of day, weather,
 * month and water (backend services/catch_analysis.py). Every chart is one
 * series in one colour, its numbers printed beside it, so nothing hides
 * behind a hover. */

interface Row {
  key: string;
  label: ReactNode;
  // What a screen reader and the tooltip call it.
  name: string;
  count: number;
  icon?: ReactNode;
}

const vars = (v: Record<string, string | number>) => v as CSSProperties;

/** A list of named bars: name, bar, count. `of` is what each share is out of. */
function Bars({ rows, of, label }: { rows: Row[]; of: number; label: string }) {
  const t = useT().analysis;
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <ul className="an-bars" aria-label={label}>
      {rows.map((r, i) => {
        const pct = of ? Math.round((r.count / of) * 100) : 0;
        const share = t.share(r.count, of, pct);
        return (
          <li key={r.key} className="an-bar" tabIndex={0} aria-label={`${r.name}: ${share}`} style={vars({ "--i": i })}>
            <span className="an-bar-name" aria-hidden="true">
              {r.icon}
              <span>{r.label}</span>
            </span>
            <span className="an-bar-track" aria-hidden="true">
              <span className="an-bar-fill" style={vars({ "--w": r.count / max })} />
            </span>
            <span className="an-bar-n" aria-hidden="true">
              {r.count}
            </span>
            <span className="an-tip" aria-hidden="true">
              {share}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** Catches by month: twelve columns with the busiest one labelled; each
 * column tells its count on hover and on keyboard focus. */
function Months({ months, tag, caption }: { months: number[]; tag: string; caption: string }) {
  const t = useT().analysis;
  const max = Math.max(1, ...months);
  const busiest = months.indexOf(Math.max(...months));
  const name = (m: number, month: "narrow" | "long") =>
    new Date(Date.UTC(2026, m, 15)).toLocaleDateString(tag, { month, timeZone: "UTC" });
  // J F M… in English and Spanish; 1 2 3… where a month is a number (1月).
  const short = (m: number) => {
    const n = name(m, "narrow");
    return /^\d/.test(n) ? String(m + 1) : n;
  };
  const total = months.reduce((a, b) => a + b, 0);
  return (
    <ul className="an-cols" aria-label={caption}>
      {months.map((n, m) => {
        const share = t.share(n, total, total ? Math.round((n / total) * 100) : 0);
        return (
          <li key={m} className="an-col" tabIndex={0} aria-label={`${name(m, "long")}: ${share}`}>
            <span className="an-col-plot" aria-hidden="true">
              {n > 0 && m === busiest && <span className="an-col-n">{n}</span>}
              <span className="an-col-fill" style={vars({ "--h": n / max, "--i": m })} />
            </span>
            <span className="an-col-name" aria-hidden="true">
              {short(m)}
            </span>
            <span className="an-tip" aria-hidden="true">
              {name(m, "long")} · {share}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function Card({ title, caption, children, wide }: { title: string; caption?: string | null; children: ReactNode; wide?: boolean }) {
  return (
    <section className={wide ? "an-card an-wide" : "an-card"}>
      <header>
        <h2>{title}</h2>
        {caption && <p className="an-caption">{caption}</p>}
      </header>
      {children}
    </section>
  );
}

/** The most common key, or the tied ones (up to two). */
function top(counts: CatchAnalysisCount[]): string[] {
  const best = Math.max(0, ...counts.map((c) => c.count));
  return best ? counts.filter((c) => c.count === best).map((c) => c.key).slice(0, 2) : [];
}

const NEED_FOR_TOP = 3;

export function CatchAnalysisView() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const all = useT();
  const t = all.analysis;
  const tc = all.catch;
  const locale = useLocale();
  const tag = useLocaleTag();
  const [species, setSpecies] = useState("");
  const [data, setData] = useState<{ species: string; body: CatchAnalysis } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login?next=/account/analysis");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    getCatchAnalysis(species || undefined)
      .then((body) => {
        if (cancelled) return;
        setData({ species, body });
        setError(null);
      })
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e.message : t.loadError));
    return () => {
      cancelled = true;
    };
  }, [user, species, t.loadError]);

  if (loading || !user || (!data && !error)) {
    return (
      <div className="an" aria-busy="true">
        <div className="sk sk-title" />
        <div className="an-tiles">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="sk" style={{ height: 96, borderRadius: 18 }} />
          ))}
        </div>
      </div>
    );
  }

  const body = data?.body;
  // Holding the last answer, faded, while another fish loads.
  const refreshing = data !== null && data.species !== species;
  const fishName = (f: CatchAnalysisFish) => (f.slug ? (localSpecies(f.slug, f.label, locale) ?? f.label) : f.label);
  const gearName = (id: string) => localGearName(id, locale) ?? body?.baits.find((b) => b.key === id)?.label ?? id;
  const join = (names: string[]) => names.join(" / ");

  const tiles: { key: string; label: string; value: string; icon?: ReactNode; n: number; of: number }[] = [];
  if (body) {
    const fish = body.fish.filter((f) => f.count === body.fish[0]?.count).slice(0, 2);
    const withFish = body.fish.reduce((a, f) => a + f.count, 0);
    if (!body.species && fish.length && withFish >= NEED_FOR_TOP)
      tiles.push({ key: "fish", label: t.topFish, value: join(fish.map(fishName)), n: fish[0].count, of: withFish });
    const bait = top(body.baits);
    if (bait.length && body.baits_logged >= NEED_FOR_TOP)
      tiles.push({ key: "bait", label: t.topBait, value: join(bait.map(gearName)), n: body.baits.find((b) => b.key === bait[0])!.count, of: body.baits_logged });
    const time = top(body.times);
    if (time.length && body.times_logged >= NEED_FOR_TOP)
      tiles.push({
        key: "time",
        label: t.topTime,
        value: join(time.map((k) => t.timeNames[k as keyof typeof t.timeNames])),
        n: body.times.find((x) => x.key === time[0])!.count,
        of: body.times_logged,
      });
    const sky = top(body.skies);
    if (sky.length && body.weather_logged >= NEED_FOR_TOP)
      tiles.push({
        key: "sky",
        label: t.topSky,
        value: join(sky.map((k) => tc.sky[k as Sky])),
        icon: <SkyIcon sky={sky[0] as Sky} size={22} />,
        n: body.skies.find((x) => x.key === sky[0])!.count,
        of: body.weather_logged,
      });
  }

  const named = <K extends string>(counts: CatchAnalysisCount[], names: Record<K, string>, icon?: (k: K) => ReactNode): Row[] =>
    counts.map((c) => ({ key: c.key, label: names[c.key as K], name: names[c.key as K], count: c.count, icon: icon?.(c.key as K) }));

  return (
    <div className="an">
      <header className="an-hero">
        <div className="an-title-row">
          <h1>{t.title}</h1>
          <span className="an-beta">{t.freeBeta}</span>
        </div>
        {body && body.total > 0 && (
          <p className="an-lede">
            {body.species ? tc.count(body.total) : t.summary(body.total, body.all_species.length)}
            {body.first_on && ` · ${t.since(formatDay(body.first_on, tag) ?? body.first_on)}`}
          </p>
        )}
        {body && body.all_species.length > 1 && (
          <label className="an-select cf-select">
            <span className="sr-only">{t.whichFish}</span>
            <select value={species} onChange={(e) => setSpecies(e.target.value)}>
              <option value="">{t.allFish}</option>
              {body.all_species.map((f) => (
                <option key={f.key} value={f.key}>
                  {fishName(f)} · {f.count}
                </option>
              ))}
            </select>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </label>
        )}
      </header>

      {error && !body ? (
        <div className="backend-error">{error}</div>
      ) : body && body.total === 0 ? (
        <div className="an-empty">
          <p>{t.empty}</p>
          <Link href="/map?addPin=1" className="btn btn-primary">
            {tc.shareTitle}
          </Link>
        </div>
      ) : (
        body && (
          <div className={refreshing ? "an-body is-refreshing" : "an-body"} aria-busy={refreshing}>
            {tiles.length > 0 && (
              <div className="an-tiles">
                {tiles.map((tile, i) => (
                  <div key={tile.key} className="an-tile" style={vars({ "--i": i })}>
                    <span className="an-tile-label">{tile.label}</span>
                    <strong className="an-tile-value">
                      {tile.icon}
                      {tile.value}
                    </strong>
                    <span className="an-tile-sub">{t.ofCatches(tile.n, tile.of)}</span>
                  </div>
                ))}
              </div>
            )}
            {body.total < 5 && <p className="hint an-few">{t.few}</p>}

            <div className="an-grid">
              <Card title={t.baits} caption={body.baits_logged ? t.baitsLogged(body.baits_logged) : null}>
                {body.baits.length ? (
                  <Bars
                    label={t.baits}
                    of={body.baits_logged}
                    rows={body.baits.map((b) => ({ key: b.key, label: gearName(b.key), name: gearName(b.key), count: b.count }))}
                  />
                ) : (
                  <p className="an-none">{t.noBaits}</p>
                )}
              </Card>

              <Card title={t.times} caption={body.times_logged ? t.timesLogged(body.times_logged) : null}>
                {body.times_logged ? (
                  <Bars label={t.times} of={body.times_logged} rows={named(body.times, t.timeNames)} />
                ) : (
                  <p className="an-none">{t.noTimes}</p>
                )}
              </Card>

              <Card title={t.weather} caption={body.weather_logged ? t.weatherLogged(body.weather_logged) : null} wide>
                {body.weather_logged ? (
                  <div className="an-weather">
                    <div>
                      <h3>{t.sky}</h3>
                      <Bars
                        label={t.sky}
                        of={body.weather_logged}
                        rows={named(body.skies, tc.sky, (k) => <SkyIcon sky={k} size={18} />)}
                      />
                    </div>
                    {body.trends.some((x) => x.count) && (
                      <div>
                        <h3>{t.pressure}</h3>
                        <Bars label={t.pressure} of={body.weather_logged} rows={named(body.trends, t.trendNames)} />
                      </div>
                    )}
                    {body.temps.some((x) => x.count) && (
                      <div>
                        <h3>{t.temp}</h3>
                        <Bars label={t.temp} of={body.weather_logged} rows={named(body.temps, t.tempNames)} />
                      </div>
                    )}
                    {body.winds.some((x) => x.count) && (
                      <div>
                        <h3>{t.wind}</h3>
                        <Bars label={t.wind} of={body.weather_logged} rows={named(body.winds, t.windNames)} />
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="an-none">{t.noWeather}</p>
                )}
              </Card>

              {!body.species && body.fish.length > 0 && (
                <Card title={t.fish}>
                  <Bars
                    label={t.fish}
                    of={body.total}
                    rows={body.fish.slice(0, 8).map((f) => ({ key: f.key, label: fishName(f), name: fishName(f), count: f.count }))}
                  />
                </Card>
              )}

              {body.waters.length > 0 && (
                <Card title={t.waters} wide={!!body.species}>
                  <Bars
                    label={t.waters}
                    of={body.total}
                    rows={body.waters.map((w) => ({ key: `${w.kind}-${w.id}`, label: w.name, name: w.name, count: w.count }))}
                  />
                </Card>
              )}

              <Card title={t.months} wide>
                <Months months={body.months} tag={tag} caption={t.monthTable} />
              </Card>
            </div>

            <details className="cf-rules an-how">
              <summary>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 11v5M12 8h.01" />
                </svg>
                {t.how}
              </summary>
              <ul>
                <li>{t.howMine}</li>
                <li>{t.howSun}</li>
                <li>{t.howWeather}</li>
                <li>{t.howWind}</li>
                <li>{t.howCounts}</li>
              </ul>
            </details>
          </div>
        )
      )}
    </div>
  );
}
