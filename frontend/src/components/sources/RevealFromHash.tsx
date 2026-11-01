"use client";

import { useRevealHash } from "@/lib/useRevealHash";

/** Opens the part of a server-rendered page the address points at. */
export function RevealFromHash() {
  useRevealHash();
  return null;
}
