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
            <h1>{title}</h1>
            <p className="lede">{lede}</p>
            <p className="legal-updated muted">{t.updated(LEGAL.updated)}</p>
            {t.englishOnly && <p className="hint">{t.englishOnly}</p>}
          </header>
          {children}
        </article>
        <LegalLinks />
      </main>
    </PageTransition>
  );
}

/** The three pages, for footers and the sign-up form. */
export function LegalLinks({ className = "legal-links" }: { className?: string }) {
  const t = useT().legal;
  return (
    <nav className={className} aria-label={t.policies}>
      <Link href="/privacy">{t.privacy}</Link>
      <Link href="/terms">{t.terms}</Link>
      <Link href="/copyright">{t.copyright}</Link>
      <a href={`mailto:${LEGAL.contactEmail}`}>{t.contact}</a>
    </nav>
  );
}
