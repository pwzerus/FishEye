import type { Metadata } from "next";

import { getT } from "@/i18n/server";
import { notFound } from "next/navigation";

import { AnglerView } from "@/components/community/AnglerView";
import { PageTransition } from "@/components/motion/Transition";

export async function generateMetadata(props: PageProps<"/community/anglers/[id]">): Promise<Metadata> {
  const t = await getT();
  const id = Number((await props.params).id);
  return {
    title: `${t.nav.catches} · FishEye`,
    ...(Number.isInteger(id) && id > 0 ? { alternates: { canonical: `/community/anglers/${id}` } } : {}),
  };
}

export default async function AnglerPage(props: PageProps<"/community/anglers/[id]">) {
  const { id } = await props.params;
  const anglerId = Number(id);
  if (!Number.isInteger(anglerId) || anglerId <= 0) notFound();
  return (
    <PageTransition>
      <main className="page-scroll community-page">
        <AnglerView id={anglerId} />
      </main>
    </PageTransition>
  );
}
