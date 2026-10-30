/**
 * Who runs FishEye and how to reach them, for the privacy policy, the terms
 * and the copyright page (src/app/privacy, terms, copyright).
 *
 * DRAFT, 2026-10-29: `operator` is a placeholder until the owner confirms
 * the legal name (a person today; the company once one is registered), and
 * the three pages should be read by a lawyer before they go live.
 */
export const LEGAL = {
  operator: "[Operator's legal name]",
  contactEmail: "feedback.fisheyefishing@gmail.com",
  site: "fisheyefishing.com",
  // Whose law governs the terms, and where disputes go.
  governingState: "Texas",
  // COPPA: no accounts for children under 13.
  minimumAge: 13,
  updated: "October 29, 2026",
} as const;
