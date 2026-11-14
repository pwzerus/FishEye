import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";
import { getLocale } from "@/i18n/server";

import { PRIVACY } from "./text";

// The policy in the reader's language (text/): English is the one that
// applies, and each translation says so at the top.
export async function generateMetadata(): Promise<Metadata> {
  const t = PRIVACY[await getLocale()];
  return { title: `${t.title} · FishEye`, description: t.description, alternates: { canonical: "/privacy" } };
}

export default async function PrivacyPage() {
  const t = PRIVACY[await getLocale()];
  return (
    <LegalPage title={t.title} lede={t.lede}>
      <t.Body />
    </LegalPage>
  );
}
