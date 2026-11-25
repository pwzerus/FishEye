import type { Messages } from "@/i18n/messages";

export type QuickKey = keyof Messages["quick"]["takes"];

/**
 * Handbook topics with a quick take (QuickTake.tsx): a line, a few moving
 * pictures of a few words each and the points to remember, with the topic's
 * own text folded under them. Started 2026-11-25 with one topic, for the
 * owner to judge before the other long topics get the same.
 */
export const QUICK_TAKES: Record<string, QuickKey> = {
  "technique-landing": "landing",
};

export function quickKey(topic: string): QuickKey | null {
  return QUICK_TAKES[topic] ?? null;
}
