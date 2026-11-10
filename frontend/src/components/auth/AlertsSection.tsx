"use client";

import { useEffect, useState } from "react";

import { SpeciesOptions } from "@/components/community/PinForm";
import { useToast } from "@/components/ui/Toast";
import { useLocale, useT } from "@/i18n/client";
import { localFishName } from "@/i18n/names";
import { ApiError, geocodePlace } from "@/lib/api/client";
import { createAlert, deleteAlert, getPinOptions, listAlerts, sendVerificationEmail } from "@/lib/api/session";
import type { AlertsInfo, PinOptions } from "@/lib/api/types";

function locate(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) reject(new Error("unsupported"));
    else navigator.geolocation.getCurrentPosition(resolve, reject, { maximumAge: 10 * 60 * 1000, timeout: 15000 });
  });
}

/** "Email me when someone confirms this fish near here" (backend services/alerts.py). */
export function AlertsSection() {
  const t = useT().alerts;
  const locale = useLocale();
  const toast = useToast();
  const [info, setInfo] = useState<AlertsInfo | null>(null);
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [species, setSpecies] = useState("");
  const [place, setPlace] = useState("");
  const [here, setHere] = useState<{ latitude: number; longitude: number } | null>(null);
  const [radius, setRadius] = useState("30");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listAlerts().then(setInfo).catch(() => setInfo(null));
    getPinOptions().then(setOptions).catch(() => undefined);
  }, []);

  if (!info) return <div className="sk sk-line" />;

  const fishName = (slug: string, english: string) => localFishName(slug, locale) ?? english;

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      let point = here;
      let label = place.trim();
      if (!point) {
        const found = await geocodePlace(label);
        point = { latitude: found.latitude, longitude: found.longitude };
        label = found.display_name.split(",").slice(0, 2).join(",").trim() || label;
      }
      const added = await createAlert({ species_slug: species, ...point, place: label, radius_miles: Number(radius), lang: locale });
      setInfo((now) => now && { ...now, alerts: [...now.alerts, added] });
      setSpecies("");
      setPlace("");
      setHere(null);
      toast(t.added);
    } catch (err) {
      toast(err instanceof ApiError ? (err.status === 404 ? t.notFound : err.message) : t.failed, "error");
    } finally {
      setBusy(false);
    }
  }

  async function useMyLocation() {
    try {
      const pos = await locate();
      setHere({ latitude: pos.coords.latitude, longitude: pos.coords.longitude });
      setPlace(t.myLocation);
    } catch {
      toast(t.locateFailed, "error");
    }
  }

  const radiusOk = Number(radius) >= info.min_radius && Number(radius) <= info.max_radius && Number.isInteger(Number(radius));
  const full = info.alerts.length >= info.max_alerts;

  return (
    <>
      <p className="muted small">{t.intro}</p>
      {!info.sending && <p className="hint hint-warn">{t.notSending}</p>}
      {info.sending && !info.email_confirmed && (
        <p className="hint hint-warn">
          {t.needConfirm(info.email)}{" "}
          <button
            type="button"
            className="text-link"
            onClick={async () => {
              try {
                await sendVerificationEmail();
                toast(t.confirmSent);
              } catch (err) {
                toast(err instanceof ApiError ? err.message : t.failed, "error");
              }
            }}
          >
            {t.sendConfirm}
          </button>
        </p>
      )}

      {info.alerts.length > 0 && (
        <ul className="alert-list">
          {info.alerts.map((a) => (
            <li key={a.id}>
              <span>{t.line(fishName(a.species_slug, a.species_label), a.radius_miles, a.place)}</span>
              <button
                type="button"
                className="text-link"
                onClick={async () => {
                  try {
                    await deleteAlert(a.id);
                    setInfo((now) => now && { ...now, alerts: now.alerts.filter((o) => o.id !== a.id) });
                  } catch (err) {
                    toast(err instanceof ApiError ? err.message : t.failed, "error");
                  }
                }}
              >
                {t.remove}
              </button>
            </li>
          ))}
        </ul>
      )}

      {!full && (
        <form className="alert-form" onSubmit={add}>
          <label className="field">
            <span>{t.fish}</span>
            <select value={species} onChange={(e) => setSpecies(e.target.value)} required>
              <SpeciesOptions options={options} otherValue="" allLabel={t.pickFish} />
            </select>
          </label>
          <label className="field">
            <span>{t.place}</span>
            <input
              value={place}
              onChange={(e) => {
                setPlace(e.target.value);
                setHere(null);
              }}
              placeholder={t.placeHint}
              maxLength={100}
              required
            />
          </label>
          <button type="button" className="text-link alert-here" onClick={useMyLocation}>
            {t.useMine}
          </button>
          <label className="field">
            <span>{t.radius}</span>
            <input type="number" inputMode="numeric" min={info.min_radius} max={info.max_radius} value={radius} onChange={(e) => setRadius(e.target.value)} required />
          </label>
          <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !species || !place.trim() || !radiusOk}>
            {t.add}
          </button>
        </form>
      )}
      <p className="muted small">{full ? t.full(info.max_alerts) : t.limits}</p>
    </>
  );
}
