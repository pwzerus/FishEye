"use client";

import type { ReactNode } from "react";

import { useSelectedJurisdiction, useSelectedState } from "@/lib/jurisdiction";

/**
 * Shows something that states one state's rules (backend docs/adr/0027) only
 * to someone in that state — or to someone who hasn't said where they are,
 * who gets it under its own heading ("Texas bait rules") rather than
 * nothing. Anyone in another state gets `fallback`.
 */
export function RegionGate({
  region,
  children,
  fallback = null,
}: {
  region: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const state = useSelectedState();
  if (state === null || state === region) return <>{children}</>;
  return <>{fallback}</>;
}

/** Where someone in a state FishEye hasn't written rules for is sent
 * instead. Never links an agency page FishEye hasn't reviewed. */
export function OtherStateRules({ subject = "Fishing rules" }: { subject?: string }) {
  const j = useSelectedJurisdiction();
  const name = j ? j.name : "your state"; // never the bare code while the list loads
  return (
    <section className="rules-card">
      <h2>{subject} differ by state</h2>
      <p>
        FishEye hasn&apos;t written {name}&apos;s rules yet. Check {name}&apos;s fish and wildlife agency
        for the current licence, limits and bait rules before you fish. Everything about how to catch,
        handle and cook a fish works the same wherever you are.
      </p>
    </section>
  );
}

/** "Check TPWD's current limits": the selected state's agency when FishEye
 * has one, else a plain pointer — a link only where one was reviewed.
 * `texasUrl` is the page that applies when no state is chosen. */
export function LimitsNote({ texasUrl, className }: { texasUrl: string; className?: string }) {
  const state = useSelectedState();
  const j = useSelectedJurisdiction();
  if (state === null || state === "TX") {
    return (
      <p className={className}>
        Size and bag limits vary by state, species and lake.{" "}
        {state === "TX" ? (
          <a href={j?.limits_url ?? texasUrl} target="_blank" rel="noreferrer">
            Check TPWD&apos;s current limits
          </a>
        ) : (
          <>
            Texas&apos;s are at{" "}
            <a href={texasUrl} target="_blank" rel="noreferrer">
              TPWD
            </a>
            ; elsewhere, check your state&apos;s fish and wildlife agency
          </>
        )}{" "}
        before you keep a fish.
      </p>
    );
  }
  const name = j ? j.name : "your state";
  return (
    <p className={className}>
      Size and bag limits vary by state, species and lake. Check {name}&apos;s fish and wildlife agency for
      the current ones before you keep a fish.
    </p>
  );
}
