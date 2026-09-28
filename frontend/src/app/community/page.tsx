import type { Metadata } from "next";

import { CommunityFeed } from "@/components/community/CommunityFeed";
import { PageTransition } from "@/components/motion/Transition";

export const metadata: Metadata = {
  title: "Community · FishEye",
  description: "Where other anglers are catching fish, pinned and photographed by them.",
};

export default function CommunityPage() {
  return (
    <PageTransition>
      <main className="page-scroll community-page">
        <CommunityFeed />
      </main>
    </PageTransition>
  );
}
