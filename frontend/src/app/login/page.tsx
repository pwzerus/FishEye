import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";
import { PageTransition } from "@/components/motion/Transition";

export const metadata: Metadata = {
  title: "Sign in · FishEye",
  description: "Sign in or create a FishEye account to pin your catches.",
};

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
