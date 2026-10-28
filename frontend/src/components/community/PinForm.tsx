"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { createPin, getPinOptions, identifyFish } from "@/lib/api/session";
import type { FishIdResult, PinDetail, PinOptions, PinVisibility } from "@/lib/api/types";
import { readPhotoFacts } from "@/lib/exif";
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

const OTHER = "__other";
// The likeliest guide species is filled in for the angler from this sure.
const SUGGEST_FROM = 0.5;

type Check =
  | { state: "checking" }
  | { state: "done"; result: FishIdResult }
  | { state: "off" } // the server doesn't check photos (FISH_ID=off)
  | { state: "error"; message: string };

function percent(p: number): string {
  return `${Math.round(p * 100)}%`;
}

/** What the photo check said, under the catch photo. */
export function FishCheckNote({
  check,
  onPick,
  onPickOther,
}: {
  check: Check | null;
  onPick: (slug: string) => void;
  onPickOther: (name: string) => void;
}) {
  if (!check || check.state === "off") return null;
  if (check.state === "checking") {
    return (
      <p className="fish-check is-checking" role="status">
        <span className="fish-check-spinner" aria-hidden="true" /> Checking which fish this is… (a few seconds)
      </p>
    );
  }
  if (check.state === "error") {
    return (
      <p className="fish-check is-error" role="status">
        {check.message}
      </p>
    );
  }
  const { verdict, candidates } = check.result;
  if (!verdict) {
    const fish = candidates.filter((c) => c.probability >= 0.05).slice(0, 3);
    if (fish.length === 0) return null;
    return (
      <div className="fish-check" role="status">
        <span>Looks like:</span>
        {fish.map((c) =>
          c.in_guides ? (
            <button key={c.slug} type="button" className="chip fish-check-chip" onClick={() => onPick(c.slug)}>
              {c.label} <small>{percent(c.probability)}</small>
            </button>
          ) : (
            <button key={c.slug} type="button" className="chip fish-check-chip" onClick={() => onPickOther(c.label)}>
              {c.label} <small>{percent(c.probability)}</small>
            </button>
          ),
        )}
      </div>
    );
  }
  if (verdict.accepted) {
    return (
      <p className={verdict.status === "confirmed" ? "fish-check is-ok" : "fish-check is-group"} role="status">
        <span aria-hidden="true">✓ </span>
        {verdict.message}
      </p>
    );
  }
  return (
    <div className="fish-check is-bad" role="alert">
      <p>{verdict.message}</p>
      {verdict.detected && verdict.detected_label && verdict.detected_in_guides && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onPick(verdict.detected!)}>
          Change to {verdict.detected_label}
        </button>
      )}
      {verdict.status === "other_fish" && verdict.detected_label && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onPickOther(verdict.detected_label!)}>
          Choose Other: {verdict.detected_label}
        </button>
      )}
      {/* Never a dead end: the catch can still go up, with no fish named. */}
      <button type="button" className="text-link fish-check-skip" onClick={() => onPick("")}>
        Share without naming the fish
      </button>
    </div>
  );
}

/**
 * A new catch at a point the user chose on the map. The catch photo comes
 * first: the server says what fish it shows (backend services/fish_id.py),
 * fills in the species, and refuses a species the photo contradicts, here
 * before saving and again when saving. Photos upload with the pin in one
 * request, with a progress bar.
 */
/** Metres between two points; enough to tell "here" from "somewhere else". */
function metresApart(a: { latitude: number; longitude: number }, b: { latitude: number; longitude: number }): number {
  const k = Math.PI / 180;
  const x = (b.longitude - a.longitude) * k * Math.cos(((a.latitude + b.latitude) / 2) * k);
  const y = (b.latitude - a.latitude) * k;
  return Math.hypot(x, y) * 6_371_000;
}

export function PinForm({
  point,
  onCreated,
  onCancel,
  onMove,
}: {
  point: { latitude: number; longitude: number };
  onCreated: (pin: PinDetail) => void;
  onCancel: () => void;
  // Moves the pin (MapView's draft), e.g. to where the photo was taken.
  onMove?: (latitude: number, longitude: number) => void;
}) {
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [title, setTitle] = useState("");
  const [species, setSpecies] = useState("");
  const [other, setOther] = useState("");
  const [caughtOn, setCaughtOn] = useState(today());
  const [note, setNote] = useState("");
  const [visibility, setVisibility] = useState<PinVisibility>("public");
  const [photos, setPhotos] = useState<File[]>([]);
  const [check, setCheck] = useState<Check | null>(null);
  // Where the catch photo says it was taken, when that isn't where the pin is.
  const [photoSpot, setPhotoSpot] = useState<{ latitude: number; longitude: number } | null>(null);
  const datePicked = useRef(false);
  const catchPhoto = useRef<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Only the newest check's answer is shown; the species is filled in from
  // the photo until the angler picks one themselves.
  const checkId = useRef(0);
  const picked = useRef(false);
  const typing = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    getPinOptions()
      .then(setOptions)
      .catch(() => setError("Couldn't load the species list. Is the backend running?"));
    return () => {
      if (typing.current) clearTimeout(typing.current);
    };
  }, []);

  async function runCheck(photo: File | undefined, sp: string, oth: string) {
    const id = ++checkId.current;
    if (!photo) {
      setCheck(null);
      return;
    }
    const claim = sp === OTHER ? (oth.trim() ? { species_other: oth.trim() } : null) : sp ? { species_slug: sp } : {};
    if (claim === null) {
      setCheck(null); // "Other" with no name yet
      return;
    }
    setCheck({ state: "checking" });
    try {
      let result = await identifyFish(photo, claim);
      if (id !== checkId.current) return;
      if (!result.available) {
        setCheck({ state: "off" });
        return;
      }
      const top = result.candidates[0];
      if (!sp && !picked.current && top?.in_guides && top.probability >= SUGGEST_FROM) {
        setSpecies(top.slug);
        result = await identifyFish(photo, { species_slug: top.slug });
        if (id !== checkId.current) return;
      }
      setCheck({ state: "done", result });
    } catch (err) {
      if (id === checkId.current) {
        setCheck({ state: "error", message: err instanceof ApiError ? err.message : "Couldn't check the photo. Try again." });
      }
    }
  }

  function changePhotos(next: File[]) {
    const firstChanged = next[0] !== photos[0];
    setPhotos(next);
    if (!firstChanged) return;
    // A new catch photo: suggest its fish again unless the angler chose one.
    const sp = picked.current ? species : "";
    if (!picked.current) setSpecies("");
    void runCheck(next[0], sp, other);
    setPhotoSpot(null);
    catchPhoto.current = null;
    if (next[0]) void fillFromPhoto(next[0]);
  }

  /** The photo's own date and place (EXIF), read on this device only. */
  async function fillFromPhoto(photo: File) {
    catchPhoto.current = photo;
    const facts = await readPhotoFacts(photo);
    if (catchPhoto.current !== photo) return; // swapped for another meanwhile
    if (facts.takenOn && facts.takenOn <= today() && !datePicked.current) setCaughtOn(facts.takenOn);
    if (facts.latitude !== null && facts.longitude !== null) {
      const spot = { latitude: facts.latitude, longitude: facts.longitude };
      if (metresApart(spot, point) > 150) setPhotoSpot(spot);
    }
  }

  function changeSpecies(sp: string, oth = other) {
    // Even "Not sure" is the angler's choice: the photo no longer overrides it.
    picked.current = true;
    setSpecies(sp);
    setOther(oth);
    void runCheck(photos[0], sp, oth);
  }

  function changeOther(oth: string) {
    setOther(oth);
    if (typing.current) clearTimeout(typing.current);
    typing.current = setTimeout(() => void runCheck(photos[0], OTHER, oth), 600);
  }

  const busy = progress !== null;
  const speciesLabel = species === OTHER ? other.trim() : (options?.species.find((s) => s.slug === species)?.label ?? "");
  const named = species !== "" && (species !== OTHER || other.trim() !== "");
  const verdict = check?.state === "done" ? check.result.verdict : null;
  // A named fish needs its photo, and a photo that backs it. The server
  // checks again on save, so a failed early check (network) doesn't block.
  const blocked =
    named && check?.state !== "off" && (photos.length === 0 || check?.state === "checking" || (verdict !== null && !verdict.accepted));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setProgress(0);
    try {
      const pin = await createPin(
        {
          ...point,
          title: title.trim() || speciesLabel || "Catch",
          note: note.trim() || undefined,
          species_slug: species && species !== OTHER ? species : undefined,
          species_other: species === OTHER ? other : undefined,
          caught_on: caughtOn || undefined,
          visibility,
          photos,
        },
        setProgress,
      );
      onCreated(pin);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save the catch. Try again.");
      setProgress(null);
    }
  }

  return (
    <form className="pin-form" onSubmit={submit}>
      <header className="pin-form-head">
        <h2>Share a catch</h2>
        <p className="muted">
          {point.latitude.toFixed(5)}, {point.longitude.toFixed(5)} · drag the pin on the map to adjust
        </p>
      </header>

      <div className="field">
        <span>Photo of the fish</span>
        <PhotoPicker
          files={photos}
          onChange={changePhotos}
          max={options?.max_photos ?? 4}
          maxMb={options?.max_photo_mb ?? 10}
          disabled={busy}
          firstLabel="Catch photo"
        />
        <FishCheckNote
          check={check}
          onPick={(slug) => changeSpecies(slug, "")}
          onPickOther={(name) => changeSpecies(OTHER, name)}
        />
        {photoSpot && onMove && (
          <p className="hint photo-spot">
            This photo was taken somewhere else.{" "}
            <button
              type="button"
              className="text-link"
              onClick={() => {
                onMove(photoSpot.latitude, photoSpot.longitude);
                setPhotoSpot(null);
              }}
            >
              Move the pin there
            </button>
          </p>
        )}
      </div>

      <div className="field-row">
        <label className="field">
          <span>Fish</span>
          <select value={species} onChange={(e) => changeSpecies(e.target.value)} disabled={busy}>
            <option value="">Not sure / none</option>
            {options?.species.map((s) => (
              <option key={s.slug} value={s.slug}>
                {s.label}
              </option>
            ))}
            <option value={OTHER}>Other…</option>
          </select>
        </label>
        <label className="field">
          <span>Date</span>
          <input
            type="date"
            value={caughtOn}
            max={today()}
            onChange={(e) => {
              datePicked.current = true;
              setCaughtOn(e.target.value);
            }}
            disabled={busy}
          />
        </label>
      </div>
      {species === OTHER && (
        <label className="field">
          <span>Which fish?</span>
          <input value={other} onChange={(e) => changeOther(e.target.value)} maxLength={60} disabled={busy} />
        </label>
      )}
      {named && photos.length === 0 && (
        <p className="hint">Add a photo of the fish: FishEye checks that it shows the fish you name.</p>
      )}

      <label className="field">
        <span>Title</span>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={speciesLabel ? `Optional · “${speciesLabel}” if empty` : "e.g. Rocks by the boat ramp"}
          maxLength={80}
          disabled={busy}
        />
      </label>

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

      {visibility === "public" && (
        <p className="hint">
          Public catches go live right away. Other anglers can report one that breaks the rules; a moderator reviews it.
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
          <small>{(progress ?? 0) < 1 ? `Uploading ${Math.round((progress ?? 0) * 100)}%` : "Checking and saving…"}</small>
        </div>
      )}

      <div className="form-actions">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button
          type="submit"
          className="btn btn-primary btn-sm"
          disabled={busy || blocked || (!named && title.trim().length < 3 && photos.length === 0)}
        >
          {busy ? "Saving…" : "Share catch"}
        </button>
      </div>
    </form>
  );
}
