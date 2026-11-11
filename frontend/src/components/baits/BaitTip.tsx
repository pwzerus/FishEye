"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";

import { useLocale, useLocaleTag, useT } from "@/i18n/client";
import { localFishName, localTopicTitle } from "@/i18n/names";
import type { BaitCard } from "@/lib/api/types";
import { findBaits, useBaitCards } from "@/lib/baits";

/**
 * Baits and lures as linked words (backend knowledge/bait_terms.py): a bait
 * named in an answer is underlined, and tapping it opens a card — what it
 * is, why this fish takes it (the fish's own guide says why), how to use it,
 * the other fish it catches, and where to get it. The card's text is the
 * guides' and handbook's own, in English like the guides themselves.
 */

// One card open at a time.
let closeOpen: (() => void) | null = null;

export function BaitTip({ card, fish, children }: { card: BaitCard; fish?: string | null; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const wrap = useRef<HTMLSpanElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const all = useT();
  const t = all.baitTip;
  const locale = useLocale();
  const tag = useLocaleTag();
  const title = localTopicTitle(card.topic, locale) ?? card.title;

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    if (closeOpen && closeOpen !== close) closeOpen();
    closeOpen = close;
    const onDown = (e: MouseEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      if (closeOpen === close) closeOpen = null;
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const forFish = fish ? card.fish.find((f) => f.slug === fish) : undefined;
  const fishName = (slug: string, name: string) => localFishName(slug, locale) ?? name;
  const others = card.fish.filter((f) => f.slug !== fish).slice(0, 6);

  return (
    <span className="bait-term-wrap" ref={wrap}>
      <button
        ref={button}
        type="button"
        className="bait-term"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        {children}
      </button>
      {open && (
        <span id={id} role="dialog" aria-label={title} className="bait-tip" lang={tag}>
          <span className="bait-tip-head">
            <strong>{title}</strong>
            <button type="button" className="icon-btn" aria-label={all.common.close} onClick={() => setOpen(false)}>
              ×
            </button>
          </span>
          <span lang="en">{card.what}</span>
          {forFish?.why ? (
            <>
              <span className="bait-tip-label">{t.whyFish(fishName(forFish.slug, forFish.name))}</span>
              <span lang="en">{forFish.why}</span>
            </>
          ) : (
            card.why && (
              <>
                <span className="bait-tip-label">{t.whyItWorks}</span>
                <span lang="en">{card.why.replace(/^Why[^:]*:\s*/, "")}</span>
              </>
            )
          )}
          {card.how && (
            <>
              <span className="bait-tip-label">{t.howToUse}</span>
              <span lang="en">{card.how.replace(/^(How to [^:]*|When):\s*/, "")}</span>
            </>
          )}
          {others.length > 0 && (
            <>
              <span className="bait-tip-label">{fish ? t.alsoCatches : t.catches}</span>
              <span className="bait-tip-fish">
                {others.map((f) => (
                  <Link key={f.slug} href={`/fish/${f.slug}`} className="chip chip-sm">
                    {fishName(f.slug, f.name)}
                  </Link>
                ))}
              </span>
            </>
          )}
          <span className="bait-tip-links">
            <Link href="/map">{t.shopsOnMap}</Link>
            <Link href={`/handbook#${card.topic}`}>{t.readMore}</Link>
            <Link href={`/ask?q=${encodeURIComponent(t.askQuestion(title))}`}>{t.askMore}</Link>
          </span>
        </span>
      )}
    </span>
  );
}

/** `text` with the baits it names made tappable (the first mention of each,
 * up to three). Plain text until the bait list has loaded. */
export function BaitText({ text, fish }: { text: string; fish?: string | null }) {
  const cards = useBaitCards();
  const locale = useLocale();
  const found = cards ? findBaits(text, cards, locale, { fish }) : [];
  if (found.length === 0) return <>{text}</>;
  const parts: ReactNode[] = [];
  let at = 0;
  for (const m of found.sort((a, b) => a.start - b.start)) {
    parts.push(text.slice(at, m.start));
    parts.push(
      <BaitTip key={m.start} card={m.card} fish={fish}>
        {text.slice(m.start, m.end)}
      </BaitTip>,
    );
    at = m.end;
  }
  parts.push(text.slice(at));
  return <>{parts}</>;
}

/** The baits several texts name, as tappable chips: for answers whose text
 * sits inside links (Ask's source cards), where a word can't be a button. */
export function BaitChips({ texts, fish, label }: { texts: string[]; fish?: string | null; label: string }) {
  const cards = useBaitCards();
  const locale = useLocale();
  if (!cards) return null;
  const seen = new Set<string>();
  // Each named as the text names it ("chicken liver"), not by its card's
  // title, which can run to a line.
  const found = texts
    .flatMap((text) => findBaits(text, cards, locale, { fish, max: 5, seen }).map((m) => ({ ...m, word: text.slice(m.start, m.end) })))
    .slice(0, 5);
  if (found.length === 0) return null;
  return (
    <p className="bait-chips">
      <span className="muted">{label}</span>{" "}
      {found.map((m) => (
        <BaitTip key={m.card.id} card={m.card} fish={fish}>
          {m.word.charAt(0).toUpperCase() + m.word.slice(1)}
        </BaitTip>
      ))}
    </p>
  );
}
