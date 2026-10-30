import type { Metadata } from "next";

import { getT } from "@/i18n/server";
import { Suspense } from "react";

import { AccountView } from "@/components/auth/AccountView";
import { PageTransition } from "@/components/motion/Transition";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.account} · FishEye` };
}

export default function AccountPage() {
  return (
    <PageTransition>
      <main className="page-scroll account-page">
        <Suspense fallback={null}>
          <AccountView />
        </Suspense>
      </main>
    </PageTransition>
  );
}
