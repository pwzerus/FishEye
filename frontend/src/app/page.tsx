import type { Metadata } from "next";

import FieldHome from "@/components/home/FieldHome";
import { getT, pageAlternates } from "@/i18n/server";
import { siteOrigin } from "@/lib/siteOrigin";

export const dynamic = "force-dynamic";

// Each public page names its own address as the canonical one, so a link
// with ?ref= (where a visitor came from) isn't a second copy for search
// engines. Set per page: one in the layout would point every page here.
// The home page's title says what FishEye is: "FishEye" alone is also a
// camera lens, and search results show the title.
export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: t.meta.homeTitle, alternates: await pageAlternates("/") };
}

export default async function Home() {
  // The site's name for search results (Google's "site names": WebSite
  // structured data on the home page), with the names people may search.
  const site = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "FishEye",
    alternateName: ["FishEye Fishing", "fisheyefishing.com"],
    url: `${await siteOrigin()}/`,
  };
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(site).replace(/</g, "\\u003c") }} />
      <FieldHome />
    </>
  );
}
