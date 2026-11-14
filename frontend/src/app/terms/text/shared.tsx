import type { LegalText } from "@/lib/legal";

/** What every language's terms share: the sections, in order, and their
 * numbers. A link to /terms#ai-answers lands on the same section in every
 * language, and "Section 17" is the same section in all of them. */
export const SECTION_IDS = [
  "agreeing",
  "accounts",
  "information",
  "ai-answers",
  "plus",
  "your-content",
  "rules",
  "moderation",
  "our-content",
  "third-parties",
  "copyright",
  "safety",
  "disclaimers",
  "liability",
  "release",
  "indemnity",
  "disputes",
  "changes",
  "app-stores",
  "general",
  "contact",
] as const;
export type SectionId = (typeof SECTION_IDS)[number];

/** A section's number, for the headings and for "see Section 17". */
export function sec(id: SectionId): number {
  return SECTION_IDS.indexOf(id) + 1;
}

/** The terms in one language (text/en.tsx is the one that applies). */
export type TermsText = LegalText;

export type SectionTitles = Record<SectionId, string>;

export function Heading({ id, titles }: { id: SectionId; titles: SectionTitles }) {
  return (
    <h2>
      {sec(id)}. {titles[id]}
    </h2>
  );
}

export function Contents({ label, titles }: { label: string; titles: SectionTitles }) {
  return (
    <nav className="legal-toc" aria-label={label}>
      <ol>
        {SECTION_IDS.map((id) => (
          <li key={id}>
            <a href={`#${id}`}>{titles[id]}</a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
