"use client";

import { useLocale, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import { rememberState, useJurisdictions, useSelectedState } from "@/lib/jurisdiction";

/**
 * "Fishing in: [state]". What the person picks decides whose rules Ask,
 * the handbook and the guides show (backend docs/adr/0027). Optional:
 * left unset, nothing is hidden.
 */
export function StatePicker({ className, label }: { className?: string; label?: string }) {
  const state = useSelectedState();
  const list = useJurisdictions();
  const t = useT().stateRules;
  const locale = useLocale();
  if (!list) return null; // no list, no picker: the rest still works
  const name = (j: { code: string; name: string }) => localStateName(j.code, j.name, locale);
  const byName = <T extends { code: string; name: string }>(a: T, b: T) => name(a).localeCompare(name(b), locale);
  const covered = list.filter((j) => j.covered).sort(byName);
  const rest = list.filter((j) => !j.covered).sort(byName);
  return (
    <label className={className ?? "state-picker"}>
      <span className="state-picker-label">{label ?? t.fishingIn}</span>
      <select value={state ?? ""} onChange={(e) => rememberState(e.target.value || null)}>
        <option value="">{t.anyState}</option>
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
