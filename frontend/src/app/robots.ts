import type { MetadataRoute } from "next";

import { siteOrigin } from "@/lib/siteOrigin";

/** Search engines may read every public page; account and admin pages, and
 * the API, are of no use in search results. */
export default async function robots(): Promise<MetadataRoute.Robots> {
  const origin = await siteOrigin();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/api/",
        "/admin",
        "/account",
        "/login",
        "/forgot-password",
        "/reset-password",
        "/verify-email",
      ],
    },
    sitemap: `${origin}/sitemap.xml`,
  };
}
