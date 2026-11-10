"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { LimitsNote } from "@/components/rules/RegionGate";
import { useLocale, useT } from "@/i18n/client";
import { localFishName } from "@/i18n/names";
import { ApiError } from "@/lib/api/client";
import { identifyFish } from "@/lib/api/session";
import type { FishCandidate, FishIdResult } from "@/lib/api/types";

// The photo check's own thresholds (backend services/fish_id.Policy): below
// MIN_FISH the photo isn't of a fish; a species this sure is named outright.
const MIN_FISH = 0.5;
const SURE = 0.8;
// Smaller shares than this aren't worth showing as a possibility.
const SHOWN = 0.1;
// Below this the likeliest fish doesn't stand out (a blurred or far-off fish,
// a photo of something else the model calls fish-like): it says it can't
// tell, rather than offer a 6% guess as "most likely".
const UNCLEAR = 0.2;
// Above this, the likeliest fish is named as the best guess, with the
// others under it, rather than a bare "not sure" list.
const LIKELY = 0.5;
// Its kind together (all the trout) this sure: named as that kind.
const KIND_SURE = 0.6;

type State =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "done"; result: FishIdResult }
  | { kind: "error"; message: string };

const percent = (p: number) => `${Math.round(p * 100)}%`;

/** The fish a photo shows clearly enough to talk about, if any: what Ask
 * offers to tell you more about (components/ask/AskChat.tsx). */
export function likelyFish(result: FishIdResult): FishCandidate | null {
  if (!result.available || (result.fish_probability ?? 0) < MIN_FISH) return null;
  const top = result.candidates[0];
  return top && top.probability >= UNCLEAR ? top : null;
}

/** "What fish is this?" from one photo (backend /api/fish-id, ADR 0037):
 * the same model as the catch check, on FishEye's own server. The photo is
 * read and thrown away; nothing is saved. */
export function IdentifyFish() {
  const { user, loading } = useAuth();
  const all = useT();
  const t = all.identify;
  const [state, setState] = useState<State>({ kind: "idle" });
  // Signed out, the day's free checks are used up (backend api/pins._trial).
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
      const result = await identifyFish(file);
      if (id === latest.current) setState({ kind: "done", result });
    } catch (err) {
      if (id !== latest.current) return;
      if (!user && err instanceof ApiError && err.status === 429) {
        setTrialUsed(true);
        setState({ kind: "idle" });
        return;
      }
      setState({ kind: "error", message: err instanceof ApiError ? err.message : t.checkFailed });
    }
  }

  if (loading) return <div className="identify-card sk" style={{ height: 320 }} />;
  if (!user && trialUsed) {
    return (
      <div className="identify-card">
        <p>{t.trialUsed}</p>
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
      <p className="hint">{t.oneFish}</p>
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
      {state.kind === "done" && <FishIdAnswer result={state.result} />}
    </div>
  );
}

/** What the photo check found, in words; also shown in Ask. */
export function FishIdAnswer({ result }: { result: FishIdResult }) {
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
  if (!top || top.probability < UNCLEAR) {
    return (
      <p className="identify-verdict" role="status">
        {t.unclear}
      </p>
    );
  }
  // One fish under two names (a steelhead is a rainbow trout) shares a
  // guide: together they can settle what the fish is.
  const sameFish = top.guide_slug
    ? result.candidates.filter((c) => c.guide_slug === top.guide_slug).reduce((sum, c) => sum + c.probability, 0)
    : top.probability;
  const sure = Math.max(top.probability, sameFish) >= SURE;
  const likely = !sure && top.probability >= LIKELY;
  // Not sure which fish, but sure what kind ("a trout"): say the kind, and
  // the likeliest of it.
  const kind = !sure && !likely && result.group && (result.group_probability ?? 0) >= KIND_SURE
    ? t.groupNames[result.group] ?? null
    : null;
  const named = sure || likely || Boolean(kind);
  const others = named ? fish.slice(1) : fish;
  const guide = top.guide_slug ?? (top.in_guides ? top.slug : null);
  const note = t.nameNotes[top.slug];
  const row = (c: FishCandidate) => {
    const target = c.guide_slug ?? (c.in_guides ? c.slug : null);
    return (
      <li key={c.slug}>
        <span className="identify-name">
          {target ? <Link href={`/fish/${target}`}>{name(c.slug, c.label)}</Link> : name(c.slug, c.label)}
        </span>
        <span className="identify-bar" aria-hidden="true">
          <span style={{ width: percent(c.probability) }} />
        </span>
        <span className="identify-pct">{percent(c.probability)}</span>
      </li>
    );
  };
  return (
    <div className="identify-answer" role="status">
      <p className="identify-verdict">
        {sure || likely ? (
          <>
            {sure ? t.looksLike : t.probably}
            <strong>{name(top.slug, top.label)}</strong>
            {sure ? t.looksLikeEnd : t.probablyEnd}
          </>
        ) : kind ? (
          <>
            {t.kindIs(kind)}
            <strong>{name(top.slug, top.label)}</strong>
            {t.kindIsEnd}
          </>
        ) : (
          t.notSure
        )}
      </p>
      {note && <p className="identify-note">{note}</p>}
      {named && <ul className="identify-list">{row(top)}</ul>}
      {others.length > 0 && (
        <>
          {named && <p className="hint">{t.couldAlso}</p>}
          <ul className="identify-list">{others.map(row)}</ul>
        </>
      )}
      {guide && (
        <p>
          <Link href={`/fish/${guide}`} className="text-link">
            {t.howTo(name(top.slug, top.label))}
          </Link>
        </p>
      )}
      <LimitsNote className="identify-rules muted" texasUrl="" />
      <p className="hint">{t.caution}</p>
    </div>
  );
}
