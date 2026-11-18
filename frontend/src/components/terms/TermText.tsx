"use client";

import Link from "next/link";
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import { BaitTip } from "@/components/baits/BaitTip";
import { rigKeys } from "@/components/fish/rigTopics";
import { useLocale, useLocaleTag, useT } from "@/i18n/client";
import { localTopicTitle } from "@/i18n/names";
import type { BaitCard } from "@/lib/api/types";
import { findBaits, useBaitCards } from "@/lib/baits";
import { MESSAGES } from "@/i18n/messages";
import { findTerms, TERM_TOPIC, type TermId } from "@/lib/terms";

const en = MESSAGES.en;

// Punctuation that mustn't be left at the start or end of a line apart from
// the word it belongs to (LinkedText keeps it with a term).
const OPENING = /[“‘（(「『【《]+$/;
const CLOSING = /^[”’）)」』】》、。，；：！？…,.;:!?]+/;

// One card open at a time, shared with nothing else: a bait card closes on
// its own outside-click.
let closeOpen: (() => void) | null = null;

/** A term as an underlined word: a tap opens a small card saying what it
 * is, and the card's link opens the handbook topic. */
export function TermTip({ id, children }: { id: TermId; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const domId = useId();
  const wrap = useRef<HTMLSpanElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const tip = useRef<HTMLSpanElement>(null);
  const keyboard = useRef(false);
  const all = useT();
  const locale = useLocale();
  const tag = useLocaleTag();
  const term = all.terms.items[id];
  const topic = TERM_TOPIC[id];
  const topicTitle = localTopicTitle(topic, locale) ?? null;

  // A word near the right edge: slide the card left so it stays on screen.
  // (On a phone it is a sheet at the bottom, and this does nothing.)
  useLayoutEffect(() => {
    const el = tip.current;
    if (!open || !el) return;
    el.style.translate = "";
    const width = document.documentElement.clientWidth || window.innerWidth;
    if (!width) return;
    const over = el.getBoundingClientRect().right - (width - 12);
    if (over > 0 && getComputedStyle(el).position === "absolute") el.style.translate = `${-over}px 0`;
    // Opened from the keyboard: on to the card's link, so Enter follows it.
    if (keyboard.current) el.querySelector<HTMLElement>("a")?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    if (closeOpen && closeOpen !== close) closeOpen();
    closeOpen = close;
    const onDown = (e: MouseEvent | TouchEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("touchstart", onDown, { passive: true });
    document.addEventListener("keydown", onKey);
    return () => {
      if (closeOpen === close) closeOpen = null;
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("touchstart", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span className="term-wrap" ref={wrap}>
      <button
        ref={button}
        type="button"
        className="term"
        aria-expanded={open}
        aria-controls={open ? domId : undefined}
        onClick={(e) => {
          // A click from Enter or Space has no pointer position.
          keyboard.current = e.detail === 0;
          setOpen((o) => !o);
        }}
      >
        {children}
      </button>
      {open && (
        <span ref={tip} id={domId} role="dialog" aria-label={term.name} className="term-tip" lang={tag}>
          <span className="term-tip-head">
            <strong>{term.name}</strong>
            <button type="button" className="icon-btn" aria-label={all.common.close} onClick={() => setOpen(false)}>
              ×
            </button>
          </span>
          <span className="term-tip-def">{term.def}</span>
          <Link className="term-tip-more" href={`/handbook#${topic}`} onClick={() => setOpen(false)}>
            {rigKeys(topic).length > 0 ? all.terms.moreDrawing(topicTitle ?? term.name) : all.terms.more(topicTitle ?? term.name)}
          </Link>
        </span>
      )}
    </span>
  );
}

type Found = { start: number; end: number } & ({ kind: "term"; id: TermId } | { kind: "bait"; card: BaitCard });

/**
 * `text` with its fishing terms made tappable, and its baits and lures too
 * when `baits` is set (on a fish's page, for that fish: `fish`). `earlier`
 * is the texts above it in the same card or list: a term they link isn't
 * linked again. (Worked out afresh on every render, not kept in a shared
 * set: React renders twice in development, and a set filled by the first
 * pass left the second with nothing to link.)
 * Plain text until the bait list has loaded, if baits are wanted.
 */
export function LinkedText({
  text,
  baits = false,
  fish = null,
  skipTopic = null,
  earlier = [],
  max = 4,
}: {
  text: string;
  baits?: boolean;
  fish?: string | null;
  skipTopic?: string | null;
  earlier?: string[];
  max?: number;
}) {
  const all = useT();
  const locale = useLocale();
  const cards = useBaitCards();
  const shared = new Set<string>();
  for (const e of earlier) findTerms(e, locale, all.terms.items, en.terms.items, { skipTopic, max, seen: shared });
  const found: Found[] = findTerms(text, locale, all.terms.items, en.terms.items, { skipTopic, max, seen: shared }).map((m) => ({
    ...m,
    kind: "term" as const,
  }));
  if (baits && cards) {
    for (const b of findBaits(text, cards, locale, { fish, max: 3 }).filter((m) => m.card.topic !== skipTopic)) {
      // A bait named inside a term ("jig" in "jig head") or over it: the longer wins.
      const clash = found.findIndex((f) => b.start < f.end && f.start < b.end);
      if (clash === -1) found.push({ ...b, kind: "bait" });
      else if (b.end - b.start > found[clash].end - found[clash].start) found[clash] = { ...b, kind: "bait" };
    }
  }
  if (found.length === 0) return <>{text}</>;
  found.sort((a, b) => a.start - b.start);
  const parts: ReactNode[] = [];
  let at = 0;
  for (const m of found) {
    // A term is a button, and a line may break on either side of it: the
    // 。 after 帕洛马结 opened the next line, a “ before 德州钓组 ended one
    // (2026-11-17). Punctuation touching the term goes with it.
    let before = text.slice(at, m.start);
    const lead = before.match(OPENING)?.[0] ?? "";
    before = before.slice(0, before.length - lead.length);
    const trail = text.slice(m.end).match(CLOSING)?.[0] ?? "";
    parts.push(before);
    const word = text.slice(m.start, m.end);
    const tip =
      m.kind === "term" ? (
        <TermTip key={`t${m.start}`} id={m.id}>
          {word}
        </TermTip>
      ) : (
        <BaitTip key={`b${m.start}`} card={m.card} fish={fish}>
          {word}
        </BaitTip>
      );
    parts.push(
      lead || trail ? (
        <span key={`g${m.start}`} className="term-glue">
          {lead}
          {tip}
          {trail}
        </span>
      ) : (
        tip
      ),
    );
    at = m.end + trail.length;
  }
  parts.push(text.slice(at));
  return <>{parts}</>;
}

/** A list of texts, each term linked once in it (a fish page's lists). */
export function LinkedItems({ items, baits = false, fish = null }: { items: string[]; baits?: boolean; fish?: string | null }) {
  return (
    <>
      {items.map((item, i) => (
        <li key={item}>
          <LinkedText text={item} baits={baits} fish={fish} earlier={items.slice(0, i)} />
        </li>
      ))}
    </>
  );
}
