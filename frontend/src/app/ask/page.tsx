import type { Metadata } from "next";

import { getT } from "@/i18n/server";

import { AskChat } from "@/components/ask/AskChat";
import { PageTransition } from "@/components/motion/Transition";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: `${t.pages.ask} · FishEye`, description: t.pages.askDescription };
}

export default async function AskPage(props: PageProps<"/ask">) {
  const params = await props.searchParams;
  const q = typeof params.q === "string" ? params.q : undefined;
  const t = (await getT()).ask;

  return (
    <PageTransition>
      <main className="page-scroll ask-page">
        <section className="page-intro page-intro-center">
          <p className="eyebrow reveal" style={{ "--i": 0 } as React.CSSProperties}>
            {t.eyebrow}
          </p>
          <h1 className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
            {t.title}
          </h1>
          <p className="lede reveal" style={{ "--i": 2 } as React.CSSProperties}>
            {t.lede}
          </p>
        </section>
        <div className="reveal" style={{ "--i": 3 } as React.CSSProperties}>
          <AskChat initialQuestion={q} suggestions={t.suggestions} />
        </div>
      </main>
    </PageTransition>
  );
}
