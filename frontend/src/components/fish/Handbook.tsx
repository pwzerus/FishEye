"use client";

import Link from "next/link";
import { RegionGate } from "@/components/rules/RegionGate";
import { useLocale, useT } from "@/i18n/client";
import { localCategory, localGearName, localTopicTitle } from "@/i18n/names";
import type { GearItem, HandbookTopic } from "@/lib/api/types";
import { useRevealHash } from "@/lib/useRevealHash";

/**
 * The angler's handbook (backend app/knowledge/angling_handbook.py): baits,
 * lures, tackle, knots, caring for a catch, telling fish apart, timing.
 *
 * Every topic is a card under its own id, because that id is where an Ask
 * answer citing it links (`/fish#<id>`, AskChat's citationHref). A category
 * gets its own id too, for links like "the handbook's cleaning steps".
 * Server-rendered. A topic that states one state's rules is wrapped in a
 * RegionGate, so it shows only to someone in that state or who hasn't said
 * where they are (backend docs/adr/0027).
 */
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

export function Handbook({ topics, gear = [] }: { topics: HandbookTopic[]; gear?: GearItem[] }) {
  const tr = useT().fish;
  const locale = useLocale();
  useRevealHash();
  if (topics.length === 0) return null;
  const groups: { category: string; label: string; topics: HandbookTopic[] }[] = [];
  for (const t of topics) {
    const last = groups[groups.length - 1];
    if (last && last.category === t.category) last.topics.push(t);
    else groups.push({ category: t.category, label: localCategory(t.category, locale) ?? t.category_label, topics: [t] });
  }

  return (
    <section id="handbook" className="handbook" aria-labelledby="handbook-title">
      <h2 id="handbook-title">{tr.handbook}</h2>
      <p className="muted">{tr.handbookLede}</p>
      {locale !== "en" && <p className="hint">{tr.englishContent}</p>}
      <nav className="chip-row handbook-nav" aria-label={tr.handbookSections}>
        {groups.map((g) => (
          <a key={g.category} className="chip" href={`#${g.category}`}>
            {g.label}
          </a>
        ))}
      </nav>
      {groups.map((g) => (
        <details key={g.category} id={g.category} className="handbook-group" suppressHydrationWarning>
          <summary><h3>{g.label}</h3><span>{tr.topics(g.topics.length)}</span></summary>
          <div className="handbook-grid">
            {g.topics.map((t) => {
              const card = (
                <article key={t.id} id={t.id} className="handbook-card">
                  <h4>
                    {localTopicTitle(t.id, locale) ?? t.title}
                    {localTopicTitle(t.id, locale) && (
                      <span className="name-en" lang="en">
                        {t.title}
                      </span>
                    )}
                  </h4>
                  {t.body.map((sentence) => (
                    <p key={sentence} lang="en">
                      {sentence}
                    </p>
                  ))}
                  <GearStrip items={gear.filter((g) => g.topic === t.id)} />
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
        </details>
      ))}
      <p className="sources-link">
        <Link href="/sources#handbook">{tr.sources}</Link>
      </p>
    </section>
  );
}
