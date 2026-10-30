"use client";

import { useState } from "react";

import { useLocale, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import { useJurisdictions } from "@/lib/jurisdiction";

/**
 * Whose rules apply at this lake, in one line: the licence, the limits and
 * the bait rules, where someone deciding where to fish is already looking.
 * The visiting angler in the 2026-10-29 persona doc fishes the way they did
 * at home; what gets them a ticket is a rule that differs here (fish as bait
 * in California, a licence from 16 rather than 18). Links only to pages
 * FishEye reviewed (knowledge/jurisdictions.py); nothing without a state.
 */
export function LakeRulesRow({ stateCode }: { stateCode: string | null | undefined }) {
  const states = useJurisdictions();
  const t = useT().rules;
  const locale = useLocale();
  const [baitOpen, setBaitOpen] = useState(false);
  const j = stateCode ? states?.find((s) => s.code === stateCode) : undefined;
  if (!j || (!j.license_url && !j.limits_url)) return null;
  const license = j.license_from_age ? t.licenseFrom(j.license_from_age) : t.license;

  return (
    <div className="lake-rules">
      <p>
        <strong>{t.title(localStateName(j.code, j.name, locale))}</strong>
        {j.license_url && (
          <a href={j.license_url} target="_blank" rel="noreferrer">
            {license} ↗
          </a>
        )}
        {j.limits_url && (
          <a href={j.limits_url} target="_blank" rel="noreferrer">
            {j.covered ? t.limits : t.regulations} ↗
          </a>
        )}
        {j.bait_rules.length > 0 && (
          <button type="button" className="link-btn" aria-expanded={baitOpen} onClick={() => setBaitOpen((o) => !o)}>
            {t.baitRules}
          </button>
        )}
      </p>
      {baitOpen && (
        <ul lang="en">
          {j.bait_rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
