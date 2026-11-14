import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";
import { getLocale } from "@/i18n/server";

import { TERMS } from "./text";

// The terms in the reader's language (text/): English is the one that
// applies, and each translation says so at the top.
export async function generateMetadata(): Promise<Metadata> {
  const t = TERMS[await getLocale()];
  return { title: `${t.title} · FishEye`, description: t.description, alternates: { canonical: "/terms" } };
}

export default async function TermsPage() {
  const t = TERMS[await getLocale()];
  return (
    <LegalPage title={t.title} lede={t.lede}>
      <t.Body />
    </LegalPage>
  );
}
