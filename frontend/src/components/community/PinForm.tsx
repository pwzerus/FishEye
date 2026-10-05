"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { createPin, getPinOptions } from "@/lib/api/session";
import type { PinDetail, PinOptions, PinVisibility } from "@/lib/api/types";
import { PhotoPicker } from "./PhotoPicker";

function today(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

export function VisibilityToggle({
  value,
  onChange,
  disabled,
}: {
  value: PinVisibility;
  onChange: (v: PinVisibility) => void;
  disabled?: boolean;
}) {
  return (
    <div className="vis-toggle" role="radiogroup" aria-label="Who can see this pin">
      {(
        [
          ["public", "Public", "Shown on the map to everyone"],
          ["private", "Only me", "Your private spot log"],
        ] as const
      ).map(([v, label, sub]) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={value === v}
          disabled={disabled}
          className={value === v ? "vis-option active" : "vis-option"}
          onClick={() => onChange(v)}
        >
          <strong>{label}</strong>
          <span>{sub}</span>
        </button>
      ))}
    </div>
  );
}

/**
 * New pin at a point the user chose on the map. Photos upload with the pin
 * in one request, with a progress bar.
 */
export function PinForm({
  point,
  onCreated,
  onCancel,
}: {
  point: { latitude: number; longitude: number };
  onCreated: (pin: PinDetail) => void;
  onCancel: () => void;
}) {
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [title, setTitle] = useState("");
  const [species, setSpecies] = useState("");
  const [other, setOther] = useState("");
  const [caughtOn, setCaughtOn] = useState(today());
  const [note, setNote] = useState("");
  const [visibility, setVisibility] = useState<PinVisibility>("public");
  const [photos, setPhotos] = useState<File[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPinOptions()
      .then(setOptions)
      .catch(() => setError("Couldn't load the species list. Is the backend running?"));
  }, []);

  const busy = progress !== null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setProgress(0);
    try {
      const pin = await createPin(
        {
          ...point,
          title,
          note: note.trim() || undefined,
          species_slug: species && species !== "__other" ? species : undefined,
          species_other: species === "__other" ? other : undefined,
          caught_on: caughtOn || undefined,
          visibility,
          photos,
        },
        setProgress,
      );
      onCreated(pin);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save the pin. Try again.");
      setProgress(null);
    }
  }

  return (
    <form className="pin-form" onSubmit={submit}>
      <header className="pin-form-head">
        <h2>New pin</h2>
        <p className="muted">
          {point.latitude.toFixed(5)}, {point.longitude.toFixed(5)} · drag the pin on the map to adjust
        </p>
      </header>

      <label className="field">
        <span>Title</span>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Rocks by the boat ramp"
          maxLength={80}
          required
          disabled={busy}
          autoFocus
        />
      </label>

      <div className="field-row">
        <label className="field">
          <span>Fish</span>
          <select value={species} onChange={(e) => setSpecies(e.target.value)} disabled={busy}>
            <option value="">Not sure / none</option>
            {options?.species.map((s) => (
              <option key={s.slug} value={s.slug}>
                {s.label}
              </option>
            ))}
            <option value="__other">Other…</option>
          </select>
        </label>
        <label className="field">
          <span>Date</span>
          <input type="date" value={caughtOn} max={today()} onChange={(e) => setCaughtOn(e.target.value)} disabled={busy} />
        </label>
      </div>
      {species === "__other" && (
        <label className="field">
          <span>Which fish?</span>
          <input value={other} onChange={(e) => setOther(e.target.value)} maxLength={60} disabled={busy} />
        </label>
      )}

      <label className="field">
        <span>Notes</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          maxLength={1000}
          placeholder="Bait, depth, time of day, what worked…"
          disabled={busy}
        />
      </label>

      <div className="field">
        <span>Who can see it</span>
        <VisibilityToggle value={visibility} onChange={setVisibility} disabled={busy} />
      </div>

      <div className="field">
        <span>Photos</span>
        <PhotoPicker
          files={photos}
          onChange={setPhotos}
          max={options?.max_photos ?? 4}
          maxMb={options?.max_photo_mb ?? 10}
          disabled={busy}
        />
      </div>

      {visibility === "public" && (
        <p className="hint">
          Public pins go live right away. Other anglers can report a pin that breaks the rules; a moderator reviews it.
        </p>
      )}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {busy && (
        <div className="upload-progress" role="progressbar" aria-valuenow={Math.round((progress ?? 0) * 100)} aria-valuemin={0} aria-valuemax={100}>
          <span style={{ transform: `scaleX(${progress ?? 0})` }} />
          <small>{(progress ?? 0) < 1 ? `Uploading ${Math.round((progress ?? 0) * 100)}%` : "Processing photos…"}</small>
        </div>
      )}

      <div className="form-actions">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary btn-sm" disabled={busy || title.trim().length < 3}>
          {busy ? "Saving…" : "Save pin"}
        </button>
      </div>
    </form>
  );
}
