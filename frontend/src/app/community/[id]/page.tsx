import type { Metadata } from "next";

import { getT } from "@/i18n/server";
import { notFound } from "next/navigation";

import { PinDetailView } from "@/components/community/PinDetailView";
import { getPublicPin } from "@/lib/api/client";
import { PageTransition } from "@/components/motion/Transition";

export async function generateMetadata(props: PageProps<"/community/[id]">): Promise<Metadata> {
  const t = await getT();
  // A public catch's link is titled with the catch and its water, in a tab
  // and in a shared link's preview; any other keeps the plain title.
  const pinId = Number((await props.params).id);
  if (Number.isInteger(pinId) && pinId > 0) {
    try {
      const pin = await getPublicPin(pinId);
      const water = pin.water?.name ?? pin.lake?.name;
      return { title: [pin.title, water, "FishEye"].filter(Boolean).join(" · "), alternates: { canonical: `/community/${pinId}` } };
    } catch {
      // Not public, or not there: the plain title.
    }
  }
  return { title: `${t.pages.catch} · FishEye` };
}

export default async function PinPage(props: PageProps<"/community/[id]">) {
  const { id } = await props.params;
  const pinId = Number(id);
  if (!Number.isInteger(pinId) || pinId <= 0) notFound();
  // Rendered in the browser: whether you may see a pin depends on your
  // session (your private pins, admins), which the server render can't see.
  return (
    <PageTransition>
      <main className="page-scroll pin-page">
        <PinDetailView pinId={pinId} />
      </main>
    </PageTransition>
  );
}
