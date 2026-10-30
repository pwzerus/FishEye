"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { LimitsNote } from "@/components/rules/RegionGate";
import { useLocale, useT } from "@/i18n/client";
import { localFishName } from "@/i18n/names";
import { ApiError } from "@/lib/api/client";
import { identifyFish } from "@/lib/api/session";
import type { FishIdResult } from "@/lib/api/types";

// The photo check's own thresholds (backend services/fish_id.Policy): below
// MIN_FISH the photo isn't of a fish; a species this sure is named outright.
const MIN_FISH = 0.5;
const SURE = 0.8;
// Smaller shares than this aren't worth showing as a possibility.
const SHOWN = 0.05;

type State =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "done"; result: FishIdResult }
  | { kind: "error"; message: string };

const percent = (p: number) => `${Math.round(p * 100)}%`;

/** "What fish is this?" from one photo (backend /api/fish-id, ADR 0037):
 * the same model as the catch check, on FishEye's own server. The photo is
 * read and thrown away; nothing is saved. */
export function IdentifyFish() {
  const { user, loading } = useAuth();
  const all = useT();
  const t = all.identify;
  const [state, setState] = useState<State>({ kind: "idle" });
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
      const result = await identifyFish(file);
      if (id === latest.current) setState({ kind: "done", result });
    } catch (err) {
      if (id === latest.current) {
        setState({ kind: "error", message: err instanceof ApiError ? err.message : t.checkFailed });
      }
    }
  }

  if (loading) return <div className="identify-card sk" style={{ height: 320 }} />;
  if (!user) {
    return (
      <div className="identify-card">
        <h2>{t.freeTitle}</h2>
        <p className="muted">{t.freeText}</p>
        <div className="identify-actions">
          <Link href="/login?mode=signup&next=/identify" className="btn btn-primary">
            {t.createFree}
          </Link>
          <Link href="/login?next=/identify" className="btn btn-ghost">
            {all.common.signIn}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="identify-card">
      <input
        ref={input}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        aria-label={t.photoLabel}
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
      {state.kind === "done" && <Answer result={state.result} />}
    </div>
  );
}

function Answer({ result }: { result: FishIdResult }) {
  const t = useT().identify;
  const locale = useLocale();
  const name = (slug: string, label: string) => localFishName(slug, locale) ?? label;
  if (!result.available) {
    return (
      <p className="muted" role="status">
        {t.off}
      </p>
    );
  }
  if ((result.fish_probability ?? 0) < MIN_FISH) {
    return (
      <p className="identify-verdict" role="status">
        {t.noFish}
      </p>
    );
  }
  const fish = result.candidates.filter((c) => c.probability >= SHOWN).slice(0, 3);
  const top = fish[0];
  if (!top) return null;
  const sure = top.probability >= SURE;
  return (
    <div className="identify-answer" role="status">
      <p className="identify-verdict">
        {sure ? (
          <>
            {t.looksLike}
            <strong>{name(top.slug, top.label)}</strong>
            {t.looksLikeEnd}
          </>
        ) : (
          t.notSure
        )}
      </p>
      <ul className="identify-list">
        {fish.map((c) => (
          <li key={c.slug}>
            <span className="identify-name">
              {c.in_guides ? <Link href={`/fish/${c.slug}`}>{name(c.slug, c.label)}</Link> : c.label}
            </span>
            <span className="identify-bar" aria-hidden="true">
              <span style={{ width: percent(c.probability) }} />
            </span>
            <span className="identify-pct">{percent(c.probability)}</span>
          </li>
        ))}
      </ul>
      {top.in_guides && (
        <p>
          <Link href={`/fish/${top.slug}`} className="text-link">
            {t.howTo(name(top.slug, top.label))}
          </Link>
        </p>
      )}
      <LimitsNote className="identify-rules muted" texasUrl="" />
      <p className="hint">{t.caution}</p>
    </div>
  );
}
