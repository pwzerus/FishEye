"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { useT } from "@/i18n/client";

type Tone = "success" | "error" | "info";
interface ToastItem {
  id: number;
  tone: Tone;
  text: string;
  leaving: boolean;
}

const ToastContext = createContext<((text: string, tone?: Tone) => void) | null>(null);
const VISIBLE_MS = 3800;
const EXIT_MS = 220;
// Kana, CJK ideographs, Hangul syllables.
const CJK_RE = /[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/g;

// A longer message stays up long enough to read: about 15 characters a
// second, a Chinese, Japanese or Korean character counting as three.
function visibleMs(text: string): number {
  const wide = text.match(CJK_RE)?.length ?? 0;
  return Math.max(VISIBLE_MS, 1000 + ((text.length + 2 * wide) / 15) * 1000);
}

/** Small confirmations ("Pin saved"). Announced politely to screen readers. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const dismissLabel = useT().common.dismiss;

  const dismiss = useCallback((id: number) => {
    setItems((all) => all.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
    setTimeout(() => setItems((all) => all.filter((t) => t.id !== id)), EXIT_MS);
  }, []);

  const show = useCallback(
    (text: string, tone: Tone = "success") => {
      const id = nextId.current++;
      setItems((all) => [...all.slice(-2), { id, tone, text, leaving: false }]);
      setTimeout(() => dismiss(id), visibleMs(text));
    },
    [dismiss],
  );

  const value = useMemo(() => show, [show]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}${t.leaving ? " leaving" : ""}`}>
            <span className="toast-dot" aria-hidden="true" />
            <span>{t.text}</span>
            <button type="button" className="toast-close" aria-label={dismissLabel} onClick={() => dismiss(t.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}

/** For a small widget used on many pages: the toast where the app has its
 * provider, nothing where it doesn't (a test rendering the widget alone). */
export function useOptionalToast() {
  return useContext(ToastContext);
}
