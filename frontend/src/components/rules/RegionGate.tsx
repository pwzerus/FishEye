"use client";

import type { ReactNode } from "react";

import type { Jurisdiction } from "@/lib/api/types";
import { useJurisdictions, useSelectedJurisdiction, useSelectedState } from "@/lib/jurisdiction";

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
 * has one, every agency it has when no state is chosen, and a plain pointer
 * otherwise — a link only where one was reviewed. `texasUrl` stands in
 * while the state list loads. */
export function LimitsNote({ texasUrl, className }: { texasUrl: string; className?: string }) {
  const state = useSelectedState();
  const list = useJurisdictions();
  const j = state ? list?.find((x) => x.code === state) ?? null : null;
  if (state && j?.covered && j.limits_url) {
    return (
      <p className={className}>
        Size and bag limits vary by species and lake.{" "}
        <a href={j.limits_url} target="_blank" rel="noreferrer">
          Check {j.agency_short ?? j.name}&apos;s current limits
        </a>{" "}
        before you keep a fish.
      </p>
    );
  }
  if (state && j && !j.covered) {
    return (
      <p className={className}>
        Size and bag limits vary by state, species and lake. Check {j.name}&apos;s fish and wildlife agency for
        the current ones before you keep a fish.
      </p>
    );
  }
  if (state && !j) {
    return (
      <p className={className}>
        Size and bag limits vary by state, species and lake. Check your state&apos;s fish and wildlife agency for
        the current ones before you keep a fish.
      </p>
    );
  }
  const covered: Pick<Jurisdiction, "code" | "name" | "agency_short" | "limits_url">[] = list
    ? list.filter((x) => x.covered && x.limits_url)
    : [{ code: "TX", name: "Texas", agency_short: "TPWD", limits_url: texasUrl }];
  return (
    <p className={className}>
      Size and bag limits vary by state, species and lake. Current limits:{" "}
      {covered.map((x, i) => (
        <span key={x.code}>
          {i > 0 && ", "}
          <a href={x.limits_url ?? undefined} target="_blank" rel="noreferrer">
            {x.name} ({x.agency_short})
          </a>
        </span>
      ))}
      ; elsewhere, your state&apos;s fish and wildlife agency. Check before you keep a fish.
    </p>
  );
}

/** The page anchor of a state's bait rules; matches the backend's passage
 * section (knowledge/jurisdictions.py bait_rules_section). */
export function baitRulesAnchor(code: string): string {
  return code === "TX" ? "bait_rules" : `bait_rules-${code.toLowerCase()}`;
}

/**
 * The bait-rules card(s): the chosen state's, every written state's when
 * none is chosen, or "differ by state" elsewhere. `texasRules` is what the
 * server rendered (the guide's own legal notes), shown until the state
 * list arrives so the page never starts empty.
 */
export function BaitRules({
  texasRules,
  texasUrl,
  suffix = "",
  className = "rules-card",
}: {
  texasRules: string[];
  texasUrl: string;
  suffix?: string;
  className?: string;
}) {
  const state = useSelectedState();
  const list = useJurisdictions();
  const withRules = list?.filter((j) => j.covered && j.bait_rules.length > 0) ?? null;
  type Card = Pick<Jurisdiction, "code" | "name" | "bait_rules"> & Partial<Pick<Jurisdiction, "bait_rules_sources">>;
  const loading: Card[] = [{ code: "TX", name: "Texas", bait_rules: texasRules }];

  let shown: Card[];
  if (state === null) shown = withRules ?? loading;
  else if (withRules) {
    const mine = withRules.find((j) => j.code === state);
    if (!mine) return <OtherStateRules subject="Bait rules" />;
    shown = [mine];
  } else if (state === "TX") shown = loading;
  else return null; // a state is chosen but the list hasn't loaded: show nothing rather than Texas's

  return (
    <>
      {shown.map((j) => (
        <section key={j.code} id={baitRulesAnchor(j.code)} className={className}>
          <h2>
            {j.name} bait rules{suffix}
          </h2>
          <ul>
            {j.bait_rules.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
          {j.bait_rules_sources && j.bait_rules_sources.length > 0 && (
            <p className="handbook-sources">
              {j.bait_rules_sources.map((s, i) => (
                <span key={s.url}>
                  {i > 0 && " · "}
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.label}
                  </a>
                </span>
              ))}
            </p>
          )}
        </section>
      ))}
      <LimitsNote className="muted" texasUrl={texasUrl} />
    </>
  );
}
