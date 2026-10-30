import type { Metadata } from "next";

import { getT } from "@/i18n/server";

import { CommunityFeed } from "@/components/community/CommunityFeed";
import { PageTransition } from "@/components/motion/Transition";
import { CATCHES_AVAILABLE } from "@/lib/features";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.community} · FishEye`, description: t.pages.communityDescription };
}

export default async function CommunityPage() {
  const t = await getT();
  return (
    <PageTransition>
      <main className="page-scroll community-page">
        {CATCHES_AVAILABLE ? (
          <CommunityFeed />
        ) : (
          <section className="coming-soon" aria-labelledby="catches-soon">
            <p className="field-kicker">{t.nav.catches}</p>
            <h1 id="catches-soon">{t.common.catchesSoon}</h1>
            <p>{t.feed.soonText}</p>
          </section>
        )}
      </main>
    </PageTransition>
  );
}
