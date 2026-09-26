"use client";

import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";

import { VT } from "@/components/motion/Transition";
import { waterFor } from "@/lib/fishArt";
import type { SpeciesGuide, SpeciesPhotos } from "@/lib/api/types";
import { FishArt } from "./FishArt";

type Filter = "all" | "beginner" | "intermediate" | "advanced" | "forage";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "beginner", label: "Beginner-friendly" },
  { id: "intermediate", label: "Intermediate" },
  { id: "advanced", label: "Advanced" },
  { id: "forage", label: "Bait fish" },
];

export const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: "Beginner-friendly",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export function Tag({ guide }: { guide: SpeciesGuide }) {
  if (guide.role === "forage") return <span className="tag tag-forage">Bait fish</span>;
  if (!guide.difficulty) return null;
  return <span className={`tag tag-${guide.difficulty}`}>{DIFFICULTY_LABEL[guide.difficulty]}</span>;
}

function matches(g: SpeciesGuide, filter: Filter, q: string): boolean {
  if (filter === "forage" && g.role !== "forage") return false;
  if (filter !== "all" && filter !== "forage" && g.difficulty !== filter) return false;
  if (!q) return true;
  const hay = `${g.common_name} ${g.scientific_name} ${g.summary}`.toLowerCase();
  return hay.includes(q.toLowerCase());
}

export function FishGrid({ guides, photos }: { guides: SpeciesGuide[]; photos: SpeciesPhotos }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const q = useDeferredValue(query.trim());
  const shown = useMemo(() => guides.filter((g) => matches(g, filter, q)), [guides, filter, q]);

  return (
    <section className="fish-grid-wrap">
      <div className="fish-toolbar reveal" style={{ "--i": 3 } as React.CSSProperties}>
        <div className="segmented" role="tablist" aria-label="Filter fish">
          {FILTERS.map((f) => (
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
            placeholder="Search fish"
            aria-label="Search fish"
          />
        </label>
      </div>

      {shown.length === 0 ? (
        <p className="empty-note">No fish match that. Try another filter.</p>
      ) : (
        // Keyed on the filter so the cards re-run their entrance when it changes.
        <ul className="fish-grid" key={`${filter}-${q}`}>
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
                      <h2>{g.common_name}</h2>
                      <Tag guide={g} />
                    </div>
                    <p className="sci">{g.scientific_name}</p>
                    <p className="fish-card-summary">{g.summary}</p>
                    <span className="fish-card-cta">
                      How to catch it <span aria-hidden="true">→</span>
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
