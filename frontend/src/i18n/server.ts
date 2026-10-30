import { cookies } from "next/headers";

import { DEFAULT_LOCALE, LOCALE_COOKIE, LOCALE_TAGS, isLocale, type Locale } from "./config";
import { MESSAGES, type Messages } from "./messages";

/** The language this request is rendered in: the visitor's choice, or
 * English. Server components only (next/headers). */
export async function getLocale(): Promise<Locale> {
  const chosen = (await cookies()).get(LOCALE_COOKIE)?.value;
  return isLocale(chosen) ? chosen : DEFAULT_LOCALE;
}

/** The strings for this request, for server components. */
export async function getT(): Promise<Messages> {
  return MESSAGES[await getLocale()];
}

export async function getLocaleTag(): Promise<string> {
  return LOCALE_TAGS[await getLocale()];
}
