import type { MetadataRoute } from "next";

import { listJurisdictions, listSpeciesGuides } from "@/lib/api/client";
import { stateSlug } from "@/lib/stateSlug";
import { siteOrigin } from "@/lib/siteOrigin";

// The fish guides come from the API, which a build has no access to (see
// app/fish/page.tsx), so the list is made when a search engine asks.
export const dynamic = "force-dynamic";

/** Every public page a search engine should know about. One URL per page:
 * the language is a cookie, not a path (i18n/config.ts), so there are no
 * per-language variants to list. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = await siteOrigin();
  const page = (path: string, priority: number, changeFrequency: "daily" | "weekly" | "monthly" | "yearly") => ({
    url: `${origin}${path}`,
    changeFrequency,
    priority,
  });
  const pages: MetadataRoute.Sitemap = [
    page("/", 1, "weekly"),
    page("/map", 0.9, "daily"),
    page("/fish", 0.9, "weekly"),
    page("/handbook", 0.8, "weekly"),
    page("/identify", 0.8, "monthly"),
    page("/ask", 0.8, "monthly"),
    page("/start", 0.7, "monthly"),
    page("/rules", 0.7, "monthly"),
    page("/gear", 0.7, "monthly"),
    page("/questions", 0.7, "monthly"),
    page("/community", 0.6, "daily"),
    page("/sources", 0.3, "monthly"),
    page("/privacy", 0.2, "yearly"),
    page("/terms", 0.2, "yearly"),
    page("/copyright", 0.2, "yearly"),
  ];
  try {
    const guides = await listSpeciesGuides();
    for (const g of guides) pages.push(page(`/fish/${g.slug}`, 0.8, "monthly"));
  } catch {
    // The API is down: the main pages are still worth listing.
  }
  try {
    for (const j of await listJurisdictions()) pages.push(page(`/rules/${stateSlug(j.name)}`, j.covered ? 0.7 : 0.5, "monthly"));
  } catch {
    // As above.
  }
  return pages;
}
