"use client";

import Link from "next/link";

import { PageTransition } from "@/components/motion/Transition";
import { useT } from "@/i18n/client";
import { LEGAL } from "@/lib/legal";

/** The privacy policy, the terms and the copyright page: one readable column. */
export function LegalPage({ title, lede, children }: { title: string; lede: string; children: React.ReactNode }) {
  const t = useT().legal;
  return (
    <PageTransition>
      <main className="page-scroll legal-page">
        <article>
          <header className="legal-head">
            <p className="eyebrow">FishEye</p>
            <h1 lang="en">{title}</h1>
            <p className="lede" lang="en">{lede}</p>
            <p className="legal-updated muted">{t.updated(LEGAL.updated)}</p>
            {t.englishOnly && <p className="hint">{t.englishOnly}</p>}
          </header>
          <div lang="en">{children}</div>
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
