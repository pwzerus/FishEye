import type { Locale } from "@/i18n/config";
import type { GuideSource } from "@/lib/api/types";

// The backend names each state's limits page "<agency>: size and bag limits"
// (knowledge/jurisdictions.py). That half is FishEye's words, not the page's
// title, so it is shown in the reader's language; every other source keeps
// its own English title, which is what the linked page says.
const LIMITS = /^(.+): size and bag limits$/;

/** A source's link text in `locale`, and its language (undefined: the page's). */
export function sourceLabel(
  source: GuideSource,
  locale: Locale,
  limitsHeading: string,
): { text: string; lang: string | undefined } {
  const m = LIMITS.exec(source.label);
  if (!m || locale === "en") return { text: source.label, lang: "en" };
  const colon = locale === "zh" || locale === "zht" || locale === "ja" ? "：" : ": ";
  const heading = locale === "es" ? limitsHeading.charAt(0).toLowerCase() + limitsHeading.slice(1) : limitsHeading;
  return { text: `${m[1]}${colon}${heading}`, lang: undefined };
}
