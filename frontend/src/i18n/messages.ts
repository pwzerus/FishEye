import type { Locale } from "./config";
import en from "./en";
import es from "./es";
import ja from "./ja";
import ko from "./ko";
import zh from "./zh";

/** Every language has every string: the others are typed as this, so a
 * string added to en.ts and not translated fails the type check. */
export type Messages = typeof en;

export const MESSAGES: Record<Locale, Messages> = { en, zh, es, ko, ja };
