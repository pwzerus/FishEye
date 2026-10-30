"use client";

import type { ReactNode } from "react";

import { useLocale, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
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
export function OtherStateRules({ subject }: { subject?: string }) {
  const j = useSelectedJurisdiction();
  const t = useT().stateRules;
  const locale = useLocale();
  // Never the bare code while the list loads.
  const name = j ? localStateName(j.code, j.name, locale) : t.yourState;
  return (
    <section className="rules-card">
      <h2>{t.differ(subject ?? t.fishingRules)}</h2>
      <p>{t.notWritten(name)}</p>
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
  const { stateRules: t, common } = useT();
  const locale = useLocale();
  const j = state ? list?.find((x) => x.code === state) ?? null : null;
  // Every state's agency page is on file now, not only the states FishEye
  // has written rules for (knowledge/jurisdictions.py).
  if (state && j?.limits_url) {
    return (
      <p className={className}>
        {t.limitsVary}
        <a href={j.limits_url} target="_blank" rel="noreferrer">
          {t.checkLimits(j.agency_short ?? j.agency ?? j.name)}
        </a>
        {t.beforeKeep}
      </p>
    );
  }
  if (state && j && !j.covered) {
    return (
      <p className={className}>{t.limitsVaryState(localStateName(j.code, j.name, locale))}</p>
    );
  }
  if (state && !j) {
    return (
      <p className={className}>{t.limitsVaryYours}</p>
    );
  }
  const covered: Pick<Jurisdiction, "code" | "name" | "agency_short" | "limits_url">[] = list
    ? list.filter((x) => x.covered && x.limits_url)
    : [{ code: "TX", name: "Texas", agency_short: "TPWD", limits_url: texasUrl }];
  return (
    <p className={className}>
      {t.currentLimits}
      {covered.map((x, i) => (
        <span key={x.code}>
          {i > 0 && common.listSep}
          <a href={x.limits_url ?? undefined} target="_blank" rel="noreferrer">
            {localStateName(x.code, x.name, locale)} ({x.agency_short})
          </a>
        </span>
      ))}
      {t.elsewhere}
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
  const t = useT().stateRules;
  const locale = useLocale();
  const withRules = list?.filter((j) => j.covered && j.bait_rules.length > 0) ?? null;
  type Card = Pick<Jurisdiction, "code" | "name" | "bait_rules"> & Partial<Pick<Jurisdiction, "bait_rules_sources">>;
  const loading: Card[] = [{ code: "TX", name: "Texas", bait_rules: texasRules }];

  let shown: Card[];
  if (state === null) shown = withRules ?? loading;
  else if (withRules) {
    const mine = withRules.find((j) => j.code === state);
    if (!mine) return <OtherStateRules subject={t.baitRulesSubject} />;
    shown = [mine];
  } else if (state === "TX") shown = loading;
  else return null; // a state is chosen but the list hasn't loaded: show nothing rather than Texas's

  return (
    <>
      {shown.map((j) => (
        <section key={j.code} id={baitRulesAnchor(j.code)} className={className}>
          <h2>
            {t.baitRulesOf(localStateName(j.code, j.name, locale))}
            {suffix}
          </h2>
          <ul lang="en">
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

/** Above a guide's live-bait list, for someone in a state whose bait rules
 * contradict it (California: no fish as bait in most inland waters). The
 * guides were written where live minnows are legal (backend ADR 0030). */
export function LiveBaitWarning() {
  const j = useSelectedJurisdiction();
  const t = useT().stateRules;
  const locale = useLocale();
  if (!j?.bait_rules_on_every_bait_question) return null;
  const name = localStateName(j.code, j.name, locale);
  return (
    <p className="bait-warning" role="note">
      {t.liveBaitWarning(name)}
      <a href={`/fish#${baitRulesAnchor(j.code)}`}>{t.bait}</a>
      {t.liveBaitWarningTail(name)}
    </p>
  );
}
