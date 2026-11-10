import type { Metadata } from "next";

import { Handbook } from "@/components/fish/Handbook";
import { PageTransition } from "@/components/motion/Transition";
import { BaitRules } from "@/components/rules/RegionGate";
import { StatePicker } from "@/components/ui/StatePicker";
import { getLocale, getT } from "@/i18n/server";
import { listGear, listHandbook, listSpeciesGuides } from "@/lib/api/client";
import type { GearItem, HandbookTopic, SpeciesGuide } from "@/lib/api/types";

// From the API at request time, like /fish: a build has no API to ask.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = (await getT()).fish;
  return { title: `${t.handbook} · FishEye`, description: t.handbookLede };
}

/** The handbook on its own page: Ask's citations and every "read more" link
 * land here, on the topic's own anchor. */
export default async function HandbookPage() {
  const all = await getT();
  const t = all.fish;
  const locale = await getLocale();
  let topics: HandbookTopic[] = [];
  let gear: GearItem[] = [];
  let guides: SpeciesGuide[] = [];
  let failed = false;
  try {
    [topics, gear, guides] = await Promise.all([
      listHandbook(locale),
      listGear(locale).then((g) => g.items).catch(() => []),
      listSpeciesGuides().catch(() => []),
    ]);
  } catch {
    failed = true;
  }
  const baitRules = guides.find((g) => g.legal_notes.length > 0)?.legal_notes ?? [];

  return (
    <PageTransition>
      <main className="page-scroll handbook-page">
        {failed ? (
          <>
            <section className="page-intro">
              <h1>{t.handbook}</h1>
              <p className="lede">{t.handbookLede}</p>
            </section>
            <div className="backend-error">{t.loadError}</div>
          </>
        ) : (
          <Handbook topics={topics} gear={gear}>
            <StatePicker />
          </Handbook>
        )}

        {baitRules.length > 0 && (
          <div className="rules-stack reveal" style={{ "--i": 6 } as React.CSSProperties}>
            <BaitRules texasRules={baitRules} texasUrl={guides[0]?.limits_url ?? ""} suffix={all.stateRules.forEveryFish} />
          </div>
        )}
      </main>
    </PageTransition>
  );
}
