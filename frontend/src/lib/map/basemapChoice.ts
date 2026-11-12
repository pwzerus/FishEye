import { useSyncExternalStore } from "react";

/**
 * Which basemap the maps draw: the plain map, free to show, or satellite
 * imagery, which MapTiler bills per tile. Plain is the default; satellite is
 * a button on the map (the product owner, 2026-11-12). The choice is kept in
 * this browser so it holds across pages and visits.
 */
export type BasemapChoice = "plain" | "satellite";

const KEY = "fisheye.basemap";
const listeners = new Set<() => void>();
let current: BasemapChoice | null = null;

function read(): BasemapChoice {
  if (current) return current;
  try {
    current = window.localStorage.getItem(KEY) === "satellite" ? "satellite" : "plain";
  } catch {
    current = "plain";
  }
  return current;
}

export function setBasemapChoice(choice: BasemapChoice): void {
  current = choice;
  try {
    window.localStorage.setItem(KEY, choice);
  } catch {
    // Private windows may refuse storage; the choice still holds for this page.
  }
  for (const l of listeners) l();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useBasemapChoice(): BasemapChoice {
  return useSyncExternalStore(subscribe, read, () => "plain");
}
