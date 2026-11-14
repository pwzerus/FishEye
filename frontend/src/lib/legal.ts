/**
 * Who runs FishEye and how to reach them, for the privacy policy, the terms
 * and the copyright page (src/app/privacy, terms, copyright).
 *
 * DRAFT, 2026-10-29: `operator` is a placeholder until the owner confirms
 * the legal name (a person today; the company once one is registered), and
 * the three pages should be read by a lawyer before they go live.
 *
 * 2026-11-12: the terms were rewritten (src/app/terms). `mailingAddress` is
 * a placeholder too: legal notices, the App Store's terms for apps and a
 * registered DMCA agent all need a postal address (a P.O. box will do).
 */
export const LEGAL = {
  // Left out at the owner's wish (2026-11-13): no personal name on the
  // site. The pages then say "the operator of FishEye". An LLC's name
  // goes here once there is one.
  operator: "" as string,
  // Left out at the owner's wish (2026-11-13): no home address on the site.
  // A P.O. box or an LLC's registered agent can go here later; the App
  // Store's own license terms and a DMCA agent will need one.
  mailingAddress: "" as string,
  contactEmail: "feedback.fisheyefishing@gmail.com",
  site: "fisheyefishing.com",
  // Whose law governs the terms, and where disputes go.
  governingState: "Texas",
  // COPPA: no accounts for children under 13.
  minimumAge: 13,
  // Notice before a change to the terms that matters applies.
  noticeDays: 14,
  // How long a new user has to opt out of arbitration (terms, "Disputes").
  optOutDays: 30,
  // The floor of FishEye's liability cap, in US dollars.
  liabilityFloorUsd: 50,
  updatedIso: "2026-11-13",
  // Accounts made before `updatedIso` come under these terms 14 days later
  // (`noticeDays`), after a notice on the site (components/legal/TermsNotice).
  existingUsersFromIso: "2026-11-27",
} as const;

/** A legal page in one language (src/app/<page>/text/): the English one
 * applies, and the others translate it. */
export interface LegalText {
  title: string;
  lede: string;
  description: string;
  Body: () => React.ReactNode;
}

/** A day ("2026-11-13") as the reader's language writes it: "November 13,
 * 2026", "2026年11月13日", "13 de noviembre de 2026". The day is a UTC date,
 * so it's the same day in every time zone. */
export function legalDate(iso: string, tag: string): string {
  return new Intl.DateTimeFormat(tag, { dateStyle: "long", timeZone: "UTC" }).format(Date.parse(`${iso}T00:00:00Z`));
}
