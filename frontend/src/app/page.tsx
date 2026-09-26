import Link from "next/link";

import { FishArt } from "@/components/fish/FishArt";
import { QuickAsk } from "@/components/home/QuickAsk";
import { PageTransition, VT } from "@/components/motion/Transition";
import { listSpeciesGuides } from "@/lib/api/client";
import { waterFor } from "@/lib/fishArt";
import type { SpeciesGuide } from "@/lib/api/types";

const FEATURES = [
  {
    href: "/map",
    title: "Find water near you",
    body: "Public lakes with official fish surveys, plus the neighborhood ponds and small lakes around you, so a quick cast after work doesn't mean a long drive.",
    cta: "Open the map",
    art: "largemouth-bass",
  },
  {
    href: "/fish",
    title: "Learn each fish",
    body: "What it eats, where it hides, which bait works, and rod-and-reel setups that are easy to start with. Every setup lists its source.",
    cta: "Browse the fish guide",
    art: "bluegill",
  },
  {
    href: "/ask",
    title: "Ask anything",
    body: "Ask in plain words. Answers come only from the reviewed guides and cite the passage they used. If the guides don't cover it, FishMate says so.",
    cta: "Ask FishMate",
    art: "channel-catfish",
  },
] as const;

export default async function Home() {
  let starters: SpeciesGuide[] = [];
  try {
    const guides = await listSpeciesGuides();
    starters = guides.filter((g) => g.difficulty === "beginner").slice(0, 4);
  } catch {
    // The landing page stands without the backend; only this row needs it.
  }

  return (
    <PageTransition>
      <main className="home">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow reveal" style={{ "--i": 0 } as React.CSSProperties}>
              A fishing buddy for beginners · Texas for now
            </p>
            <h1 className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
              New place, no idea where to fish?
              <span className="hero-accent"> Start here.</span>
            </h1>
            <p className="lede reveal" style={{ "--i": 2 } as React.CSSProperties}>
              FishMate finds lakes and ponds near you, ranks the best spot for right now, and
              teaches you how to catch what lives there, with every answer traced back to its
              source.
            </p>
            <div className="hero-actions reveal" style={{ "--i": 3 } as React.CSSProperties}>
              <Link href="/map" className="btn btn-primary" transitionTypes={["nav-forward"]}>
                Find a spot
              </Link>
              <Link href="/fish" className="btn btn-ghost" transitionTypes={["nav-forward"]}>
                Browse fish
              </Link>
            </div>
            <div className="reveal" style={{ "--i": 4 } as React.CSSProperties}>
              <QuickAsk />
            </div>
          </div>

          <div className="hero-stage" aria-hidden="true">
            <div className="hero-water">
              <svg className="hero-waves" viewBox="0 0 600 80" preserveAspectRatio="none">
                <path d="M0 40 Q 75 10 150 40 T 300 40 T 450 40 T 600 40 V80 H0Z" />
                <path d="M0 50 Q 75 25 150 50 T 300 50 T 450 50 T 600 50 V80 H0Z" />
              </svg>
              <span className="bubble" style={{ "--b": 0 } as React.CSSProperties} />
              <span className="bubble" style={{ "--b": 1 } as React.CSSProperties} />
              <span className="bubble" style={{ "--b": 2 } as React.CSSProperties} />
              <span className="bubble" style={{ "--b": 3 } as React.CSSProperties} />
              <div className="hero-fish hero-fish-main">
                <FishArt slug="largemouth-bass" uid="hero-lmb" className="swimming" />
              </div>
              <div className="hero-fish hero-fish-small">
                <FishArt slug="bluegill" uid="hero-bg" className="swimming" />
              </div>
              <div className="hero-fish hero-fish-tiny">
                <FishArt slug="threadfin-shad" uid="hero-ts" className="swimming" />
              </div>
            </div>
          </div>
        </section>

        <section className="feature-grid" aria-label="What FishMate does">
          {FEATURES.map((f, i) => (
            <Link
              key={f.href}
              href={f.href}
              className="feature-card reveal"
              style={{ "--i": i + 5 } as React.CSSProperties}
              transitionTypes={["nav-forward"]}
            >
              <div
                className="feature-art"
                style={{ "--wa": waterFor(f.art)[0], "--wb": waterFor(f.art)[1] } as React.CSSProperties}
              >
                <FishArt slug={f.art} uid={`feature-${f.art}`} />
              </div>
              <h2>{f.title}</h2>
              <p>{f.body}</p>
              <span className="feature-cta">
                {f.cta} <span aria-hidden="true">→</span>
              </span>
            </Link>
          ))}
        </section>

        {starters.length > 0 && (
          <section className="starters">
            <div className="section-head">
              <h2>Good fish to start with</h2>
              <Link href="/fish" className="text-link" transitionTypes={["nav-forward"]}>
                All fish →
              </Link>
            </div>
            <div className="starter-row">
              {starters.map((g, i) => (
                <Link
                  key={g.slug}
                  href={`/fish/${g.slug}`}
                  className="starter-card reveal"
                  style={{ "--i": i + 8 } as React.CSSProperties}
                  transitionTypes={["nav-forward"]}
                >
                  <div
                    className="starter-art"
                    style={{ "--wa": waterFor(g.slug)[0], "--wb": waterFor(g.slug)[1] } as React.CSSProperties}
                  >
                    <VT name={`fish-art-${g.slug}`} share="morph" default="none">
                      <div className="morph-box">
                        <FishArt slug={g.slug} uid={`starter-${g.slug}`} />
                      </div>
                    </VT>
                  </div>
                  <div className="starter-name">{g.common_name}</div>
                  <div className="starter-sub">{g.summary}</div>
                </Link>
              ))}
            </div>
          </section>
        )}

        <section className="trust">
          <div className="trust-copy">
            <h2>Answers you can check</h2>
            <p>
              A language model is good at explaining and bad at knowing where fish are. So in
              FishMate it only explains. Spot rankings come from a transparent scoring engine;
              answers come from reviewed guides. Before any AI answer is shown, the server checks
              that every fish, number and citation in it came from the guide passages it was
              given. If one didn&apos;t, you see the guide text instead.
            </p>
          </div>
          <ol className="trust-steps">
            <li>
              <span className="step-dot">1</span>
              <div>
                <strong>Find</strong> the guide passages that match your question.
              </div>
            </li>
            <li>
              <span className="step-dot">2</span>
              <div>
                <strong>Explain</strong> them in plain words, citing each one.
              </div>
            </li>
            <li>
              <span className="step-dot">3</span>
              <div>
                <strong>Check</strong> every fish, number and citation against those passages.
              </div>
            </li>
          </ol>
        </section>

        <footer className="site-footer">
          <p>
            Data: Texas Parks and Wildlife, OpenStreetMap contributors, GBIF, National Weather
            Service. Fish photos from Wikimedia Commons, credited on each fish&apos;s page. Always
            check current TPWD regulations before you keep a fish.
          </p>
        </footer>
      </main>
    </PageTransition>
  );
}
