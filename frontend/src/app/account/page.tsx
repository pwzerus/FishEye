import type { Metadata } from "next";
import { Suspense } from "react";

import { AccountView } from "@/components/auth/AccountView";
import { PageTransition } from "@/components/motion/Transition";

export const metadata: Metadata = { title: "Account · FishMate" };

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
