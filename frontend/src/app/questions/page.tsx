import type { Metadata } from "next";
import Link from "next/link";

import { PageTransition } from "@/components/motion/Transition";
import { RevealFromHash } from "@/components/sources/RevealFromHash";
import { getLocale, getT } from "@/i18n/server";
import { listQuestions } from "@/lib/api/client";
import type { LibraryQuestion } from "@/lib/api/types";

// Rendered per request for the same reason as /fish: a build has no API.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = (await getT()).questionsPage;
  return { title: `${t.title} · FishEye`, description: t.lede };
}

/** The question library (backend app/knowledge/angling_qa.py, docs/adr/0051).
 * Each answer is a card under its own id, because that id is where an Ask
 * answer citing it links (AskChat's citationHref). Every card says what it
 * rests on, and "general knowledge" means it wasn't checked against a source. */
export default async function QuestionsPage() {
  const all = await getT();
  const t = all.questionsPage;
  const locale = await getLocale();
  const lang = locale === "zh" ? "zh" : "en";
  const questions: LibraryQuestion[] = await listQuestions(lang).catch(() => []);

  const groups: { category: string; label: string; items: LibraryQuestion[] }[] = [];
  for (const q of questions) {
    const last = groups[groups.length - 1];
    if (last && last.category === q.category) last.items.push(q);
    else groups.push({ category: q.category, label: q.category_label, items: [q] });
  }

  return (
    <PageTransition>
      <main className="page-scroll sources-page">
        <RevealFromHash />
        <header className="page-intro">
          <p className="eyebrow">FishEye</p>
          <h1>{t.title}</h1>
          <p className="lede">{t.lede}</p>
        </header>

        {questions.length === 0 && <div className="backend-error">{all.fish.loadError}</div>}
        {questions.length > 0 && locale !== "en" && locale !== "zh" && <p className="hint">{t.englishOnly}</p>}

        <nav className="chip-row handbook-nav" aria-label={t.title}>
          {groups.map((g) => (
            <a key={g.category} className="chip" href={`#${g.category}`} lang={lang}>
              {g.label}
            </a>
          ))}
        </nav>

        {groups.map((g) => (
          <details key={g.category} id={g.category} className="handbook-group" suppressHydrationWarning>
            <summary>
              <h3 lang={lang}>{g.label}</h3>
              <span>{t.count(g.items.length)}</span>
            </summary>
            <div className="handbook-grid">
              {g.items.map((q) => (
                <article key={q.id} id={q.id} className="handbook-card">
                  <h4 lang={lang}>{q.question}</h4>
                  <p lang={lang}><strong>{q.short}</strong></p>
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

        <p className="sources-link">
          <Link href="/sources#questions">{all.fish.sources}</Link>
        </p>
      </main>
    </PageTransition>
  );
}
