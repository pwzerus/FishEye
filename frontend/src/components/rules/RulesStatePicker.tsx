"use client";

import { useRouter } from "next/navigation";

import { useLocale, useLocaleTag, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import { rememberState, useJurisdictions } from "@/lib/jurisdiction";
import { stateSlug } from "@/lib/stateSlug";

/**
 * On one state's rules page (/rules/texas): pick another state and its page
 * opens. The pick is remembered like the "Fishing in" picker elsewhere, so the
 * handbook and the guides follow it.
 */
export function RulesStatePicker({ code }: { code: string }) {
  const list = useJurisdictions();
  const router = useRouter();
  const t = useT().stateRules;
  const locale = useLocale();
  const tag = useLocaleTag();
  if (!list) return null; // the page itself doesn't need it
  const name = (j: { code: string; name: string }) => localStateName(j.code, j.name, locale);
  const byName = <T extends { code: string; name: string }>(a: T, b: T) => name(a).localeCompare(name(b), tag);
  const covered = list.filter((j) => j.covered).sort(byName);
  const rest = list.filter((j) => !j.covered).sort(byName);
  return (
    <label className="state-picker rules-state-picker">
      <span className="state-picker-label">{t.fishingIn}</span>
      <select
        value={code}
        onChange={(e) => {
          const j = list.find((x) => x.code === e.target.value);
          if (!j) return;
          rememberState(j.code);
          router.push(`/rules/${stateSlug(j.name)}`);
        }}
      >
        {covered.length > 0 && (
          <optgroup label={t.rulesWritten}>
            {covered.map((j) => (
              <option key={j.code} value={j.code}>
                {name(j)}
              </option>
            ))}
          </optgroup>
        )}
        <optgroup label={t.rulesNotYet}>
          {rest.map((j) => (
            <option key={j.code} value={j.code}>
              {name(j)}
            </option>
          ))}
        </optgroup>
      </select>
    </label>
  );
}
