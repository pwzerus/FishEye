import type { Metadata } from "next";

import { getT } from "@/i18n/server";

import { PageTransition } from "@/components/motion/Transition";
import { FirstTrip } from "@/components/start/FirstTrip";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.start} · FishEye`, description: t.pages.startDescription };
}

export default function StartPage() {
  return (
    <PageTransition>
      <FirstTrip />
    </PageTransition>
  );
}
