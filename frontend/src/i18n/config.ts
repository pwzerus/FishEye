/**
 * The languages the site is written in. English is the default and the
 * fallback. A page renders on the server in the language its address names
 * ("/zh/rules", see `LOCALE_PATHS`), or else in the visitor's choice, a
 * cookie (`LOCALE_COOKIE`) the language menu sets.
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

/** The first path segment that names a language in an address
 * ("/zh/rules/texas"). English has none: its addresses are the plain ones.
 * The cookie still holds a visitor's choice, but search engines never send
 * it, so they saw every page in English only; an address for each language
 * lets each one be found (docs/adr/0068). */
export const LOCALE_PATHS: Record<Locale, string> = { en: "", zh: "zh", zht: "zh-tw", es: "es", ko: "ko", ja: "ja" };

/** hreflang values: a language, and for Chinese its script, never a
 * country, so readers anywhere are matched. */
export const HREFLANG: Record<Locale, string> = { en: "en", zh: "zh-Hans", zht: "zh-Hant", es: "es", ko: "ko", ja: "ja" };

/** Set by src/proxy.ts on a request made to a language's address. */
export const LOCALE_HEADER = "x-fisheye-locale";

const BY_SEGMENT: ReadonlyMap<string, Locale> = new Map(
  LOCALES.filter((l) => LOCALE_PATHS[l] !== "").map((l) => [LOCALE_PATHS[l], l] as const),
);

/** The language an address names, and the page it shows: "/zh/rules/texas"
 * is zh and "/rules/texas", "/zh" is zh and "/", "/rules" is null and
 * "/rules". Takes a pathname, without ?query or #hash. */
export function splitLocalePath(pathname: string): { locale: Locale | null; path: string } {
  const match = /^\/([^/]+)(\/.*)?$/.exec(pathname);
  const locale = match ? BY_SEGMENT.get(match[1]) : undefined;
  if (!match || !locale) return { locale: null, path: pathname };
  return { locale, path: match[2] ?? "/" };
}

/** A page of this site, as opposed to the API, Next's own files, static
 * files ("/brand/mark.svg") and other sites. */
function isPagePath(path: string): boolean {
  if (!path.startsWith("/") || path.startsWith("//")) return false;
  const pathname = path.split(/[?#]/, 1)[0];
  const first = pathname.split("/")[1] ?? "";
  if (first === "api" || first === "_next") return false;
  return !pathname.slice(pathname.lastIndexOf("/") + 1).includes(".");
}

/** `path` (a page path, perhaps with ?query or #hash) at its address in
 * `locale`: "/rules" is "/zh/rules" in Chinese, "/" is "/zh", "/map?lake=5"
 * is "/zh/map?lake=5". English, paths that already name a language and
 * anything that isn't a page come back as they are. */
export function localePath(locale: Locale, path: string): string {
  const segment = LOCALE_PATHS[locale];
  if (!segment || !isPagePath(path)) return path;
  const cut = path.search(/[?#]/);
  const pathname = cut === -1 ? path : path.slice(0, cut);
  if (splitLocalePath(pathname).locale) return path;
  return `/${segment}${pathname === "/" ? "" : pathname}${cut === -1 ? "" : path.slice(cut)}`;
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
