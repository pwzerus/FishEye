"use client";

import { useEffect, useRef, useState } from "react";

import { useLocale, useT } from "@/i18n/client";
import { MESSAGES, type Messages } from "@/i18n/messages";
import { localFishName } from "@/i18n/names";
import { ApiError } from "@/lib/api/client";
import { createPin, getPinOptions, identifyFish } from "@/lib/api/session";
import type { FishIdResult, FishVerdict, PinDetail, PinOptions, PinVisibility } from "@/lib/api/types";
import { readPhotoFacts } from "@/lib/exif";
import { PhotoPicker } from "./PhotoPicker";

function today(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

/** What the map knows about the water under the pin being placed (backend
 * ADR 0040, /api/pins/where). */
export type DraftWater =
  | { state: "checking" }
  | { state: "on"; name: string; kind: "lake" | "river" }
  // `required`: the state holds catches to named water, so this one can't be saved.
  | { state: "off"; required: boolean }
  | { state: "unknown" };

/** The guide species as <option>s, named in the chosen language. */
export function SpeciesOptions({
  options,
  otherValue,
  allLabel,
}: {
  options: PinOptions | null;
  // "" to leave "Other…" out (a filter, not a form).
  otherValue: string;
  // A filter's first option ("All fish") instead of "Not sure / none".
  allLabel?: string;
}) {
  const t = useT().catch;
  const locale = useLocale();
  const species = (options?.species ?? [])
    .map((s) => ({ slug: s.slug, label: localFishName(s.slug, locale) ?? s.label, english: s.label }))
    .sort((a, b) => a.label.localeCompare(b.label, locale));
  return (
    <>
      <option value="">{allLabel ?? t.notSure}</option>
      {species.map((s) => (
        <option key={s.slug} value={s.slug}>
          {s.label === s.english ? s.label : `${s.label} · ${s.english}`}
        </option>
      ))}
      {otherValue && <option value={otherValue}>{t.other}</option>}
    </>
  );
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
  const t = useT().catch;
  return (
    <div className="vis-toggle" role="radiogroup" aria-label={t.whoSeesLabel}>
      {(
        [
          ["public", t.visPublic, t.visPublicSub],
          ["private", t.visPrivate, t.visPrivateSub],
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

/** Whether other anglers see the exact spot of a public catch (backend ADR
 * 0038). Off by default: they see its lake or river, never the spot. */
export function ShareSpotToggle({
  value,
  onChange,
  disabled,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  const t = useT().catch;
  return (
    <label className="check-row share-spot">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)} disabled={disabled} />
      <span>
        {t.shareSpot}
        <small className="muted">{t.shareSpotSub}</small>
      </span>
    </label>
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

/** The photo check's verdict in the chosen language. The server writes it
 * in English (backend services/fish_id.check_claim); other languages say the
 * same from its status and the fish involved. */
function verdictText(t: Messages, v: FishVerdict, claimed: string | null, name: (slug: string, english: string) => string): string {
  const seen = v.detected && v.detected_label ? name(v.detected, v.detected_label) : (v.detected_label ?? "");
  switch (v.status) {
    case "no_fish":
      return t.catch.verdictNoFish;
    case "confirmed":
      return claimed ? t.catch.verdictConfirmed(claimed) : t.catch.verdictAnyFish;
    case "group":
      return t.catch.verdictGroup(claimed ?? seen);
    case "other_fish":
      return t.catch.verdictNotListed(seen, claimed ?? "");
    case "mismatch":
      return claimed ? t.catch.verdictMismatch(seen, claimed) : t.catch.verdictPickInstead(seen);
    default:
      return t.catch.verdictUnsure(claimed ?? seen);
  }
}

/** What the photo check said, under the catch photo. */
export function FishCheckNote({
  check,
  claimed,
  onPick,
  onPickOther,
}: {
  check: Check | null;
  // The fish the angler named, in the chosen language.
  claimed: string | null;
  onPick: (slug: string) => void;
  onPickOther: (name: string) => void;
}) {
  const all = useT();
  const t = all.catch;
  const locale = useLocale();
  const name = (slug: string, english: string) => localFishName(slug, locale) ?? english;
  if (!check || check.state === "off") return null;
  if (check.state === "checking") {
    return (
      <p className="fish-check is-checking" role="status">
        <span className="fish-check-spinner" aria-hidden="true" /> {t.checking}
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
        <span>{t.looksLike}</span>
        {fish.map((c) =>
          c.in_guides ? (
            <button key={c.slug} type="button" className="chip fish-check-chip" onClick={() => onPick(c.slug)}>
              {name(c.slug, c.label)} <small>{percent(c.probability)}</small>
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
  const message = locale === "en" ? verdict.message : verdictText(all, verdict, claimed, name);
  if (verdict.accepted) {
    return (
      <p className={verdict.status === "confirmed" ? "fish-check is-ok" : "fish-check is-group"} role="status">
        <span aria-hidden="true">✓ </span>
        {message}
      </p>
    );
  }
  const seen = verdict.detected && verdict.detected_label ? name(verdict.detected, verdict.detected_label) : null;
  return (
    <div className="fish-check is-bad" role="alert">
      <p>{message}</p>
      {verdict.detected && seen && verdict.detected_in_guides && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onPick(verdict.detected!)}>
          {t.changeTo(seen)}
        </button>
      )}
      {verdict.status === "other_fish" && verdict.detected_label && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onPickOther(verdict.detected_label!)}>
          {t.chooseOther(verdict.detected_label)}
        </button>
      )}
      {/* Never a dead end: the catch can still go up, with no fish named. */}
      <button type="button" className="text-link fish-check-skip" onClick={() => onPick("")}>
        {t.shareWithout}
      </button>
    </div>
  );
}

/** Metres between two points; enough to tell "here" from "somewhere else". */
function metresApart(a: { latitude: number; longitude: number }, b: { latitude: number; longitude: number }): number {
  const k = Math.PI / 180;
  const x = (b.longitude - a.longitude) * k * Math.cos(((a.latitude + b.latitude) / 2) * k);
  const y = (b.latitude - a.latitude) * k;
  return Math.hypot(x, y) * 6_371_000;
}

/** Where the pin is, in the form's header: the water it's on, or a plain
 * "move it onto the water" with a way to report water the map lacks. */
export function WaterLine({ water, onMissingWater }: { water: DraftWater; onMissingWater?: () => void }) {
  const t = useT().catch;
  if (water.state === "on") {
    return (
      <p className="pin-water-line">
        <strong>{t.at(water.name)}</strong> <span className="muted">· {t.dragToAdjust}</span>
      </p>
    );
  }
  if (water.state === "off" && water.required) {
    return (
      <div className="pin-water-line is-off" role="alert">
        <p>{t.notOnWater}</p>
        {onMissingWater && (
          <button type="button" className="text-link" onClick={onMissingWater}>
            {t.missingWater}
          </button>
        )}
      </div>
    );
  }
  if (water.state === "checking") return <p className="pin-water-line muted">{t.chipChecking}</p>;
  return <p className="pin-water-line muted">{t.dragToAdjust}</p>;
}

/**
 * A new catch at a point the user chose on the map. The catch photo comes
 * first: the server says what fish it shows (backend services/fish_id.py),
 * fills in the species, and refuses a species the photo contradicts, here
 * before saving and again when saving. Photos upload with the pin in one
 * request, with a progress bar. The pin has to be on named water (ADR 0040):
 * `water` says whether it is.
 */
export function PinForm({
  point,
  water = { state: "unknown" },
  onCreated,
  onCancel,
  onMove,
  onMissingWater,
}: {
  point: { latitude: number; longitude: number };
  water?: DraftWater;
  onCreated: (pin: PinDetail) => void;
  onCancel: () => void;
  // Moves the pin (MapView's draft), e.g. to where the photo was taken.
  onMove?: (latitude: number, longitude: number) => void;
  // "Water not on the map? Tell us": a missing-lake report at the pin.
  onMissingWater?: () => void;
}) {
  const all = useT();
  const t = all.catch;
  const locale = useLocale();
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [title, setTitle] = useState("");
  const [species, setSpecies] = useState("");
  const [other, setOther] = useState("");
  const [caughtOn, setCaughtOn] = useState(today());
  const [note, setNote] = useState("");
  const [visibility, setVisibility] = useState<PinVisibility>("public");
  const [shareExact, setShareExact] = useState(false);
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
      .catch(() => setError(t.speciesError));
    return () => {
      if (typing.current) clearTimeout(typing.current);
    };
  }, [t.speciesError]);

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
        setCheck({ state: "error", message: err instanceof ApiError ? err.message : t.checkError });
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
  const englishLabel = options?.species.find((s) => s.slug === species)?.label ?? "";
  const speciesLabel = species === OTHER ? other.trim() : (localFishName(species, locale) ?? englishLabel);
  const named = species !== "" && (species !== OTHER || other.trim() !== "");
  const verdict = check?.state === "done" ? check.result.verdict : null;
  // A named fish needs its photo, and a photo that backs it. The server
  // checks again on save, so a failed early check (network) doesn't block.
  const blocked =
    named && check?.state !== "off" && (photos.length === 0 || check?.state === "checking" || (verdict !== null && !verdict.accepted));
  const offWater = (water.state === "off" && water.required) || water.state === "checking";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setProgress(0);
    try {
      const pin = await createPin(
        {
          ...point,
          // The title is stored as typed; with none, the fish's English name,
          // which every reader's language shows beside its own.
          title: title.trim() || englishLabel || other.trim() || MESSAGES.en.catch.catch,
          note: note.trim() || undefined,
          species_slug: species && species !== OTHER ? species : undefined,
          species_other: species === OTHER ? other : undefined,
          caught_on: caughtOn || undefined,
          visibility,
          share_exact: visibility === "public" && shareExact,
          photos,
        },
        setProgress,
      );
      onCreated(pin);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.saveError);
      setProgress(null);
    }
  }

  return (
    <form className="pin-form" onSubmit={submit}>
      <header className="pin-form-head">
        <h2>{t.shareTitle}</h2>
        <WaterLine water={water} onMissingWater={onMissingWater} />
      </header>

      <div className="field">
        <span>{t.photoLabel}</span>
        <PhotoPicker
          files={photos}
          onChange={changePhotos}
          max={options?.max_photos ?? 4}
          maxMb={options?.max_photo_mb ?? 10}
          disabled={busy}
          firstLabel={t.catchPhoto}
        />
        <FishCheckNote
          check={check}
          claimed={named ? speciesLabel : null}
          onPick={(slug) => changeSpecies(slug, "")}
          onPickOther={(name) => changeSpecies(OTHER, name)}
        />
        {photoSpot && onMove && (
          <p className="hint photo-spot">
            {t.photoElsewhere}{" "}
            <button
              type="button"
              className="text-link"
              onClick={() => {
                onMove(photoSpot.latitude, photoSpot.longitude);
                setPhotoSpot(null);
              }}
            >
              {t.movePinThere}
            </button>
          </p>
        )}
      </div>

      <div className="field-row">
        <label className="field">
          <span>{t.fish}</span>
          <select value={species} onChange={(e) => changeSpecies(e.target.value)} disabled={busy}>
            <SpeciesOptions options={options} otherValue={OTHER} />
          </select>
        </label>
        <label className="field">
          <span>{t.date}</span>
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
          <span>{t.whichFish}</span>
          <input value={other} onChange={(e) => changeOther(e.target.value)} maxLength={60} disabled={busy} />
        </label>
      )}
      {named && photos.length === 0 && <p className="hint">{t.needPhoto}</p>}

      <label className="field">
        <span>{t.title}</span>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={speciesLabel ? t.titleIfEmpty(speciesLabel) : t.titleExample}
          maxLength={80}
          disabled={busy}
        />
      </label>

      <label className="field">
        <span>{t.notes}</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          maxLength={1000}
          placeholder={t.notesExample}
          disabled={busy}
        />
      </label>

      <div className="field">
        <span>{t.whoSees}</span>
        <VisibilityToggle value={visibility} onChange={setVisibility} disabled={busy} />
      </div>

      {visibility === "public" && (
        <>
          <ShareSpotToggle value={shareExact} onChange={setShareExact} disabled={busy} />
          <p className="hint">{t.liveNote}</p>
        </>
      )}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {busy && (
        <div className="upload-progress" role="progressbar" aria-valuenow={Math.round((progress ?? 0) * 100)} aria-valuemin={0} aria-valuemax={100}>
          <span style={{ transform: `scaleX(${progress ?? 0})` }} />
          <small>{(progress ?? 0) < 1 ? t.uploading(Math.round((progress ?? 0) * 100)) : t.checkingSaving}</small>
        </div>
      )}

      <div className="form-actions">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel} disabled={busy}>
          {all.common.cancel}
        </button>
        <button
          type="submit"
          className="btn btn-primary btn-sm"
          disabled={busy || blocked || offWater || (!named && title.trim().length < 3 && photos.length === 0)}
        >
          {busy ? all.common.saving : t.submit}
        </button>
      </div>
    </form>
  );
}
