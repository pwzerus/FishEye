"use client";

import type { CSSProperties, ReactNode } from "react";

export interface SegmentOption<T extends string> {
  value: T;
  label: ReactNode;
  disabled?: boolean;
  title?: string;
}

/** Equal-width choices with a thumb that slides to the one chosen. The thumb
 * is placed by CSS from the chosen index (app/catches.css, .seg). */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
  className,
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  className?: string;
}) {
  const at = Math.max(
    0,
    options.findIndex((o) => o.value === value),
  );
  return (
    <div
      className={className ? `seg ${className}` : "seg"}
      role="tablist"
      aria-label={label}
      style={{ "--n": options.length, "--at": at } as CSSProperties}
    >
      <span className="seg-thumb" aria-hidden="true" />
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="tab"
          aria-selected={o.value === value}
          disabled={o.disabled}
          title={o.title}
          className={o.value === value ? "seg-item active" : "seg-item"}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
