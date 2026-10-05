"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const ACCEPT = ["image/jpeg", "image/png", "image/webp"];

/**
 * Pick up to `max` photos: click or drop, with previews and remove buttons.
 * Checks type and size in the browser for instant feedback only — the
 * server decodes and re-encodes every photo regardless (services/media.py).
 */
export function PhotoPicker({
  files,
  onChange,
  max,
  maxMb,
  disabled = false,
}: {
  files: File[];
  onChange: (files: File[]) => void;
  max: number;
  maxMb: number;
  disabled?: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  function add(list: FileList | File[]) {
    const incoming = Array.from(list);
    const bad = incoming.find((f) => !ACCEPT.includes(f.type));
    const big = incoming.find((f) => f.size > maxMb * 1024 * 1024);
    if (bad) setProblem(`"${bad.name}" isn't a JPEG, PNG or WebP photo.`);
    else if (big) setProblem(`"${big.name}" is over ${maxMb} MB.`);
    else setProblem(null);
    const ok = incoming.filter((f) => ACCEPT.includes(f.type) && f.size <= maxMb * 1024 * 1024);
    const next = [...files, ...ok].slice(0, max);
    if (files.length + ok.length > max) setProblem(`Up to ${max} photos per pin.`);
    onChange(next);
  }

  return (
    <div className="photo-picker">
      <div className="photo-grid">
        {files.map((f, i) => (
          <figure key={`${f.name}-${i}`} className="photo-thumb">
            {/* A local preview (blob: URL) of a file not yet uploaded. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={previews[i]} alt={`Selected photo ${i + 1}`} />
            <button
              type="button"
              className="photo-remove"
              aria-label={`Remove photo ${i + 1}`}
              disabled={disabled}
              onClick={() => onChange(files.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </figure>
        ))}
        {files.length < max && (
          <button
            type="button"
            className={drag ? "photo-drop dragging" : "photo-drop"}
            disabled={disabled}
            onClick={() => input.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              add(e.dataTransfer.files);
            }}
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <rect x="3" y="5" width="18" height="14" rx="3" />
              <circle cx="9" cy="10" r="1.6" />
              <path d="M5 17l5-5 4 4 2-2 3 3" />
            </svg>
            <span>{files.length === 0 ? "Add photos" : "Add more"}</span>
            <small>
              {files.length}/{max}
            </small>
          </button>
        )}
      </div>
      <input
        ref={input}
        type="file"
        accept={ACCEPT.join(",")}
        multiple
        hidden
        onChange={(e) => {
          if (e.target.files) add(e.target.files);
          e.target.value = "";
        }}
      />
      <p className="hint">
        Location data inside photos is removed when you upload.
        {problem && <span className="hint-warn"> {problem}</span>}
      </p>
    </div>
  );
}
