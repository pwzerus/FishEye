/**
 * The languages the site is written in. English is the default and the
 * fallback; the choice is a cookie (`LOCALE_COOKIE`), set by the language
 * menu and read by the root layout, so a page renders in it on the server
 * and URLs stay the same in every language.
 */
/** "zht" is Traditional Chinese as written in Taiwan, made from the
 * Simplified ("zh") by scripts/zh_hant.py; the API serves it the same way
 * (backend app/knowledge/zh_hant.py). */
export const LOCALES = ["en", "zh", "zht", "es", "ko", "ja"] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";
export const LOCALE_COOKIE = "fisheye.lang";

/** Each language's name in itself, for the menu. */
export const LOCALE_NAMES: Record<Locale, string> = {
  en: "English",
  zh: "简体中文",
  zht: "繁體中文",
  es: "Español",
  ko: "한국어",
  ja: "日本語",
};
/** Short labels for the header button: the first character of the
 * language's own name, as on a Korean keyboard's 한/영 key; the two
 * Chinese by how they're written. */
export const LOCALE_SHORT: Record<Locale, string> = { en: "EN", zh: "简", zht: "繁", es: "ES", ko: "한", ja: "日" };
/** <html lang> and Intl formatting. US formats for English and Spanish:
 * dates and numbers as the person will see them on signs and licences.
 * The tag also picks Japanese, Korean or Chinese glyphs for the shared
 * characters. */
export const LOCALE_TAGS: Record<Locale, string> = {
  en: "en-US",
  zh: "zh-CN",
  zht: "zh-TW",
  es: "es-US",
  ko: "ko-KR",
  ja: "ja-JP",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

/** Chinese as written in Taiwan, Hong Kong or Macau, or marked Traditional. */
const TRADITIONAL = /^zh-(hant|tw|hk|mo)\b/;

/** The supported language a browser prefers, if it prefers one of ours
 * over English; used only to suggest switching, never to switch. */
export function preferredLocale(languages: readonly string[]): Locale | null {
  for (const tag of languages) {
    const lower = tag.toLowerCase();
    if (TRADITIONAL.test(lower)) return "zht";
    const base = lower.split("-")[0];
    if (base === "en") return null;
    if (isLocale(base)) return base;
  }
  return null;
}
