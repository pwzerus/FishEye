import type { Metadata } from "next";

import { ForgotPassword } from "@/components/auth/ForgotPassword";
import { PageTransition } from "@/components/motion/Transition";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.auth.forgotTitle} · FishEye`, robots: { index: false, follow: false } };
}

export default function ForgotPasswordPage() {
  return (
    <PageTransition>
      <main className="page-scroll auth-page">
        <ForgotPassword />
      </main>
    </PageTransition>
  );
}
