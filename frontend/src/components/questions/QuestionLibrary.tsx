"use client";

import { useState } from "react";

import { useT } from "@/i18n/client";
import type { LibraryQuestion } from "@/lib/api/types";

/**
 * The question library, by category, with a search box: nearly 500 answers
 * are too many to browse. Every answer is in the page for search engines; the
 * box only hides the ones that don't match.
 */
export function QuestionLibrary({ questions, lang }: { questions: LibraryQuestion[]; lang: string }) {
  const t = useT().questionsPage;
  const [query, setQuery] = useState("");
  const words = query.trim().toLowerCase();
  const matches = (q: LibraryQuestion) => !words || `${q.question} ${q.short} ${q.body}`.toLowerCase().includes(words);

  const groups: { category: string; label: string; total: number; items: LibraryQuestion[] }[] = [];
  for (const q of questions) {
    let last = groups[groups.length - 1];
    if (!last || last.category !== q.category) {
      last = { category: q.category, label: q.category_label, total: 0, items: [] };
      groups.push(last);
    }
    last.total += 1;
    if (matches(q)) last.items.push(q);
  }
  const found = groups.filter((g) => g.items.length > 0);

  return (
    <>
      <label className="handbook-search">
        <span className="sr-only">{t.search}</span>
        <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t.search} />
      </label>

      {!words && (
        <nav className="chip-row handbook-nav" aria-label={t.title}>
          {groups.map((g) => (
            <a key={g.category} className="chip" href={`#${g.category}`} lang={lang}>
              {g.label}
            </a>
          ))}
        </nav>
      )}

      {found.length === 0 && <p className="muted">{t.none}</p>}

      {found.map((g) => (
        <details key={g.category} id={g.category} className="handbook-group" open={words ? true : undefined} suppressHydrationWarning>
          <summary>
            <h3 lang={lang}>{g.label}</h3>
            <span>{t.count(g.items.length)}</span>
          </summary>
          <div className="handbook-grid">
            {g.items.map((q) => (
              <article key={q.id} id={q.id} className="handbook-card">
                <h4 lang={lang}>{q.question}</h4>
                <p lang={lang}>
                  <strong>{q.short}</strong>
                </p>
                <p lang={lang}>{q.body}</p>
                <p className="handbook-sources">
                  <span className={q.basis === "general" ? "badge badge-muted" : undefined}>{t.basis[q.basis]}</span>
                  {q.sources.map((s) => (
                    <span key={s.url}>
                      {" · "}
                      <a href={s.url} target="_blank" rel="noreferrer" lang="en">
                        {s.label}
                      </a>
                    </span>
                  ))}
                </p>
              </article>
            ))}
          </div>
        </details>
      ))}
    </>
  );
}
