import type { Metadata } from "next";

import { AskChat } from "@/components/ask/AskChat";
import { PageTransition } from "@/components/motion/Transition";

export const metadata: Metadata = {
  title: "Ask · FishEye",
  description: "Ask a fishing question. Answers come from FishEye's reviewed fish guides, with sources.",
};

const SUGGESTIONS = [
  "What bait for crappie?",
  "Easiest setup for a kid who has never fished?",
  "When do white bass run?",
  "How do I get shad for bait?",
  "Can I bring live bait from one lake to another?",
  "What hook size for bluegill?",
];

export default async function AskPage(props: PageProps<"/ask">) {
  const params = await props.searchParams;
  const q = typeof params.q === "string" ? params.q : undefined;

  return (
    <PageTransition>
      <main className="page-scroll ask-page">
        <section className="page-intro page-intro-center">
          <p className="eyebrow reveal" style={{ "--i": 0 } as React.CSSProperties}>
            Ask FishEye
          </p>
          <h1 className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
            What do you want to know?
          </h1>
          <p className="lede reveal" style={{ "--i": 2 } as React.CSSProperties}>
            Answers come only from FishEye&apos;s reviewed fish guides and cite the passage they
            used. If the guides don&apos;t cover your question, FishEye says so instead of
            guessing.
          </p>
        </section>
        <div className="reveal" style={{ "--i": 3 } as React.CSSProperties}>
          <AskChat initialQuestion={q} suggestions={SUGGESTIONS} />
        </div>
      </main>
    </PageTransition>
  );
}
