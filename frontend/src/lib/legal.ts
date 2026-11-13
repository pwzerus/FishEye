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
  operator: "[Operator's legal name]",
  mailingAddress: "[Mailing address]",
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
  updated: "November 13, 2026",
  updatedIso: "2026-11-13",
  // Accounts made before `updated` come under these terms 14 days later
  // (`noticeDays`), after a notice on the site (components/legal/TermsNotice).
  existingUsersFrom: "November 27, 2026",
  existingUsersFromIso: "2026-11-27",
} as const;
