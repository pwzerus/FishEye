"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useT } from "@/i18n/client";

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
  firstLabel,
}: {
  files: File[];
  onChange: (files: File[]) => void;
  max: number;
  maxMb: number;
  disabled?: boolean;
  // Marks the first photo, e.g. "Catch photo": the one the fish is checked on.
  firstLabel?: string;
}) {
  const t = useT().catch;
  const input = useRef<HTMLInputElement>(null);
  const camera = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  // A phone opens its camera from a "capture" input; a desktop would just
  // show the same file chooser twice, so the button is for touch screens.
  const [touch] = useState(() => typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)")?.matches === true);
  const [problem, setProblem] = useState<string | null>(null);
  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  function add(list: FileList | File[]) {
    const incoming = Array.from(list);
    const bad = incoming.find((f) => !ACCEPT.includes(f.type));
    const big = incoming.find((f) => f.size > maxMb * 1024 * 1024);
    if (bad) setProblem(t.badType(bad.name));
    else if (big) setProblem(t.tooBig(big.name, maxMb));
    else setProblem(null);
    const ok = incoming.filter((f) => ACCEPT.includes(f.type) && f.size <= maxMb * 1024 * 1024);
    const next = [...files, ...ok].slice(0, max);
    if (files.length + ok.length > max) setProblem(t.tooMany(max));
    onChange(next);
  }

  return (
    <div className="photo-picker">
      <div className="photo-grid">
        {files.map((f, i) => (
          <figure key={`${f.name}-${i}`} className="photo-thumb">
            {/* A local preview (blob: URL) of a file not yet uploaded. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={previews[i]} alt={t.selectedPhoto(i + 1)} />
            {i === 0 && firstLabel && <figcaption className="photo-first">{firstLabel}</figcaption>}
            <button
              type="button"
              className="photo-remove"
              aria-label={t.removePhoto(i + 1)}
              disabled={disabled}
              onClick={() => onChange(files.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </figure>
        ))}
        {files.length < max && touch && (
          <button type="button" className="photo-drop photo-camera" disabled={disabled} onClick={() => camera.current?.click()}>
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
              <circle cx="12" cy="13" r="3.5" />
            </svg>
            <span>{t.takePhoto}</span>
          </button>
        )}
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
            <span>{files.length === 0 ? t.addPhotos : t.addMore}</span>
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
      <input
        ref={camera}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(e) => {
          if (e.target.files) add(e.target.files);
          e.target.value = "";
        }}
      />
      <p className="hint">
        {t.locationRemoved}
        {problem && <span className="hint-warn"> {problem}</span>}
      </p>
    </div>
  );
}
