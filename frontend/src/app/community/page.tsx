import type { Metadata } from "next";

import { CommunityFeed } from "@/components/community/CommunityFeed";
import { PageTransition } from "@/components/motion/Transition";
import { CATCHES_AVAILABLE, CATCHES_SOON } from "@/lib/features";

export const metadata: Metadata = {
  title: "Community · FishEye",
  description: "Where other anglers are catching fish, pinned and photographed by them.",
};

export default function CommunityPage() {
  return (
    <PageTransition>
      <main className="page-scroll community-page">
        {CATCHES_AVAILABLE ? (
          <CommunityFeed />
        ) : (
          <section className="coming-soon" aria-labelledby="catches-soon">
            <p className="field-kicker">CATCHES</p>
            <h1 id="catches-soon">{CATCHES_SOON}</h1>
            <p>Sharing where you caught a fish isn&apos;t open yet. Lakes, fish guides and Ask work as usual.</p>
          </section>
        )}
      </main>
    </PageTransition>
  );
}
