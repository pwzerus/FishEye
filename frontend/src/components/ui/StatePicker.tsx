"use client";

import { rememberState, useJurisdictions, useSelectedState } from "@/lib/jurisdiction";

/**
 * "Fishing in: [state]". What the person picks decides whose rules Ask,
 * the handbook and the guides show (backend docs/adr/0027). Optional:
 * left unset, nothing is hidden.
 */
export function StatePicker({ className }: { className?: string }) {
  const state = useSelectedState();
  const list = useJurisdictions();
  if (!list) return null; // no list, no picker: the rest still works
  const covered = list.filter((j) => j.covered);
  const rest = list.filter((j) => !j.covered);
  return (
    <label className={className ?? "state-picker"}>
      <span className="state-picker-label">Fishing in</span>
      <select value={state ?? ""} onChange={(e) => rememberState(e.target.value || null)}>
        <option value="">Any state</option>
        {covered.length > 0 && (
          <optgroup label="Rules written">
            {covered.map((j) => (
              <option key={j.code} value={j.code}>
                {j.name}
              </option>
            ))}
          </optgroup>
        )}
        <optgroup label="Rules not written yet">
          {rest.map((j) => (
            <option key={j.code} value={j.code}>
              {j.name}
            </option>
          ))}
        </optgroup>
      </select>
    </label>
  );
}
