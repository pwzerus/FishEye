import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";
import { getLocale } from "@/i18n/server";

import { PRIVACY } from "./text";

// This page's own date: gear on catches and the gear counts (backend ADR
// 0056). Nothing collected before applies: catches had no gear until then.
const UPDATED = "2026-11-16";

// The policy in the reader's language (text/): English is the one that
// applies, and each translation says so at the top.
export async function generateMetadata(): Promise<Metadata> {
  const t = PRIVACY[await getLocale()];
  return { title: `${t.title} · FishEye`, description: t.description, alternates: { canonical: "/privacy" } };
}

export default async function PrivacyPage() {
  const t = PRIVACY[await getLocale()];
  return (
    <LegalPage title={t.title} lede={t.lede} updatedIso={UPDATED}>
      <t.Body />
    </LegalPage>
  );
}
