import type { Metadata } from "next";

import { getT } from "@/i18n/server";

import { PageTransition } from "@/components/motion/Transition";
import { FirstTrip } from "@/components/start/FirstTrip";
import { listGear } from "@/lib/api/client";
import type { GearPhoto } from "@/lib/api/types";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.start} · FishEye`, description: t.pages.startDescription, alternates: { canonical: "/start" } };
}

export default async function StartPage() {
  // What each thing on the shopping list looks like. Without the API the
  // list still works, with no photos.
  const items = await listGear().then((g) => g.items).catch(() => []);
  const photos: Record<string, GearPhoto> = {};
  for (const i of items) if (i.photo) photos[i.id] = i.photo;
  return (
    <PageTransition>
      <FirstTrip photos={photos} />
    </PageTransition>
  );
}
