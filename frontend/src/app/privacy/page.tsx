import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";
import { getLocale } from "@/i18n/server";

import { PRIVACY } from "./text";

// This page's own date: the time and weather of a catch, and the National
// Weather Service as a recipient (backend ADR 0064). Before that, gear on
// catches and the gear counts (ADR 0056). Nothing collected before applies:
// catches had no time or weather until then.
const UPDATED = "2026-11-19";

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
