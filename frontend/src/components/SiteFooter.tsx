"use client";

import { usePathname } from "next/navigation";

import { LegalLinks } from "@/components/legal/LegalPage";

/**
 * The small print at the bottom of a page: privacy, terms, copyright and the
 * rest (LegalLinks), as on most sites, so the terms are one tap from every
 * page (the product owner, 2026-11-12).
 *
 * Not on pages that already have them or have no bottom to put them at:
 * home (its own footer), the map (it fills the screen), Ask (a line under
 * its question box instead), the legal pages, sign-in (the agreement sits
 * next to its buttons) and the admin pages.
 */
const NO_FOOTER = [/^\/$/, /^\/map(\/|$)/, /^\/ask(\/|$)/, /^\/(privacy|terms|copyright)$/, /^\/login$/, /^\/admin(\/|$)/];

export function SiteFooter() {
  const path = usePathname() ?? "/";
  if (NO_FOOTER.some((r) => r.test(path))) return null;
  return (
    <footer className="site-footer">
      <LegalLinks />
    </footer>
  );
}
