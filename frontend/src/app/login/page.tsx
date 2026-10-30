import type { Metadata } from "next";

import { getT } from "@/i18n/server";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";
import { PageTransition } from "@/components/motion/Transition";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.login} · FishEye`, description: t.pages.loginDescription };
}

export default function LoginPage() {
  return (
    <PageTransition>
      <main className="page-scroll auth-page">
        <Suspense fallback={<div className="auth-card sk" style={{ height: 420 }} />}>
          <LoginForm />
        </Suspense>
      </main>
    </PageTransition>
  );
}
