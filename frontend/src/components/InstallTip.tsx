"use client";

import { useSyncExternalStore } from "react";

import { useT } from "@/i18n/client";

/**
 * After signing in or making an account on a phone: how to keep FishEye on
 * the home screen, where it opens in its own window like an app
 * (app/manifest.ts): Safari on an iPhone, Chrome on Android, said the same
 * way. "Got it" hides it until the next sign-in, "Don't show again" for good
 * (the product owner, 2026-11-13). Not shown where FishEye already runs from
 * the home screen, nor on a computer, which has no home screen to add it to.
 */
const KEY = "fisheye.installTip";
const EVENT = "fisheye:installTip";

function read(): string {
  try {
    return window.localStorage.getItem(KEY) ?? "";
  } catch {
    return ""; // private window, blocked storage
  }
}

function subscribe(changed: () => void): () => void {
  window.addEventListener(EVENT, changed);
  window.addEventListener("storage", changed);
  return () => {
    window.removeEventListener(EVENT, changed);
    window.removeEventListener("storage", changed);
  };
}

// "show": waiting to be seen; "done": seen, back at the next sign-in;
// "never": don't show again.
function remember(value: "show" | "done" | "never"): void {
  try {
    window.localStorage.setItem(KEY, value);
  } catch {
    /* then it's just for this page */
  }
  window.dispatchEvent(new Event(EVENT));
}

/** Someone just signed in or made an account here: show the tip, unless
 * they asked never to see it again. */
export function offerInstallTip(): void {
  if (read() !== "never") remember("show");
}

/** Opened from the home screen already (iPhones say so their own way). */
function fromHomeScreen(): boolean {
  const iphone = (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return iphone || window.matchMedia?.("(display-mode: standalone)").matches === true;
}

/** A mouse or trackpad: a computer, with no home screen to add FishEye to. */
function onComputer(): boolean {
  return window.matchMedia?.("(pointer: fine)").matches === true;
}

export function InstallTip() {
  const t = useT().installTip;
  // Nothing on the server or while hydrating, like the server's page.
  const state = useSyncExternalStore(subscribe, read, () => "");
  if (state !== "show" || fromHomeScreen() || onComputer()) return null;
  return (
    <aside className="install-tip" aria-label={t.title}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="install-tip-icon" src="/icons/icon-192.png" alt="" width={44} height={44} />
      <div className="install-tip-body">
        <strong>{t.title}</strong>
        <p>{t.iphone}</p>
        <p>{t.android}</p>
      </div>
      <div className="install-tip-actions">
        <button type="button" className="btn btn-primary btn-sm install-tip-ok" onClick={() => remember("done")}>
          {t.ok}
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => remember("never")}>
          {t.never}
        </button>
      </div>
    </aside>
  );
}
