import type { Metadata } from "next";
import Link from "next/link";

import { PageTransition } from "@/components/motion/Transition";
import { QuestionLibrary } from "@/components/questions/QuestionLibrary";
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
  // Chinese either way (the API writes Traditional from the Simplified), else English.
  const chinese = locale === "zh" || locale === "zht";
  const questions: LibraryQuestion[] = await listQuestions(chinese ? locale : "en").catch(() => []);
  const lang = locale === "zht" ? "zh-Hant" : chinese ? "zh" : "en";

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
        {questions.length > 0 && locale !== "en" && !chinese && <p className="hint">{t.englishOnly}</p>}

        {questions.length > 0 && <QuestionLibrary questions={questions} lang={lang} />}

        <p className="sources-link">
          <Link href="/sources#questions">{all.fish.sources}</Link>
        </p>
      </main>
    </PageTransition>
  );
}
