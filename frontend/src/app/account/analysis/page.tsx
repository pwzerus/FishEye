import type { Metadata } from "next";

import { CatchAnalysisView } from "@/components/analysis/CatchAnalysisView";
import { PageTransition } from "@/components/motion/Transition";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.analysis.title} · FishEye`, description: t.analysis.description };
}

/** The signed-in angler's own catches, counted (backend services/catch_analysis.py). */
export default function CatchAnalysisPage() {
  return (
    <PageTransition>
      <main className="page-scroll account-page analysis-page">
        <CatchAnalysisView />
      </main>
    </PageTransition>
  );
}
