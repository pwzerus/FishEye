"use client";

import { useEffect, useSyncExternalStore } from "react";
import { useState } from "react";

import { useLocale } from "@/i18n/client";
import { listJurisdictions } from "@/lib/api/client";
import type { Jurisdiction } from "@/lib/api/types";

/**
 * Which state's rules the person wants (backend docs/adr/0027).
 *
 * How to catch a fish is the same everywhere; a licence, a limit or a bait
 * rule belongs to a state. The choice is remembered in the browser — set
 * here by the state picker, or by entering a state on the map — and read by
 * everything that shows a rule: Ask, the handbook, the guide pages.
 * Nothing chosen means nothing hidden: rule passages name their state in
 * their own words, so they can't be mistaken for a general rule.
 */
const KEY = "fisheye.state";
const EVENT = "fisheye:state";

export function readState(): string | null {
  try {
    const v = window.localStorage.getItem(KEY);
    return v && /^[A-Z]{2}$/.test(v) ? v : null;
  } catch {
    return null; // private window, blocked storage
  }
}

export function rememberState(code: string | null): void {
  try {
    if (code) window.localStorage.setItem(KEY, code);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* the choice just doesn't outlive the page */
  }
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange); // another tab
  // Back on a page the browser kept (back/forward cache), or on a tab that
  // sat in the background: the choice may have changed elsewhere meanwhile,
  // and a page showing the old state's rules looks like it never updates.
  window.addEventListener("pageshow", onChange);
  window.addEventListener("focus", onChange);
  document.addEventListener("visibilitychange", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
    window.removeEventListener("pageshow", onChange);
    window.removeEventListener("focus", onChange);
    document.removeEventListener("visibilitychange", onChange);
  };
}

/** The remembered state code, or null. Null on the server and during
 * hydration, so the first render matches the server's. */
export function useSelectedState(): string | null {
  return useSyncExternalStore(subscribe, readState, () => null);
}

const jurisdictions = new Map<string, Promise<Jurisdiction[]>>();

/** The states and their agencies, fetched once per language (their bait rules
 * are translated). Null while loading or if the request failed: callers fall
 * back to the state code. */
export function useJurisdictions(): Jurisdiction[] | null {
  const locale = useLocale();
  const [list, setList] = useState<Jurisdiction[] | null>(null);
  useEffect(() => {
    let live = true;
    const pending = jurisdictions.get(locale) ?? listJurisdictions(locale);
    jurisdictions.set(locale, pending);
    pending
      .then((l) => live && setList(l))
      .catch(() => {
        jurisdictions.delete(locale); // a later mount retries
      });
    return () => {
      live = false;
    };
  }, [locale]);
  return list;
}

/** The selected state's record, when both are known. */
export function useSelectedJurisdiction(): Jurisdiction | null {
  const code = useSelectedState();
  const list = useJurisdictions();
  return (code && list?.find((j) => j.code === code)) || null;
}
