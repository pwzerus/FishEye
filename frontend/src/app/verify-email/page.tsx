import type { Metadata } from "next";

import { getT } from "@/i18n/server";
import { Suspense } from "react";

import { VerifyEmail } from "@/components/auth/VerifyEmail";
import { PageTransition } from "@/components/motion/Transition";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.verifyEmail} · FishEye`,
    // The link carries a one-time code: keep it out of search engines.
    robots: { index: false, follow: false } };
}

export default function VerifyEmailPage() {
  return (
    <PageTransition>
      <main className="page-scroll auth-page">
        <Suspense fallback={<div className="auth-card sk" style={{ height: 240 }} />}>
          <VerifyEmail />
        </Suspense>
      </main>
    </PageTransition>
  );
}
