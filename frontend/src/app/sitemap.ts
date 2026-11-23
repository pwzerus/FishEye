import type { MetadataRoute } from "next";

import { HREFLANG, LOCALES, localePath } from "@/i18n/config";
import { listJurisdictions, listSpeciesGuides } from "@/lib/api/client";
import { stateSlug } from "@/lib/stateSlug";
import { siteOrigin } from "@/lib/siteOrigin";

// The fish guides come from the API, which a build has no access to (see
// app/fish/page.tsx), so the list is made when a search engine asks.
export const dynamic = "force-dynamic";

type Frequency = "daily" | "weekly" | "monthly" | "yearly";
interface Page {
  path: string;
  priority: number;
  changeFrequency: Frequency;
}

/** Every public page a search engine should know about, at each language's
 * address ("/rules/texas", "/zh/rules/texas", ...), every entry naming the
 * others (hreflang), so each language can turn up in its own searches
 * (docs/adr/0068). */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = await siteOrigin();
  const page = (path: string, priority: number, changeFrequency: Frequency): Page => ({ path, priority, changeFrequency });
  const pages: Page[] = [
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
  return pages.flatMap(({ path, priority, changeFrequency }) => {
    const languages: Record<string, string> = {};
    for (const l of LOCALES) languages[HREFLANG[l]] = `${origin}${localePath(l, path)}`;
    languages["x-default"] = `${origin}${path}`;
    return LOCALES.map((l) => ({ url: `${origin}${localePath(l, path)}`, changeFrequency, priority, alternates: { languages } }));
  });
}
