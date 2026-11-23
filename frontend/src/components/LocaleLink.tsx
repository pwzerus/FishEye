"use client";

import NextLink from "next/link";
import type { ComponentProps } from "react";

import { useLocale } from "@/i18n/client";
import { localePath, type Locale } from "@/i18n/config";

type Href = ComponentProps<typeof NextLink>["href"];

export function localeHref(locale: Locale, href: Href): Href {
  if (typeof href === "string") return localePath(locale, href);
  if (href.pathname) return { ...href, pathname: localePath(locale, href.pathname) };
  return href;
}

/** next/link that keeps the page's language in the address: on a page in
 * Chinese, "/rules" leads to "/zh/rules". So the language stays in every
 * link a person shares and every link a search engine follows
 * (docs/adr/0068). In English, links are left as written. */
export default function Link({ href, ...props }: ComponentProps<typeof NextLink>) {
  return <NextLink href={localeHref(useLocale(), href)} {...props} />;
}
