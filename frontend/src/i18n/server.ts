import type { Metadata } from "next";
import { cookies, headers } from "next/headers";

import {
  DEFAULT_LOCALE,
  HREFLANG,
  LOCALES,
  LOCALE_COOKIE,
  LOCALE_HEADER,
  LOCALE_TAGS,
  isLocale,
  localePath,
  type Locale,
} from "./config";
import { MESSAGES, type Messages } from "./messages";

/** The language the address names ("/zh/rules"), which src/proxy.ts passes
 * on as a header; null for a plain address. */
export async function getUrlLocale(): Promise<Locale | null> {
  const named = (await headers()).get(LOCALE_HEADER);
  return isLocale(named) ? named : null;
}

/** The language this request is rendered in: the one its address names,
 * else the visitor's choice, else English. Server components only
 * (next/headers). */
export async function getLocale(): Promise<Locale> {
  const named = await getUrlLocale();
  if (named) return named;
  const chosen = (await cookies()).get(LOCALE_COOKIE)?.value;
  return isLocale(chosen) ? chosen : DEFAULT_LOCALE;
}

/** A page's addresses for search engines: the one being read as canonical,
 * and every language's, so each is listed in its own language's results
 * (hreflang). `path` is the page's plain address ("/rules/texas"); a ?ref=
 * on the visit isn't part of it, so a tagged link is no second copy. */
export async function pageAlternates(path: string): Promise<NonNullable<Metadata["alternates"]>> {
  const languages: Record<string, string> = {};
  for (const l of LOCALES) languages[HREFLANG[l]] = localePath(l, path);
  languages["x-default"] = path;
  return { canonical: localePath((await getUrlLocale()) ?? DEFAULT_LOCALE, path), languages };
}

/** The strings for this request, for server components. */
export async function getT(): Promise<Messages> {
  return MESSAGES[await getLocale()];
}

export async function getLocaleTag(): Promise<string> {
  return LOCALE_TAGS[await getLocale()];
}
