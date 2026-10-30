"use client";

import type { SpeciesGuide } from "@/lib/api/types";
import { useSelectedState } from "@/lib/jurisdiction";

/** A guide's summary: the Texas one for someone fishing in Texas, the same
 * sentences without the Texas-only claims for everyone else ("Texas's most
 * sought-after freshwater fish" opened the bass guide in Georgia). */
export function GuideSummary({ guide }: { guide: Pick<SpeciesGuide, "summary" | "summary_general"> }) {
  const state = useSelectedState();
  return <>{state === "TX" || !guide.summary_general ? guide.summary : guide.summary_general}</>;
}
