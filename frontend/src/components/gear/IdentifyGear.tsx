"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useLocale, useT } from "@/i18n/client";
import { localGearName } from "@/i18n/names";
import { ApiError } from "@/lib/api/client";
import { identifyGear } from "@/lib/api/session";
import { sized } from "@/lib/photoSizes";
import type { GearCandidate, GearIdResult, GearItem } from "@/lib/api/types";

type State =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "done"; result: GearIdResult }
  | { kind: "error"; message: string };

const percent = (p: number) => `${Math.round(p * 100)}%`;
// The camera's own threshold (backend services/gear_id.Policy.min_gear): at
// or above it with nothing offered, it is gear too unclear to name.
const MIN_GEAR = 0.5;

/** "What is this?" for a piece of gear, from one photo (backend
 * /api/gear/identify, ADR 0048): the likeliest items of this page, each with
 * its photo to compare and a link down to its card. The photo is read on
 * FishEye's server and not kept. */
export function IdentifyGear({ items }: { items: GearItem[] }) {
  const { user } = useAuth();
  const all = useT();
  const t = all.gearPage.camera;
  const [state, setState] = useState<State>({ kind: "idle" });
  // Signed out, the day's free photos are used up (backend api/gear._allow).
  const [trialUsed, setTrialUsed] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const latest = useRef(0);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  async function check(file: File | undefined) {
    if (!file) return;
    const id = ++latest.current;
    setPreview(URL.createObjectURL(file));
    setState({ kind: "checking" });
    try {
      const result = await identifyGear(file);
      if (id === latest.current) setState({ kind: "done", result });
    } catch (err) {
      if (id !== latest.current) return;
      if (!user && err instanceof ApiError && err.status === 429) {
        setTrialUsed(true);
        setState({ kind: "idle" });
        return;
      }
      setState({ kind: "error", message: err instanceof ApiError ? err.message : t.failed });
    }
  }

  return (
    <section className="gear-camera" aria-labelledby="gear-camera-title">
      <h2 id="gear-camera-title">{t.title}</h2>
      <p className="muted">{t.lede}</p>
      {!user && trialUsed ? (
        <div className="identify-card">
          <p>{t.trialUsed}</p>
          <div className="identify-actions">
            <Link href="/login?mode=signup&next=/gear" className="btn btn-primary">
              {all.identify.createFree}
            </Link>
            <Link href="/login?next=/gear" className="btn btn-ghost">
              {all.common.signIn}
            </Link>
          </div>
        </div>
      ) : (
        <div className="identify-card">
          <input
            ref={input}
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            aria-label={t.pick}
            onChange={(e) => {
              void check(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            className="btn btn-primary identify-pick"
            disabled={state.kind === "checking"}
            onClick={() => input.current?.click()}
          >
            {state.kind === "idle" ? t.pick : t.another}
          </button>
          <p className="hint">{t.tip}</p>
          {!user && <p className="hint">{t.trialNote}</p>}
          {preview && (
            // A local preview of the user's own photo.
            // eslint-disable-next-line @next/next/no-img-element
            <img className="identify-preview" src={preview} alt={t.preview} />
          )}
          {state.kind === "checking" && (
            <p className="fish-check is-checking" role="status">
              <span className="fish-check-spinner" aria-hidden="true" /> {t.checking}
            </p>
          )}
          {state.kind === "error" && (
            <p className="form-error" role="alert">
              {state.message}
            </p>
          )}
          {state.kind === "done" && <GearIdAnswer result={state.result} items={items} />}
        </div>
      )}
    </section>
  );
}

/** What the camera found: one item named, or a few to compare, each with
 * this page's photo of it. */
export function GearIdAnswer({ result, items }: { result: GearIdResult; items: GearItem[] }) {
  const t = useT().gearPage.camera;
  const locale = useLocale();
  if (!result.available) {
    return (
      <p className="muted" role="status">
        {t.off}
      </p>
    );
  }
  if (result.candidates.length === 0) {
    return (
      <div className="identify-answer" role="status">
        <p className="identify-verdict">
          {result.not_gear === "fish" ? t.fish : (result.gear_probability ?? 0) >= MIN_GEAR ? t.unclear : t.notGear}
        </p>
        {result.not_gear === "fish" && (
          <p>
            <Link href="/identify" className="text-link">
              {t.nameFish}
            </Link>
          </p>
        )}
      </div>
    );
  }
  const byId = new Map(items.map((i) => [i.id, i]));
  const name = (c: GearCandidate) => localGearName(c.id, locale) ?? c.name;
  const row = (c: GearCandidate) => {
    const photo = byId.get(c.id)?.photo;
    return (
      <li key={c.id} className="gear-id-row">
        {photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img {...sized(photo.url, photo.width, "64px")} alt="" width={photo.width} height={photo.height} loading="lazy" />
        ) : (
          <span className="gear-id-nophoto" aria-hidden="true" />
        )}
        <span className="identify-name">
          <a href={`#${c.id}`}>{name(c)}</a>
        </span>
        <span className="identify-bar" aria-hidden="true">
          <span style={{ width: percent(c.probability) }} />
        </span>
        <span className="identify-pct">{percent(c.probability)}</span>
      </li>
    );
  };
  const [top, ...rest] = result.candidates;
  return (
    <div className="identify-answer" role="status">
      {result.sure ? (
        <>
          <p className="identify-verdict">
            {t.looksLike} <strong>{name(top)}</strong>
          </p>
          <ul className="identify-list gear-id-list">{row(top)}</ul>
          <p>
            <a href={`#${top.id}`} className="text-link">
              {t.seeIt}
            </a>
          </p>
          {rest.length > 0 && <ul className="identify-list gear-id-list is-quiet">{rest.map(row)}</ul>}
        </>
      ) : (
        <>
          <p className="identify-verdict">{t.couldBe}</p>
          <ul className="identify-list gear-id-list">{result.candidates.map(row)}</ul>
        </>
      )}
      <p className="hint">{t.caution}</p>
    </div>
  );
}
