import type { Metadata } from "next";

import { getT } from "@/i18n/server";

import { IdentifyFish } from "@/components/identify/IdentifyFish";
import { PageTransition } from "@/components/motion/Transition";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.identify} · FishEye`, description: t.pages.identifyDescription };
}

export default async function IdentifyPage() {
  const t = (await getT()).identify;
  return (
    <PageTransition>
      <main className="page-scroll identify-page">
        <section className="page-intro page-intro-center">
          <p className="eyebrow reveal" style={{ "--i": 0 } as React.CSSProperties}>
            {t.eyebrow}
          </p>
          <h1 className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
            {t.title}
          </h1>
          <p className="lede reveal" style={{ "--i": 2 } as React.CSSProperties}>
            {t.lede}
          </p>
        </section>
        <IdentifyFish />
      </main>
    </PageTransition>
  );
}
