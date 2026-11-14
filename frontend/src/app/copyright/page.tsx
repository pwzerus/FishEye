import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";
import { getLocale } from "@/i18n/server";

import { COPYRIGHT } from "./text";

// This page's own date: it hasn't changed since the terms were rewritten.
const UPDATED = "2026-11-06";

// The page in the reader's language (text/): English is the one that
// applies, and each translation says so at the top.
export async function generateMetadata(): Promise<Metadata> {
  const t = COPYRIGHT[await getLocale()];
  return { title: `${t.title} · FishEye`, description: t.description, alternates: { canonical: "/copyright" } };
}

export default async function CopyrightPage() {
  const t = COPYRIGHT[await getLocale()];
  return (
    <LegalPage title={t.title} lede={t.lede} updatedIso={UPDATED}>
      <t.Body />
    </LegalPage>
  );
}
