"use client";

import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";

import { VT } from "@/components/motion/Transition";
import { useLocale, useT } from "@/i18n/client";
import type { Locale } from "@/i18n/config";
import { localFishName } from "@/i18n/names";
import { useSelectedState } from "@/lib/jurisdiction";
import { waterFor } from "@/lib/fishArt";
import type { SpeciesGuide, SpeciesPhotos } from "@/lib/api/types";
import { FishArt } from "./FishArt";
import { FishName } from "./FishName";

type Filter = "all" | "beginner" | "intermediate" | "advanced" | "forage";

export function Tag({ guide }: { guide: SpeciesGuide }) {
  const t = useT().fish;
  if (guide.role === "forage") return <span className="tag tag-forage">{t.baitFish}</span>;
  if (!guide.difficulty) return null;
  const label = { beginner: t.beginner, intermediate: t.intermediate, advanced: t.advanced }[guide.difficulty];
  return <span className={`tag tag-${guide.difficulty}`}>{label}</span>;
}

function matches(g: SpeciesGuide, filter: Filter, q: string, locale: Locale): boolean {
  if (filter === "forage" && g.role !== "forage") return false;
  if (filter !== "all" && filter !== "forage" && g.difficulty !== filter) return false;
  if (!q) return true;
  // A fish's name in the chosen language finds it too ("鲶", "bagre").
  const hay = `${g.common_name} ${localFishName(g.slug, locale) ?? ""} ${g.scientific_name} ${g.summary}`.toLowerCase();
  return hay.includes(q.toLowerCase());
}

export function FishGrid({ guides, photos }: { guides: SpeciesGuide[]; photos: SpeciesPhotos }) {
  const t = useT().fish;
  const locale = useLocale();
  const filters: { id: Filter; label: string }[] = [
    { id: "all", label: t.all },
    { id: "beginner", label: t.beginner },
    { id: "intermediate", label: t.intermediate },
    { id: "advanced", label: t.advanced },
    { id: "forage", label: t.baitFish },
  ];
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const q = useDeferredValue(query.trim());
  // A fish that lives in one state only (the Guadalupe bass) is left out for
  // anyone who chose another; with no state chosen, every fish shows.
  const state = useSelectedState();
  const shown = useMemo(
    () => guides.filter((g) => (!state || !g.only_in_state || g.only_in_state === state) && matches(g, filter, q, locale)),
    [guides, filter, q, state, locale],
  );

  return (
    <section className="fish-grid-wrap">
      <div className="fish-toolbar reveal" style={{ "--i": 3 } as React.CSSProperties}>
        <div className="segmented" role="tablist" aria-label={t.filter}>
          {filters.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={filter === f.id}
              className={filter === f.id ? "segment active" : "segment"}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <label className="search-field">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="M20 20l-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.search}
            aria-label={t.search}
          />
        </label>
      </div>

      {shown.length === 0 ? (
        <p className="empty-note">{t.noMatch}</p>
      ) : (
        // Keyed on the filter so the cards re-run their entrance when it changes.
        <ul className="fish-grid">
          {shown.map((g, i) => {
            const photo = photos[g.slug];
            const [wa, wb] = waterFor(g.slug);
            return (
              <li key={g.slug} className="reveal" style={{ "--i": Math.min(i, 8) } as React.CSSProperties}>
                <Link href={`/fish/${g.slug}`} className="fish-card" transitionTypes={["nav-forward"]}>
                  <div className="fish-card-art" style={{ "--wa": wa, "--wb": wb } as React.CSSProperties}>
                    <VT name={`fish-art-${g.slug}`} share="morph" default="none">
                      <div className="morph-box">
                        <FishArt slug={g.slug} uid={`grid-${g.slug}`} />
                      </div>
                    </VT>
                    {photo && (
                      <span className="fish-card-photo" title={`Photo: ${photo.author} (${photo.license})`}>
                        {/* Wikimedia thumbnail, hot-linked as served and credited in full on the
                            fish's page (ADR 0015); next/image would re-host a resized copy. */}
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={photo.url} alt="" loading="lazy" />
                      </span>
                    )}
                  </div>
                  <div className="fish-card-body">
                    <div className="fish-card-top">
                      <h2>
                        <FishName slug={g.slug} english={g.common_name} />
                      </h2>
                      <Tag guide={g} />
                    </div>
                    <span className="fish-card-cta">
                      {t.baitGear} <span aria-hidden="true">→</span>
                    </span>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
