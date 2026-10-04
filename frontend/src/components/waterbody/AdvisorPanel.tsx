"use client";

import { useState } from "react";

import { ApiError, postAdvisorExplain } from "@/lib/api/client";
import type { AdvisorResponse } from "@/lib/api/types";

/**
 * The AI advisor panel (PRD §5.1).
 *
 * Two deliberate choices worth knowing about:
 *
 * 1. It fetches on demand, not on lake selection. Every other panel loads
 *    automatically because it's reading data that already exists; this one
 *    asks a model to write something, which costs tokens and money once a
 *    real provider is wired in. Spending that on every map click — including
 *    the clicks where someone is just browsing — would be wasteful and,
 *    worse, would train the demo to look like the LLM *is* the product. It
 *    isn't: the ranking above is complete and useful without a word of prose
 *    attached to it.
 *
 * 2. It always says which kind of answer it's showing. `answer_source` and
 *    `trace.provider` are surfaced, not hidden, because the backend goes to
 *    real trouble to distinguish a validated model answer from a fixed
 *    template from a mock — and a UI that flattens those three into "here's
 *    your advice" throws that away.
 */

function badgeForAnswer(response: AdvisorResponse): { text: string; className: string } {
  if (response.answer_source === "fallback") {
    return { text: "plain summary", className: "advisor-badge advisor-badge-fallback" };
  }
  if (response.trace.provider === "mock") {
    return { text: "mock model", className: "advisor-badge advisor-badge-mock" };
  }
  return { text: response.trace.model, className: "advisor-badge advisor-badge-llm" };
}

function explainOutcome(outcome: string): string | null {
  switch (outcome) {
    case "ok":
      return null;
    case "provider_unavailable":
      return "The language model could not be reached, so this is the plain summary built from the same data.";
    case "invalid_json":
      return "The model's reply could not be parsed after a retry, so this is the plain summary instead.";
    case "ungrounded_source":
      return "The model cited a source the backend never supplied, so its answer was discarded — this is the plain summary instead.";
    case "ungrounded_species":
      return "The model named a fish that isn't confirmed in this lake, so its answer was discarded — this is the plain summary instead.";
    default:
      return "This is the plain summary rather than a written explanation.";
  }
}

function TraceDetails({ trace }: { trace: AdvisorResponse["trace"] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="advisor-trace">
      <button
        type="button"
        className="advisor-trace-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? "Hide" : "Show"} request trace
      </button>
      {open && (
        <dl className="advisor-trace-list">
          <div>
            <dt>trace id</dt>
            <dd className="advisor-trace-id">{trace.trace_id}</dd>
          </div>
          <div>
            <dt>provider / model</dt>
            <dd>
              {trace.provider} / {trace.model}
            </dd>
          </div>
          <div>
            <dt>outcome</dt>
            <dd>{trace.outcome}</dd>
          </div>
          <div>
            <dt>validation attempts</dt>
            <dd>{trace.validation_attempts}</dd>
          </div>
          <div>
            <dt>tokens (prompt / completion)</dt>
            <dd>
              {trace.prompt_tokens} / {trace.completion_tokens}
            </dd>
          </div>
          <div>
            <dt>estimated cost</dt>
            <dd>${trace.estimated_cost_usd.toFixed(6)}</dd>
          </div>
          <div>
            <dt>latency</dt>
            <dd>{Math.round(trace.latency_ms)} ms</dd>
          </div>
          <div>
            <dt>sources retrieved</dt>
            <dd>{trace.retrieved_source_count}</dd>
          </div>
          <div>
            <dt>cache</dt>
            <dd>{trace.cache_hit ? "hit" : "miss"}</dd>
          </div>
        </dl>
      )}
    </div>
  );
}

function StringList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="advisor-section">
      <h4>{title}</h4>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function AdvisorPanel({
  waterbodyId,
  targetSpecies,
}: {
  waterbodyId: number;
  targetSpecies?: string;
}) {
  const [response, setResponse] = useState<AdvisorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // An explicit user action, so setState in a click handler — no effect, and
  // therefore none of the react-hooks/set-state-in-effect trouble the other
  // panels have to work around.
  function requestExplanation() {
    setLoading(true);
    setError(null);
    postAdvisorExplain({
      waterbody_id: waterbodyId,
      target_species: targetSpecies || undefined,
    })
      .then((r) => {
        setResponse(r);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof ApiError ? e.message : "Could not reach the advisor.");
        setLoading(false);
      });
  }

  const badge = response ? badgeForAnswer(response) : null;
  const outcomeNote = response ? explainOutcome(response.trace.outcome) : null;

  return (
    <div className="advisor-panel">
      <div className="advisor-header">
        <h3>Why these spots?</h3>
        <button
          type="button"
          className="advisor-button"
          onClick={requestExplanation}
          disabled={loading}
        >
          {loading ? "Thinking…" : response ? "Ask again" : "Explain these picks"}
        </button>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {response && badge && (
        <>
          <div className="advisor-answer-meta">
            <span className={badge.className}>{badge.text}</span>
            {response.trace.cache_hit && <span className="advisor-badge">cached</span>}
          </div>

          {outcomeNote && <p className="advisor-outcome-note">{outcomeNote}</p>}

          <p className="advisor-summary">{response.explanation.summary}</p>

          <StringList title="Steps" items={response.explanation.steps} />
          <StringList title="Gear" items={response.explanation.gear} />
          <StringList title="Bait" items={response.explanation.bait} />
          <StringList title="Watch out for" items={response.explanation.risks} />

          {response.explanation.sources.length > 0 && (
            <div className="advisor-section">
              <h4>Sources</h4>
              <ul className="advisor-sources">
                {response.explanation.sources.map((s) => (
                  <li key={s.url}>
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <TraceDetails trace={response.trace} />
        </>
      )}
    </div>
  );
}
