"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { FishArt } from "@/components/fish/FishArt";
import { ApiError, postAsk } from "@/lib/api/client";
import { postAskSummary } from "@/lib/api/session";
import { waterFor } from "@/lib/fishArt";
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
 * - every cited passage is a card that links to the exact spot in the guide;
 * - "How this answer was checked" opens the trace — what was retrieved and
 *   how it scored, what the model cost, and which checks it passed.
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
  if (r.answer_source === "passages") {
    return <span className="badge badge-ok">From the guides</span>;
  }
  if (r.answer_source === "no_match") {
    return <span className="badge badge-muted">Not in the guides</span>;
  }
  if (r.answer_source === "fallback") {
    return (
      <span className="badge badge-warn" title={`Model answer ${r.trace.outcome.replaceAll("_", " ")}`}>
        Straight from the guides
      </span>
    );
  }
  if (r.trace.provider === "mock") {
    return (
      <span className="badge badge-info" title="The demo model restates the retrieved passages; set LLM_PROVIDER=anthropic for a real one">
        Demo model
      </span>
    );
  }
  return <span className="badge badge-ok">AI answer · checked</span>;
}

const OUTCOME_TEXT: Record<string, string> = {
  ok: "Passed every check",
  no_match: "Nothing in the guides matched, so no model was called",
  invalid_json: "Model reply was malformed, so the guide text is shown",
  ungrounded_citation: "Model cited a passage it wasn't given, so its answer was discarded",
  ungrounded_species: "Model named a fish the passages don't mention, so its answer was discarded",
  ungrounded_number: "Model used a number the passages don't give, so its answer was discarded",
  url_in_answer: "Model wrote a link, so its answer was discarded",
  provider_unavailable: "Model unavailable, so the guide text is shown",
};

function Trace({ r }: { r: AskResponse }) {
  const t = r.trace;
  const searchOnly = r.answer_source === "passages";
  const max = Math.max(0.001, ...t.retrieved.map((x) => x.score));
  const cited = new Set(r.citations.map((c) => c.id));
  return (
    <details className="trace">
      <summary>How this answer was checked</summary>
      <ol className="trace-steps">
        <li>
          <span className="trace-step-title">1 · Retrieve</span>
          <span className="muted">
            {t.retriever.toUpperCase()} over the fish guides
            {t.routed_species.length > 0 && <> · routed to {t.routed_species.join(", ")}</>}
          </span>
          {t.retrieved.length > 0 ? (
            <ul className="trace-hits">
              {t.retrieved.map((h) => (
                <li key={h.id}>
                  <code>{h.id}</code>
                  <span className="score-bar" aria-hidden="true">
                    <span style={{ width: `${Math.max(6, (h.score / max) * 100)}%` }} />
                  </span>
                  <span className="score">{h.score.toFixed(2)}</span>
                  <span className="cited">{cited.has(h.id) ? "cited" : ""}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No passage matched.</p>
          )}
        </li>
        <li>
          <span className="trace-step-title">2 · Explain</span>
          <span className="muted">
            {searchOnly
              ? "No model: these are the guide's own words"
              : t.provider === "none"
              ? "Skipped"
              : `${t.provider} · ${t.model} · ${t.prompt_tokens + t.completion_tokens} tokens · ${t.latency_ms.toFixed(0)} ms · ~$${t.estimated_cost_usd.toFixed(5)}`}
            {t.cache_hit && " · cached"}
          </span>
        </li>
        <li>
          <span className="trace-step-title">3 · Check</span>
          {searchOnly ? (
            <span className="muted">Nothing to check: no model wrote anything</span>
          ) : (
            <span className={t.outcome === "ok" ? "check-ok" : "check-warn"}>
              {OUTCOME_TEXT[t.outcome] ?? t.outcome}
            </span>
          )}
          {t.validation_attempts > 1 && <span className="muted"> ({t.validation_attempts} attempts)</span>}
        </li>
      </ol>
      <p className="trace-id muted">trace {t.trace_id.slice(0, 8)}</p>
    </details>
  );
}

function Citations({ items, compact }: { items: AskCitation[]; compact: boolean }) {
  if (items.length === 0) return null;
  return (
    <div className="citations">
      <p className="citations-label">From the guide</p>
      <ul>
        {items.map((c, i) => {
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
                    {c.species_name ? `${c.species_name} · ` : ""}
                    {c.title}
                  </span>
                  <span className="citation-excerpt">{c.excerpt}</span>
                  {c.sources[0] && <span className="citation-source">{c.sources[0].label}</span>}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
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
        <Trace r={r} />
      </div>
    );
  }
  if (summary?.status === "loading") {
    return (
      <div className="ai-summary ai-summary-cta" aria-live="polite">
        <span className="muted">Writing a summary of these passages…</span>
      </div>
    );
  }
  const error = summary?.status === "error" ? <p className="ai-summary-error">{summary.message}</p> : null;
  if (ai && !ai.signed_in) {
    return (
      <div className="ai-summary ai-summary-cta">
        {error}
        <p className="muted">
          Want these in a few plain sentences? <Link href={loginHref}>Sign in</Link> for a few AI summaries a day.
        </p>
      </div>
    );
  }
  if (ai && ai.remaining === 0) {
    return (
      <div className="ai-summary ai-summary-cta">
        {error}
        <p className="muted">You&apos;ve used today&apos;s AI summaries. Searching the guides stays free; summaries come back tomorrow.</p>
      </div>
    );
  }
  const left = ai?.remaining == null ? "" : ` (${ai.remaining} left today)`;
  return (
    <div className="ai-summary ai-summary-cta">
      {error}
      <button type="button" className="btn btn-ghost btn-sm" onClick={onRequest} disabled={disabled}>
        Summarize with AI{left}
      </button>
    </div>
  );
}

function Thinking() {
  return (
    <div className="msg msg-assistant msg-thinking" aria-live="polite">
      <span className="avatar" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element -- tiny static SVG mark, nothing to optimize */}
        <img src="/brand/fisheye-mark.svg" alt="" />
      </span>
      <div className="bubble-card">
        <span className="sr-only">Looking through the guides…</span>
        <span className="typing" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        <span className="thinking-text">Searching the guides</span>
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
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  // How many AI summaries are left, as the server last said (every reply
  // carries it). Null until the first reply.
  const [ai, setAi] = useState<AiAllowance | null>(null);
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
        const response = await postAsk({ question: q, species_slug: speciesSlug ?? null });
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
    [busy, speciesSlug],
  );

  const summarize = useCallback(
    async (turnId: number, question: string) => {
      const setSummary = (summary: Summary) =>
        setTurns((ts) => ts.map((t) => (t.id === turnId && t.role === "assistant" ? { ...t, summary } : t)));
      setSummary({ status: "loading" });
      try {
        const response = await postAskSummary({ question, species_slug: speciesSlug ?? null });
        setAi(response.ai);
        setSummary({ status: "done", response });
      } catch (e) {
        const message = e instanceof ApiError ? e.message : "Couldn't reach FishEye's server.";
        if (e instanceof ApiError && e.status === 429) setAi((a) => (a ? { ...a, remaining: 0 } : a));
        if (e instanceof ApiError && e.status === 401) setAi({ signed_in: false, limit: null, remaining: null });
        setSummary({ status: "error", message });
      }
    },
    [speciesSlug],
  );

  useEffect(() => {
    if (initialQuestion && !asked.current) {
      asked.current = true;
      void ask(initialQuestion);
    }
  }, [initialQuestion, ask]);

  useEffect(() => {
    if (turns.length === 0 && !busy) return;
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: compact ? "nearest" : "end" });
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
          <h2>Ask about {speciesName}</h2>
          <p className="muted">Answers come from this fish&apos;s guide, with the passage cited.</p>
        </div>
      )}

      <div className="ask-thread" aria-live="polite">
        {empty && (
          <div className="ask-empty">
            {!compact && (
              <p className="muted">Try one of these, or ask your own:</p>
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
                  <p>{turn.message ?? "Couldn't reach FishEye's server. Is the backend running?"}</p>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => ask(turn.question)} disabled={busy}>
                    Try again
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
                <div className="answer-text">
                  {r.answer.split("\n\n").map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
                <Citations items={r.citations} compact={compact} />
                <Trace r={r} />
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
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask(input);
            }
          }}
          placeholder={speciesName ? `Ask about ${speciesName.toLowerCase()}…` : "Ask about bait, rigs, where to look…"}
          aria-label="Your question"
        />
        <button type="submit" className="send-btn" disabled={busy || input.trim().length < 3} aria-label="Send">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path d="M4 12l16-8-6 16-2.5-6.5L4 12z" fill="currentColor" />
          </svg>
        </button>
      </form>
      {input.length > MAX_LEN - 60 && (
        <p className="char-count muted">
          {input.length}/{MAX_LEN}
        </p>
      )}
    </div>
  );
}
