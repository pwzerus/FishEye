"use client";

import Link from "next/link";

import { PageTransition } from "@/components/motion/Transition";
import { useLocaleTag, useT } from "@/i18n/client";
import { LEGAL, legalDate } from "@/lib/legal";

/** The privacy policy, the terms and the copyright page: one readable column,
 * in the reader's language (each page's text/ folder). A translation says the
 * English version is the one that applies, as the terms do (General).
 * `updatedIso`: this page's own date, where it differs from LEGAL.updatedIso. */
export function LegalPage({
  title,
  lede,
  updatedIso = LEGAL.updatedIso,
  children,
}: {
  title: string;
  lede: string;
  updatedIso?: string;
  children: React.ReactNode;
}) {
  const t = useT().legal;
  const tag = useLocaleTag();
  return (
    <PageTransition>
      <main className="page-scroll legal-page">
        <article>
          <header className="legal-head">
            <p className="eyebrow">FishEye</p>
            <h1>{title}</h1>
            <p className="lede">{lede}</p>
            <p className="legal-updated muted">{t.updated(legalDate(updatedIso, tag))}</p>
            {t.translation && <p className="hint">{t.translation}</p>}
          </header>
          <div>{children}</div>
        </article>
        <LegalLinks />
      </main>
    </PageTransition>
  );
}

/** The policies and the sources, for footers and the sign-up form. */
export function LegalLinks({ className = "legal-links" }: { className?: string }) {
  const t = useT().legal;
  return (
    <nav className={className} aria-label={t.policies}>
      <Link href="/privacy">{t.privacy}</Link>
      <Link href="/terms">{t.terms}</Link>
      <Link href="/copyright">{t.copyright}</Link>
      <Link href="/rules">{t.rules}</Link>
      <Link href="/gear">{t.gear}</Link>
      <Link href="/questions">{t.questions}</Link>
      <Link href="/sources">{t.sources}</Link>
      <a href={`mailto:${LEGAL.contactEmail}`}>{t.contact}</a>
    </nav>
  );
}
