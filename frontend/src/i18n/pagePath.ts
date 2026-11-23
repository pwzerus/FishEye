"use client";

import { usePathname } from "next/navigation";

import { splitLocalePath } from "./config";

/** The page's path without a language segment ("/zh/rules" is "/rules"),
 * for comparing with the site's routes: the header's current tab, pages
 * where a notice stays hidden (docs/adr/0068).
 *
 * Kept out of i18n/client.tsx, which nearly everything imports: tests mock
 * next/navigation with a factory that imports the app's providers, and an
 * import of next/navigation there would wait on itself. */
export function usePagePath(): string {
  return splitLocalePath(usePathname() ?? "/").path;
}
