"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { FishArt } from "@/components/fish/FishArt";
import { useLocale, useT } from "@/i18n/client";
import type { Locale } from "@/i18n/config";
import type { Messages } from "@/i18n/messages";
import { localFishName, localStateName, localTopicTitle } from "@/i18n/names";
import { ApiError, postAsk } from "@/lib/api/client";
import { postAskSummary } from "@/lib/api/session";
import { waterFor } from "@/lib/fishArt";
import { useJurisdictions, useSelectedState } from "@/lib/jurisdiction";
import { StatePicker } from "@/components/ui/StatePicker";
import type { AiAllowance, AskCitation, AskResponse } from "@/lib/api/types";

/**
 * Q&A over the fish guides (backend services/rag/ask.py), in two steps
 * (docs/adr/0023):
 *
 * 1. Every question searches the guides and shows the passages that answer
 *    it, with their sources. No model, no account, no cost.
 * 2. Under that, a signed-in person can ask for an AI summary of those
 *    passages, a few times a day. Signed out, the same spot says how to get
 *    them. A question the guides don't cover never offers one.
 *
 * The UI's job is to make the answer's provenance obvious at a glance:
 * - a badge says whether this is a model's answer, a quote of the guides
 *   (the model's answer was unavailable or rejected), or "not covered";
 * - every cited passage is a card that links to the exact spot in the guide.
 *
 * How the answer was found (retrieval scores, the model, its tokens and cost,
 * the checks it passed, the trace id) is for developers: it stays in the API
 * response and the server's logs, and none of it is shown here.
 *
 * History lives in component state only: a conversation here is scratch
 * work, not something to persist.
 */

type Summary =
  | { status: "loading" }
  | { status: "done"; response: AskResponse }
  | { status: "error"; message: string };

type Turn =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "assistant"; response: AskResponse; summary?: Summary }
  | { id: number; role: "error"; question: string; message?: string };

const MAX_LEN = 300;

function citationHref(c: AskCitation): string {
  if (!c.species_slug || c.species_slug === "all-fish") return `/fish#${c.section}`;
  return `/fish/${c.species_slug}#${c.section}`;
}

function SourceBadge({ r }: { r: AskResponse }) {
  const t = useT().ask;
  if (r.answer_source === "passages") {
    return <span className="badge badge-ok">{t.fromGuides}</span>;
  }
  if (r.answer_source === "no_match") {
    // Three different reasons for an empty answer (backend ADR 0026).
    const label =
      r.trace.outcome === "off_topic"
        ? t.offTopic
        : r.trace.outcome === "unguided_fish"
          ? t.unguided
          : r.trace.outcome === "other_state"
            ? t.otherState
            : t.notInGuides;
    return <span className="badge badge-muted">{label}</span>;
  }
  if (r.answer_source === "fallback") {
    return (
      <span className="badge badge-warn" title={t.fallbackTitle}>
        {t.fallback}
      </span>
    );
  }
  if (r.trace.provider === "mock") {
    return (
      <span className="badge badge-info" title={t.demoTitle}>
        {t.demo}
      </span>
    );
  }
  return <span className="badge badge-ok">{t.aiChecked}</span>;
}

/** A state's agency's own pages, so the answer ends in the rules rather than
 * in "check elsewhere": under a rules question FishEye hasn't written up for
 * that state, and under any fishing question the guides couldn't answer for a
 * state whose rules FishEye hasn't written at all. "The walleye limit in
 * Minnesota" found no walleye guide and said only that (2026-10-29 review). */
function StateRulesLinks({ r }: { r: AskResponse }) {
  const states = useJurisdictions();
  const t = useT().ask;
  if (!r.state || r.answer_source !== "no_match" || r.trace.outcome === "off_topic") return null;
  const j = states?.find((x) => x.code === r.state);
  if (!j || (r.trace.outcome !== "other_state" && j.covered)) return null;
  if (!j.limits_url && !j.license_url) return null;
  return (
    <p className="state-rules-links">
      <strong>{j.agency ?? j.name}:</strong>{" "}
      {j.limits_url && (
        <a href={j.limits_url} target="_blank" rel="noreferrer">
          {t.regulations}
        </a>
      )}
      {j.limits_url && j.license_url && " · "}
      {j.license_url && (
        <a href={j.license_url} target="_blank" rel="noreferrer">
          {t.licenses}
        </a>
      )}
    </p>
  );
}

/** A quoted passage's heading in the reader's language: a guide's own
 * sections (backend rag/chunking.py) and the Handbook's titles are
 * translated; anything else (a state's bait rules) keeps the guide's
 * English, as the passage itself does. */
export function citationTitle(c: Pick<AskCitation, "section" | "title">, f: Messages["fish"], locale: Locale): string {
  if (locale === "en") return c.title;
  const sections: Record<string, string> = {
    overview: f.tabOverview, diet: f.whatItEats, identification: f.recognise, habitat: f.habitat, habits: f.habits,
    where_and_when: f.whereWhen, live_baits: f.liveBait, lures: f.lures, why_these_baits: f.whyBaits,
    how_to_get: f.howToGet, bait_for: f.baitFor, tips: f.tips, eating: f.eating,
  };
  if (sections[c.section]) return sections[c.section];
  if (c.section.startsWith("setup-")) {
    // "Rod and reel setup — Cane pole": the setup's name is the guide's.
    const name = c.title.split(" — ")[1];
    return name ? `${f.setups} — ${name}` : f.setups;
  }
  return localTopicTitle(c.section, locale) ?? c.title;
}

function Citations({ items, compact }: { items: AskCitation[]; compact: boolean }) {
  const states = useJurisdictions();
  const all = useT();
  const t = all.ask;
  const locale = useLocale();
  const [showAll, setShowAll] = useState(false);
  if (items.length === 0) return null;
  const shown = showAll ? items : items.slice(0, 2);
  return (
    <div className="citations">
      <p className="citations-label">{t.sources}</p>
      <ul>
        {shown.map((c, i) => {
          const fish = c.species_slug !== "all-fish" ? c.species_slug : null;
          return (
            <li key={c.id} className="citation" style={{ "--i": i } as React.CSSProperties}>
              <Link href={citationHref(c)} className="citation-link" transitionTypes={compact ? undefined : ["nav-forward"]}>
                {fish && !compact && (
                  <span
                    className="citation-art"
                    style={{ "--wa": waterFor(fish)[0], "--wb": waterFor(fish)[1] } as React.CSSProperties}
                  >
                    <FishArt slug={fish} uid={`cite-${c.id.replace(/[^a-z0-9-]/g, "-")}-${i}`} />
                  </span>
                )}
                <span className="citation-body">
                  <span className="citation-title">
                    {c.species_name ? `${(fish && localFishName(fish, locale)) || c.species_name} · ` : ""}
                    {citationTitle(c, all.fish, locale)}
                    {c.region !== "all" && (
                      <span className="badge badge-muted citation-region">
                        {t.stateRules(localStateName(c.region, states?.find((j) => j.code === c.region)?.name ?? c.region, locale))}
                      </span>
                    )}
                  </span>
                  <span className="citation-excerpt" lang="en">{c.excerpt}</span>
                  {c.sources[0] && <span className="citation-source">{c.sources[0].label}</span>}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
      {items.length > 2 && <button type="button" className="sources-expand" aria-expanded={showAll} onClick={() => setShowAll((value) => !value)}>{showAll ? t.fewerSources : t.moreSources(items.length - 2)}</button>}
    </div>
  );
}

/** The AI-summary spot under a search result: a button, a sign-in prompt,
 * an "all used today" note, or the summary itself. */
function AiSummary({
  summary,
  ai,
  onRequest,
  loginHref,
  disabled,
}: {
  summary?: Summary;
  ai: AiAllowance | null;
  onRequest: () => void;
  loginHref: string;
  disabled: boolean;
}) {
  const t = useT().ask;
  if (summary?.status === "done") {
    const r = summary.response;
    return (
      <div className="ai-summary">
        <div className="bubble-meta">
          <SourceBadge r={r} />
        </div>
        <div className="answer-text">
          {r.answer.split("\n\n").map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>
      </div>
    );
  }
  if (summary?.status === "loading") {
    return (
      <div className="ai-summary ai-summary-cta" aria-live="polite">
        <span className="muted">{t.summarizing}</span>
      </div>
    );
  }
  const error = summary?.status === "error" ? <p className="ai-summary-error">{summary.message}</p> : null;
  if (ai && !ai.signed_in) {
    return (
      <div className="ai-summary ai-summary-cta">
        {error}
        <p className="muted">
          {t.signInBefore}<Link href={loginHref}>{t.signInLink}</Link>{t.signInFor}
        </p>
      </div>
    );
  }
  if (ai && ai.remaining === 0) {
    return (
      <div className="ai-summary ai-summary-cta">
        {error}
        <p className="muted">{t.usedToday}</p>
      </div>
    );
  }
  return (
    <div className="ai-summary ai-summary-cta">
      {error}
      <button type="button" className="btn btn-ghost btn-sm" onClick={onRequest} disabled={disabled}>
        {t.summarize(ai?.remaining ?? null)}
      </button>
    </div>
  );
}

function Thinking() {
  const t = useT().ask;
  return (
    <div className="msg msg-assistant msg-thinking" aria-live="polite">
      <span className="avatar" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element -- tiny static SVG mark, nothing to optimize */}
        <img src="/brand/fisheye-mark.svg" alt="" />
      </span>
      <div className="bubble-card">
        <span className="sr-only">{t.lookingThrough}</span>
        <span className="typing" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        <span className="thinking-text">{t.searching}</span>
      </div>
    </div>
  );
}

export function AskChat({
  compact = false,
  speciesSlug,
  speciesName,
  initialQuestion,
  suggestions,
}: {
  compact?: boolean;
  speciesSlug?: string;
  speciesName?: string;
  initialQuestion?: string;
  suggestions: string[];
}) {
  const all = useT();
  const t = all.ask;
  const locale = useLocale();
  const fishName = speciesSlug && speciesName ? (localFishName(speciesSlug, locale) ?? speciesName) : speciesName;
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  // How many AI summaries are left, as the server last said (every reply
  // carries it). Null until the first reply.
  const [ai, setAi] = useState<AiAllowance | null>(null);
  const state = useSelectedState();
  const pathname = usePathname();
  const loginHref = `/login?next=${encodeURIComponent(pathname ?? "/ask")}`;
  const nextId = useRef(1);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const asked = useRef(false);

  const ask = useCallback(
    async (question: string) => {
      const q = question.trim().slice(0, MAX_LEN);
      if (q.length < 3 || busy) return;
      setTurns((t) => [...t, { id: nextId.current++, role: "user", text: q }]);
      setInput("");
      setBusy(true);
      try {
        const response = await postAsk({ question: q, species_slug: speciesSlug ?? null, state, lang: locale });
        setAi(response.ai);
        setTurns((t) => [...t, { id: nextId.current++, role: "assistant", response }]);
      } catch (e) {
        // A request limit has its own message; anything else means the
        // server couldn't be reached.
        const message = e instanceof ApiError && e.code === "rate_limited" ? e.message : undefined;
        setTurns((t) => [...t, { id: nextId.current++, role: "error", question: q, message }]);
      } finally {
        setBusy(false);
      }
    },
    [busy, speciesSlug, state, locale],
  );

  const summarize = useCallback(
    async (turnId: number, question: string) => {
      const setSummary = (summary: Summary) =>
        setTurns((ts) => ts.map((t) => (t.id === turnId && t.role === "assistant" ? { ...t, summary } : t)));
      setSummary({ status: "loading" });
      try {
        const response = await postAskSummary({ question, species_slug: speciesSlug ?? null, state, lang: locale });
        setAi(response.ai);
        setSummary({ status: "done", response });
      } catch (e) {
        const message = e instanceof ApiError ? e.message : t.serverDown;
        if (e instanceof ApiError && e.status === 429) setAi((a) => (a ? { ...a, remaining: 0 } : a));
        if (e instanceof ApiError && e.status === 401) setAi({ signed_in: false, limit: null, remaining: null });
        setSummary({ status: "error", message });
      }
    },
    [speciesSlug, state, locale, t.serverDown],
  );

  useEffect(() => {
    if (initialQuestion && !asked.current) {
      asked.current = true;
      void ask(initialQuestion);
    }
  }, [initialQuestion, ask]);

  useEffect(() => {
    if (turns.length === 0 && !busy) return;
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    endRef.current?.previousElementSibling?.scrollIntoView?.({ behavior: reduced ? "instant" : "smooth", block: compact ? "nearest" : "start" });
  }, [turns, busy, compact]);

  // Grow the textarea with its content, up to a few lines.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [input]);

  const empty = turns.length === 0 && !busy;

  return (
    <div className={compact ? "ask ask-compact" : "ask"}>
      {compact && (
        <div className="ask-compact-head">
          <h2>{t.askAbout(fishName ?? "")}</h2>
          <p className="muted">{t.fishNote}</p>
        </div>
      )}

      <div className="ask-thread" aria-live="polite">
        {empty && (
          <div className="ask-empty">
            {!compact && (
              <p className="muted">{t.tryThese}</p>
            )}
            <div className="chip-row">
              {suggestions.map((s, i) => (
                <button
                  key={s}
                  type="button"
                  className="chip chip-lg reveal"
                  style={{ "--i": i } as React.CSSProperties}
                  onClick={() => ask(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn) => {
          if (turn.role === "user") {
            return (
              <div key={turn.id} className="msg msg-user">
                <div className="bubble-user">{turn.text}</div>
              </div>
            );
          }
          if (turn.role === "error") {
            return (
              <div key={turn.id} className="msg msg-assistant">
                <span className="avatar" aria-hidden="true">
                  {/* eslint-disable-next-line @next/next/no-img-element -- tiny static SVG mark, nothing to optimize */}
        <img src="/brand/fisheye-mark.svg" alt="" />
                </span>
                <div className="bubble-card bubble-error">
                  <p>{turn.message ?? t.unable}</p>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => ask(turn.question)} disabled={busy}>
                    {all.common.tryAgain}
                  </button>
                </div>
              </div>
            );
          }
          const r = turn.response;
          return (
            <div key={turn.id} className="msg msg-assistant">
              <span className="avatar" aria-hidden="true">
                {/* eslint-disable-next-line @next/next/no-img-element -- tiny static SVG mark, nothing to optimize */}
        <img src="/brand/fisheye-mark.svg" alt="" />
              </span>
              <div className="bubble-card">
                <div className="bubble-meta">
                  <SourceBadge r={r} />
                </div>
                <div className="answer-text" lang={r.answer_source === "passages" ? "en" : undefined}>
      {r.answer.split("\n\n").map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
                <StateRulesLinks r={r} />
                <Citations items={r.citations} compact={compact} />
                {r.answer_source === "passages" && (
                  <AiSummary
                    summary={turn.summary}
                    ai={ai}
                    loginHref={loginHref}
                    disabled={turn.summary?.status === "loading"}
                    onRequest={() => void summarize(turn.id, r.question)}
                  />
                )}
              </div>
            </div>
          );
        })}

        {busy && <Thinking />}
        <div ref={endRef} />
      </div>

      <div className="ask-composer">
      {!compact && <StatePicker className="state-picker state-picker-ask" label={t.rulesFor} />}
      <form
        className="ask-form"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(input);
        }}
      >
        <textarea
          ref={inputRef}
          rows={1}
          value={input}
          maxLength={MAX_LEN}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.nativeEvent.isComposing || e.keyCode === 229) return;
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask(input);
            }
          }}
          placeholder={fishName ? t.placeholderFish(fishName) : t.placeholder}
          aria-label={t.yourQuestion}
        />
        <button type="submit" className="send-btn" disabled={busy || input.trim().length < 3} aria-label={t.send}>
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path d="M4 12l16-8-6 16-2.5-6.5L4 12z" fill="currentColor" />
          </svg>
        </button>
      </form>
      </div>
      {input.length > MAX_LEN - 60 && (
        <p className="char-count muted">
          {input.length}/{MAX_LEN}
        </p>
      )}
    </div>
  );
}
