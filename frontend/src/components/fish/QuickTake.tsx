"use client";

import { useSyncExternalStore } from "react";

import { LinkedText } from "@/components/terms/TermText";
import { useT } from "@/i18n/client";

import { QUICK_DRAWINGS } from "./QuickDrawings";
import type { QuickKey } from "./quickTopics";

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

/**
 * A handbook topic at a glance (the owner, 2026-11-25: "too many words"):
 * one line, then the steps as moving pictures with a few words each, then
 * the points to remember. The topic's own text stays, folded under it
 * (Handbook.tsx), with every fact this leaves out.
 */
export function QuickTake({ k, topic }: { k: QuickKey; topic: string }) {
  const all = useT();
  const words = all.quick.takes[k];
  const pictures = QUICK_DRAWINGS[k];
  const motion = !useSyncExternalStore(subscribe, lessMotion, () => false);
  return (
    <div className="qt">
      <p className="qt-lead">{words.lead}</p>
      <ol className="qt-steps">
        {pictures.map((draw, i) => (
          <li key={words.steps[i]}>
            <p>
              <b aria-hidden="true">{i + 1}</b>
              <span>{words.steps[i]}</span>
            </p>
            <svg viewBox="0 0 160 120" aria-hidden="true">
              {draw(motion)}
            </svg>
          </li>
        ))}
      </ol>
      <div className="qt-points">
        <p className="qt-points-title">{all.quick.remember}</p>
        <ul>
          {words.points.map((point, i) => (
            <li key={point}>
              <LinkedText text={point} skipTopic={topic} earlier={words.points.slice(0, i)} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
