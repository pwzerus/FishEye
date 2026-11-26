import type { Messages } from "@/i18n/messages";

export type MovingKey = keyof Messages["quick"]["steps"];

/**
 * Quick takes (QuickTake.tsx) whose steps are moving pictures of their own
 * (QuickDrawings.tsx), each with a few words, in place of the topic's
 * drawing. The words of every quick take come from the API (backend
 * handbook_quick.py); only these captions live here, beside their pictures.
 */
export const MOVING_STEPS: Record<string, MovingKey> = {
  "technique-landing": "landing",
};

export function movingKey(topic: string): MovingKey | null {
  return MOVING_STEPS[topic] ?? null;
}
