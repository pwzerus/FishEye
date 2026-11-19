"use client";

import { useLocale, useT } from "@/i18n/client";
import type { Messages } from "@/i18n/messages";
import { localWindSpeed } from "@/i18n/weather";
import { SKIES, type PinWeather, type Sky } from "@/lib/api/types";

/** When a catch was made and the weather then (backend
 * services/catch_weather.py): the time field's helpers, the sky icons and
 * the sky picker the catch form and the edit dialog share. */

const DAY_MS = 86_400_000;
// The weather service keeps 7 days of station reports; the server looks a
// catch up when it was made within the last 6.5 (LOOKUP_DAYS).
const LOOKUP_MS = 6.5 * DAY_MS;

/** This device's clock offset from UTC in minutes east (-300 for Central
 * daylight time), on that day at that time: what the server needs to place
 * "06:40" against sunrise and the hourly reports. */
export function utcOffset(day: string, time: string): number {
  const at = new Date(`${day}T${time || "12:00"}:00`);
  return -(Number.isNaN(at.getTime()) ? new Date() : at).getTimezoneOffset();
}

/** Whether the server can still look the weather up for that day and time. */
export function canLookUpWeather(day: string, time: string, now = Date.now()): boolean {
  if (!day || !time) return false;
  const at = new Date(`${day}T${time}:00`).getTime();
  return !Number.isNaN(at) && at >= now - LOOKUP_MS && at <= now + 3_600_000;
}

/** "06:40" as the reader's language writes a time of day ("6:40 AM"). */
export function formatClock(hhmm: string, tag: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  if (!Number.isFinite(h) || !Number.isFinite(m)) return hhmm;
  return new Date(Date.UTC(2000, 0, 1, h, m)).toLocaleTimeString(tag, { hour: "numeric", minute: "2-digit", timeZone: "UTC" });
}

/** "Partly cloudy · 72°F · wind 10 mph · pressure falling", in the reader's language. */
export function weatherLine(t: Messages["catch"], w: PinWeather, locale: ReturnType<typeof useLocale>): string {
  const parts: string[] = [];
  if (w.sky) parts.push(t.sky[w.sky]);
  if (w.temp_f !== null) parts.push(`${Math.round(w.temp_f)}°F`);
  if (w.wind_mph !== null) parts.push(t.windSpeed(localWindSpeed(`${Math.round(w.wind_mph)} mph`, locale) ?? ""));
  if (w.trend) parts.push(t.pressure[w.trend]);
  return parts.join(" · ");
}

const ICON = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

/** A small line drawing of the sky. */
export function SkyIcon({ sky, size = 20 }: { sky: Sky; size?: number }) {
  const cloud = "M7.5 18.5h9.25a3.75 3.75 0 0 0 .45-7.47A5.25 5.25 0 0 0 7.1 10.6 4 4 0 0 0 7.5 18.5z";
  switch (sky) {
    case "clear":
      return (
        <svg {...ICON} width={size} height={size}>
          <circle cx="12" cy="12" r="4.2" />
          <path d="M12 2.8v2M12 19.2v2M2.8 12h2M19.2 12h2M5.5 5.5l1.4 1.4M17.1 17.1l1.4 1.4M5.5 18.5l1.4-1.4M17.1 6.9l1.4-1.4" />
        </svg>
      );
    case "partly":
      return (
        <svg {...ICON} width={size} height={size}>
          <path d="M8.6 7.4A3.6 3.6 0 0 1 14.4 6M8.2 3.2v1.5M3.6 7.8h1.5M4.9 4.5l1 1" />
          <path d="M8 19.5h8.6a3.4 3.4 0 0 0 .4-6.77 4.8 4.8 0 0 0-9.2-.4A3.6 3.6 0 0 0 8 19.5z" />
        </svg>
      );
    case "cloudy":
      return (
        <svg {...ICON} width={size} height={size}>
          <path d={cloud} />
        </svg>
      );
    case "rain":
      return (
        <svg {...ICON} width={size} height={size}>
          <path d="M7.5 15h9.25a3.75 3.75 0 0 0 .45-7.47A5.25 5.25 0 0 0 7.1 7.1 4 4 0 0 0 7.5 15z" />
          <path d="M9 18l-1 2.5M13 18l-1 2.5M17 18l-1 2.5" />
        </svg>
      );
    case "snow":
      return (
        <svg {...ICON} width={size} height={size}>
          <path d="M7.5 15h9.25a3.75 3.75 0 0 0 .45-7.47A5.25 5.25 0 0 0 7.1 7.1 4 4 0 0 0 7.5 15z" />
          <path d="M8.5 18.5h.01M12 20h.01M15.5 18.5h.01" strokeWidth={2.6} />
        </svg>
      );
  }
}

/** The angler's own sky, for a catch too old for the weather service.
 * Tapping the chosen one again takes it off. */
export function SkyPicker({ value, onChange, disabled }: { value: Sky | ""; onChange: (s: Sky | "") => void; disabled?: boolean }) {
  const t = useT().catch;
  return (
    <div className="field">
      <span id="sky-picker-label">{t.weather}</span>
      <div className="sky-picker" role="radiogroup" aria-labelledby="sky-picker-label">
        {SKIES.map((s) => (
          <button
            key={s}
            type="button"
            role="radio"
            aria-checked={value === s}
            className={value === s ? "sky-option active" : "sky-option"}
            disabled={disabled}
            onClick={() => onChange(value === s ? "" : s)}
          >
            <SkyIcon sky={s} />
            <span>{t.sky[s]}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
