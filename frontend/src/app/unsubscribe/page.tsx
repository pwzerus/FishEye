import type { Metadata } from "next";

import { getT } from "@/i18n/server";
import { Suspense } from "react";

import { UnsubscribeView } from "@/components/auth/UnsubscribeView";
import { PageTransition } from "@/components/motion/Transition";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return {
    title: `${t.alerts.unsubTitle} · FishEye`,
    // The link carries the alert's own code: keep it out of search engines.
    robots: { index: false, follow: false },
  };
}

export default function UnsubscribePage() {
  return (
    <PageTransition>
      <main className="page-scroll auth-page">
        <Suspense fallback={<div className="auth-card sk" style={{ height: 240 }} />}>
          <UnsubscribeView />
        </Suspense>
      </main>
    </PageTransition>
  );
}
