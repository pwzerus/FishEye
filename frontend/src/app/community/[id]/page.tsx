import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PinDetailView } from "@/components/community/PinDetailView";
import { PageTransition } from "@/components/motion/Transition";

export const metadata: Metadata = { title: "Pin · FishEye" };

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
