"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { RegionGate } from "@/components/rules/RegionGate";
import { useLocale, useT } from "@/i18n/client";
import { localCategory, localGearName, localTopicTitle } from "@/i18n/names";
import type { GearItem, HandbookTopic } from "@/lib/api/types";
import { useSelectedState } from "@/lib/jurisdiction";

/**
 * The angler's handbook (backend app/knowledge/angling_handbook.py): baits,
 * lures, tackle, knots, caring for a catch, telling fish apart, timing.
 * Read a chapter at a time: the address says which (`/handbook#knots`), so
 * the chapter list is plain links and the back button works.
 *
 * Every topic is a card under its own id, because that id is where an Ask
 * answer citing it links (`/handbook#<id>`, AskChat's citationHref); such a
 * link opens the topic's chapter. Every chapter stays in the page, hidden, so
 * it is still there for search engines and the browser's find. A topic that
 * states one state's rules is wrapped in a RegionGate, so it shows only to
 * someone in that state or who hasn't said where they are (backend
 * docs/adr/0027).
 */

// A colour for each chapter, as a hue (refinements.css makes the tints).
const HUES: Record<string, number> = {
  baits: 28, lures: 195, tackle: 212, rigs: 262, knots: 300, care: 350, identify: 168,
  timing: 45, technique: 14, methods: 142, conditions: 200, safety: 5, rules: 228, trouble: 34,
};

// The first things to read, in the order you need them.
const START_HERE = ["start-what-to-buy", "knot-improved-clinch", "bait-worms", "cast-spinning", "technique-bite", "technique-landing"];

function subscribeToHash(changed: () => void) {
  window.addEventListener("hashchange", changed);
  return () => window.removeEventListener("hashchange", changed);
}

function currentHash(): string {
  try {
    return decodeURIComponent(window.location.hash.slice(1));
  } catch {
    return "";
  }
}

const ICONS: Record<string, React.ReactNode> = {
  baits: <path d="M3 15c2-5 4-5 6 0s4 5 6 0 4-5 6-1" />,
  lures: (
    <>
      <path d="M3 12c3-5 9-6 14-3l4-2-1 5 1 5-4-2c-5 3-11 2-14-3z" />
      <circle cx="8" cy="11" r="0.9" fill="currentColor" />
    </>
  ),
  tackle: (
    <>
      <circle cx="10" cy="12" r="7" />
      <circle cx="10" cy="12" r="2.5" />
      <path d="M17 12h4M21 10v4" />
    </>
  ),
  rigs: <path d="M13 3v11a4.5 4.5 0 1 1-9 0v-1l3 2" />,
  knots: <path d="M3 8c6-3 12 11 18 8M3 16c6 3 12-11 18-8" />,
  care: <path d="M12 21s-8-5-9-11a5 5 0 0 1 9-3 5 5 0 0 1 9 3c-1 6-9 11-9 11z" />,
  identify: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M16.5 16.5L21 21" />
    </>
  ),
  timing: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  technique: <path d="M3 21C8 12 14 6 21 4M21 4v9" />,
  methods: <path d="M20 4C11 4 5 10 5 19M20 4c0 9-6 15-15 15M3 21l2-2M10 14l6-6" />,
  conditions: <path d="M7 14a4 4 0 0 1 .4-8 5 5 0 0 1 9.7 1.3A3.4 3.4 0 0 1 17 14H7zM3 19c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0" />,
  safety: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" />
      <path d="M5.6 5.6l3.6 3.6M18.4 5.6l-3.6 3.6M5.6 18.4l3.6-3.6M18.4 18.4l-3.6-3.6" />
    </>
  ),
  rules: <path d="M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5" />,
  trouble: <path d="M14.5 6.5a4 4 0 0 0-5.3 5.3L3.5 17.5l3 3 5.7-5.7a4 4 0 0 0 5.3-5.3l-2.6 2.6-2.7-.7-.7-2.7z" />,
};

function CategoryIcon({ id }: { id: string }) {
  return (
    <span className="handbook-cat-icon" aria-hidden="true">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {ICONS[id] ?? <circle cx="12" cy="12" r="8" />}
      </svg>
    </span>
  );
}

/** The gear a topic explains, as small photos linking to /gear. */
function GearStrip({ items }: { items: GearItem[] }) {
  const tr = useT().fish;
  const locale = useLocale();
  const shown = items.filter((i) => i.photo).slice(0, 4);
  if (shown.length === 0) return null;
  return (
    <div className="handbook-gear" aria-label={tr.topicGear}>
      {shown.map((i) => (
        <Link key={i.id} href={`/gear#${i.id}`} className="handbook-gear-item">
          {/* Credit is on /gear, one tap away, under the full-size photo. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={i.photo!.url} alt="" width={i.photo!.width} height={i.photo!.height} loading="lazy" />
          <span>{localGearName(i.id, locale) ?? i.name}</span>
        </Link>
      ))}
    </div>
  );
}

export function Handbook({
  topics,
  gear = [],
  children,
}: {
  topics: HandbookTopic[];
  gear?: GearItem[];
  // Beside the search box: which state's rules to show.
  children?: React.ReactNode;
}) {
  const tr = useT().fish;
  const locale = useLocale();
  const [query, setQuery] = useState("");
  const state = useSelectedState();
  const hash = useSyncExternalStore(subscribeToHash, currentHash, () => "");
  const rail = useRef<HTMLElement>(null);

  // Another state's rule cards aren't shown (RegionGate), so they aren't counted.
  const applies = (t: HandbookTopic) => t.region === "all" || state === null || t.region === state;
  const words = query.trim().toLowerCase();
  const matches = (t: HandbookTopic) =>
    !words || `${localTopicTitle(t.id, locale) ?? ""} ${t.title} ${t.body.join(" ")}`.toLowerCase().includes(words);
  const groups: { category: string; label: string; total: number; topics: HandbookTopic[] }[] = [];
  for (const t of topics) {
    let last = groups[groups.length - 1];
    if (!last || last.category !== t.category) {
      last = { category: t.category, label: localCategory(t.category, locale) ?? t.category_label, total: 0, topics: [] };
      groups.push(last);
    }
    if (!applies(t)) continue;
    last.total += 1;
    if (matches(t)) last.topics.push(t);
  }
  const shown = groups.filter((g) => g.total > 0);
  const found = groups.filter((g) => g.topics.length > 0);
  // The chapter in the address, or the one holding the topic in it.
  const fromHash = topics.find((t) => t.id === hash)?.category ?? shown.find((g) => g.category === hash)?.category;
  const active = fromHash ?? shown[0]?.category;

  // Landing on a chapter or a topic: it's only visible once `active` is set.
  useEffect(() => {
    if (hash) document.getElementById(hash)?.scrollIntoView?.({ block: "start", behavior: "instant" });
  }, [hash, active]);
  // On a phone the chapters are a row: keep the current one in view.
  useEffect(() => {
    const row = rail.current;
    const item = row?.querySelector<HTMLElement>('[aria-current="true"]');
    if (row && item && row.scrollWidth > row.clientWidth) row.scrollLeft = item.offsetLeft - (row.clientWidth - item.offsetWidth) / 2;
  }, [active]);

  if (topics.length === 0) return null;
  const articles = shown.reduce((n, g) => n + g.total, 0);
  const firstReads = START_HERE.map((id) => topics.find((t) => t.id === id)).filter((t) => t !== undefined);

  return (
    <section id="handbook" className="hb" aria-label={tr.handbook}>
      <header className="hb-hero reveal" style={{ "--i": 0 } as React.CSSProperties}>
        <div className="hb-hero-text">
          <p className="hb-eyebrow">FishEye</p>
          <h1>{tr.handbook}</h1>
          <p className="hb-lede">{tr.handbookLede}</p>
          <p className="hb-count">{tr.handbookCount(shown.length, articles)}</p>
        </div>
        <div className="hb-hero-tools">
          <label className="hb-search">
            <span className="sr-only">{tr.handbookSearch}</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="M16.5 16.5L21 21" />
            </svg>
            <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={tr.handbookSearch} />
          </label>
          {children}
        </div>
      </header>

      {locale !== "en" && topics.some((t) => !t.body_lang) && <p className="hint">{tr.englishContent}</p>}

      {!words && firstReads.length > 0 && (
        <nav className="hb-start reveal" style={{ "--i": 1 } as React.CSSProperties} aria-label={tr.handbookStart}>
          <h2>{tr.handbookStart}</h2>
          <ol>
            {firstReads.map((t, i) => (
              <li key={t.id}>
                <a href={`#${t.id}`}>
                  <span className="hb-step" aria-hidden="true">{i + 1}</span>
                  <span>{localTopicTitle(t.id, locale) ?? t.title}</span>
                </a>
              </li>
            ))}
          </ol>
        </nav>
      )}

      {found.length === 0 && <p className="muted">{tr.handbookNone}</p>}

      <div className={words ? "hb-body is-search" : "hb-body"}>
        {!words && (
          <nav ref={rail} className="hb-rail" aria-label={tr.handbookSections}>
            {shown.map((g) => (
              <a
                key={g.category}
                href={`#${g.category}`}
                className="hb-rail-item"
                aria-current={g.category === active ? "true" : undefined}
                style={{ "--hue": HUES[g.category] ?? 170 } as React.CSSProperties}
              >
                <CategoryIcon id={g.category} />
                <strong>{g.label}</strong>
                <small>{tr.topics(g.total)}</small>
              </a>
            ))}
          </nav>
        )}

        <div className="hb-chapters">
          {found.map((g) => {
            const next = shown[shown.findIndex((o) => o.category === g.category) + 1];
            return (
              <section
                key={g.category}
                id={g.category}
                className="hb-chapter"
                hidden={!words && g.category !== active}
                style={{ "--hue": HUES[g.category] ?? 170 } as React.CSSProperties}
              >
                <header className="hb-chapter-head">
                  <CategoryIcon id={g.category} />
                  <div>
                    <h2>{g.label}</h2>
                    <p>{tr.topics(g.topics.length)}</p>
                  </div>
                </header>
                <div className="hb-articles">
                  {g.topics.map((t) => {
                    const local = localTopicTitle(t.id, locale);
                    const card = (
                      <article key={t.id} id={t.id} className="handbook-card">
                        <h3>
                          {local ?? t.title}
                          {local && (
                            <span className="name-en" lang="en">
                              {t.title}
                            </span>
                          )}
                        </h3>
                        {t.body.map((sentence) => (
                          <p key={sentence} lang={t.body_lang ?? "en"}>
                            {sentence}
                          </p>
                        ))}
                        <GearStrip items={gear.filter((i) => i.topic === t.id)} />
                        {/* A state's rule keeps its official page beside it, to check
                            it against; the rest are on /sources (docs/adr/0043). */}
                        {t.region !== "all" && (
                          <p className="handbook-sources">
                            {t.sources.map((s, i) => (
                              <span key={s.url}>
                                {i > 0 && " · "}
                                <a href={s.url} target="_blank" rel="noreferrer" lang="en">
                                  {s.label}
                                </a>
                              </span>
                            ))}
                          </p>
                        )}
                      </article>
                    );
                    return t.region === "all" ? (
                      card
                    ) : (
                      <RegionGate key={t.id} region={t.region}>
                        {card}
                      </RegionGate>
                    );
                  })}
                </div>
                {!words && next && (
                  <a className="hb-next" href={`#${next.category}`}>
                    {tr.handbookNext(next.label)} <span aria-hidden="true">→</span>
                  </a>
                )}
              </section>
            );
          })}
        </div>
      </div>

      <p className="sources-link">
        <Link href="/sources#handbook">{tr.sources}</Link>
      </p>
    </section>
  );
}
