import type { HandbookTopic } from "@/lib/api/types";

/**
 * The angler's handbook (backend app/knowledge/angling_handbook.py): baits,
 * lures, tackle, knots, caring for a catch, telling fish apart, timing.
 *
 * Every topic is a card under its own id, because that id is where an Ask
 * answer citing it links (`/fish#<id>`, AskChat's citationHref). A category
 * gets its own id too, for links like "the handbook's cleaning steps".
 * Server-rendered; no state.
 */
export function Handbook({ topics }: { topics: HandbookTopic[] }) {
  if (topics.length === 0) return null;
  const groups: { category: string; label: string; topics: HandbookTopic[] }[] = [];
  for (const t of topics) {
    const last = groups[groups.length - 1];
    if (last && last.category === t.category) last.topics.push(t);
    else groups.push({ category: t.category, label: t.category_label, topics: [t] });
  }

  return (
    <section id="handbook" className="handbook" aria-labelledby="handbook-title">
      <h2 id="handbook-title">The angler&apos;s handbook</h2>
      <p className="muted">
        What applies to every fish: baits and why they work, lures, tackle, knots, casting and
        playing a fish, weather and water, staying safe, the licence, and releasing, cleaning and
        cooking a catch. Each card names its sources.
      </p>
      <nav className="chip-row handbook-nav" aria-label="Handbook sections">
        {groups.map((g) => (
          <a key={g.category} className="chip" href={`#${g.category}`}>
            {g.label}
          </a>
        ))}
      </nav>
      {groups.map((g) => (
        <div key={g.category} id={g.category} className="handbook-group">
          <h3>{g.label}</h3>
          <div className="handbook-grid">
            {g.topics.map((t) => (
              <article key={t.id} id={t.id} className="handbook-card">
                <h4>{t.title}</h4>
                {t.body.map((sentence) => (
                  <p key={sentence}>{sentence}</p>
                ))}
                <p className="handbook-sources">
                  {t.sources.map((s, i) => (
                    <span key={s.url}>
                      {i > 0 && " · "}
                      <a href={s.url} target="_blank" rel="noreferrer">
                        {s.label}
                      </a>
                    </span>
                  ))}
                </p>
              </article>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
