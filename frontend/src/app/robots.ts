import type { MetadataRoute } from "next";

import { LOCALES, localePath } from "@/i18n/config";
import { siteOrigin } from "@/lib/siteOrigin";

const PRIVATE = ["/admin", "/account", "/login", "/forgot-password", "/reset-password", "/verify-email"];

/** Search engines may read every public page; account and admin pages, and
 * the API, are of no use in search results, at any language's address
 * ("/zh/account" too, docs/adr/0068). */
export default async function robots(): Promise<MetadataRoute.Robots> {
  const origin = await siteOrigin();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", ...LOCALES.flatMap((l) => PRIVATE.map((p) => localePath(l, p)))],
    },
    sitemap: `${origin}/sitemap.xml`,
  };
}
