import type { Metadata } from "next";
import { Suspense } from "react";

import { ResetPassword } from "@/components/auth/ResetPassword";
import { PageTransition } from "@/components/motion/Transition";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return {
    title: `${t.auth.resetTitle} · FishEye`,
    // The link carries a one-time code: keep it out of search engines.
    robots: { index: false, follow: false },
  };
}

export default function ResetPasswordPage() {
  return (
    <PageTransition>
      <main className="page-scroll auth-page">
        <Suspense fallback={<div className="auth-card sk" style={{ height: 240 }} />}>
          <ResetPassword />
        </Suspense>
      </main>
    </PageTransition>
  );
}
