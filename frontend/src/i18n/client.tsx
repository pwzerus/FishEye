"use client";

import { createContext, use, useMemo, type ReactNode } from "react";

import { LOCALE_COOKIE, LOCALE_TAGS, type Locale } from "./config";
import { MESSAGES, type Messages } from "./messages";

interface I18n {
  locale: Locale;
  t: Messages;
}

// Without a provider (tests, a component rendered on its own): English.
const I18nContext = createContext<I18n>({ locale: "en", t: MESSAGES.en });

/** Gives every client component below it the chosen language. The root
 * layout reads the cookie and passes the locale; changing it refreshes the
 * page's server components, which re-render this with the new one. */
export function I18nProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  const value = useMemo(() => ({ locale, t: MESSAGES[locale] }), [locale]);
  return <I18nContext value={value}>{children}</I18nContext>;
}

/** The strings in the chosen language: `t.nav.map`, `t.map.catchesAt(3)`. */
export function useT(): Messages {
  return use(I18nContext).t;
}

export function useLocale(): Locale {
  return use(I18nContext).locale;
}

/** A BCP 47 tag for Intl formatting in the chosen language. */
export function useLocaleTag(): string {
  return LOCALE_TAGS[use(I18nContext).locale];
}

/** Remembers the choice for a year. The caller refreshes the page. */
export function saveLocale(locale: Locale): void {
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
}
