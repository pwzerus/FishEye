"use client";

import { useSyncExternalStore, type ReactNode } from "react";

import { LinkedText } from "@/components/terms/TermText";
import { useT } from "@/i18n/client";
import type { QuickTakeText } from "@/lib/api/types";
import type { TopicTitle } from "@/lib/seeRefs";

import { QUICK_DRAWINGS } from "./QuickDrawings";
import { movingKey } from "./quickTopics";

const LESS_MOTION = "(prefers-reduced-motion: reduce)";

function subscribe(changed: () => void) {
  if (typeof window.matchMedia !== "function") return () => {};
  const query = window.matchMedia(LESS_MOTION);
  query.addEventListener?.("change", changed);
  return () => query.removeEventListener?.("change", changed);
}

function lessMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(LESS_MOTION).matches;
}

/** A topic's steps as moving pictures, a few words above each. */
export function MovingSteps({ topic }: { topic: string }) {
  const all = useT();
  const motion = !useSyncExternalStore(subscribe, lessMotion, () => false);
  const k = movingKey(topic);
  if (k === null) return null;
  const steps = all.quick.steps[k];
  return (
    <ol className="qt-steps">
      {QUICK_DRAWINGS[k].map((draw, i) => (
        <li key={steps[i]}>
          <p>
            <b aria-hidden="true">{i + 1}</b>
            <span>{steps[i]}</span>
          </p>
          <svg viewBox="0 0 160 120" aria-hidden="true">
            {draw(motion)}
          </svg>
        </li>
      ))}
    </ol>
  );
}

/**
 * A handbook topic at a glance (the owner, 2026-11-25: "too many words"):
 * one line, then the picture (`children`: the steps moving, the topic's
 * drawing, or its gear photos), then the points to remember. The topic's
 * own text stays, folded under it (Handbook.tsx), with every fact this
 * leaves out.
 */
export function QuickTake({
  topic,
  quick,
  refs = null,
  children,
}: {
  topic: string;
  quick: QuickTakeText;
  /** The handbook's titles, so a "(see …)" in it links like the topic's own text. */
  refs?: TopicTitle[] | null;
  children?: ReactNode;
}) {
  const all = useT();
  const lang = quick.lang ?? "en";
  return (
    <div className="qt">
      <p className="qt-lead" lang={lang}>
        {/* Terms are underlined in the points; the line only links its references. */}
        <LinkedText text={quick.lead} skipTopic={topic} max={0} refs={refs} />
      </p>
      {children}
      <div className="qt-points">
        <p className="qt-points-title">{all.quick.remember}</p>
        <ul>
          {quick.points.map((point, i) => (
            <li key={point} lang={lang}>
              <LinkedText text={point} skipTopic={topic} earlier={quick.points.slice(0, i)} refs={refs} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
