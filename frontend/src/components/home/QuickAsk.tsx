"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const EXAMPLES = ["What bait for crappie?", "Easiest setup for a kid?", "When do white bass run?"];

/** A question box on the landing page that hands off to /ask. */
export function QuickAsk() {
  const router = useRouter();
  const [q, setQ] = useState("");

  function go(question: string) {
    const trimmed = question.trim();
    if (trimmed.length < 3) return;
    router.push(`/ask?q=${encodeURIComponent(trimmed)}`, { transitionTypes: ["nav-forward"] });
  }

  return (
    <div className="quick-ask">
      <form
        className="quick-ask-form"
        onSubmit={(e) => {
          e.preventDefault();
          go(q);
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask a fishing question…"
          aria-label="Ask a fishing question"
          maxLength={300}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={q.trim().length < 3}>
          Ask
        </button>
      </form>
      <div className="quick-ask-examples">
        {EXAMPLES.map((ex) => (
          <button key={ex} type="button" className="chip" onClick={() => go(ex)}>
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
