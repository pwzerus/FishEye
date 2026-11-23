import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_COOKIE, LOCALE_HEADER, splitLocalePath } from "@/i18n/config";

/**
 * A language's address shows the page at the plain one in that language:
 * "/zh/rules/texas" is "/rules/texas" in Chinese (docs/adr/0068). The
 * address stays in the browser; the page reads the language from the
 * header set here (i18n/server.ts getLocale).
 *
 * The visit also becomes the visitor's choice (the cookie), so a link or
 * script that leads to a plain address keeps the language. Search engines
 * keep no cookies from one page to the next, so a plain address is English
 * to them.
 */
export function proxy(request: NextRequest) {
  const { locale, path } = splitLocalePath(request.nextUrl.pathname);
  if (!locale) return NextResponse.next();

  const url = request.nextUrl.clone();
  url.pathname = path;
  const headers = new Headers(request.headers);
  headers.set(LOCALE_HEADER, locale);
  const response = NextResponse.rewrite(url, { request: { headers } });
  if (request.cookies.get(LOCALE_COOKIE)?.value !== locale) {
    response.cookies.set(LOCALE_COOKIE, locale, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
  }
  return response;
}

// Only the language addresses: everything else (pages, the API, files)
// never reaches the proxy. Keep in step with LOCALE_PATHS.
export const config = {
  matcher: ["/(zh|zh-tw|es|ko|ja)", "/(zh|zh-tw|es|ko|ja)/:path*"],
};
