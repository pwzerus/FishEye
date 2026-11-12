"use client";

import { useSyncExternalStore } from "react";

import { useT } from "@/i18n/client";

/**
 * Once, right after a new account is made: how to keep FishEye on the
 * phone's home screen, where it opens in its own window like an app
 * (app/manifest.ts): Safari on an iPhone, Chrome on Android, said the same
 * way. Not shown where FishEye already runs from the home screen.
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

function remember(value: "show" | "done"): void {
  try {
    window.localStorage.setItem(KEY, value);
  } catch {
    /* then it's just for this page */
  }
  window.dispatchEvent(new Event(EVENT));
}

/** An account was just made here: show the tip, once per phone (a second
 * account made on it doesn't bring it back). */
export function offerInstallTip(): void {
  if (read() !== "done") remember("show");
}

/** Opened from the home screen already (iPhones say so their own way). */
function fromHomeScreen(): boolean {
  const iphone = (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return iphone || window.matchMedia?.("(display-mode: standalone)").matches === true;
}

export function InstallTip() {
  const t = useT().installTip;
  // Nothing on the server or while hydrating, like the server's page.
  const state = useSyncExternalStore(subscribe, read, () => "");
  if (state !== "show" || fromHomeScreen()) return null;
  return (
    <aside className="install-tip" aria-label={t.title}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="install-tip-icon" src="/icons/icon-192.png" alt="" width={44} height={44} />
      <div className="install-tip-body">
        <strong>{t.title}</strong>
        <p>{t.iphone}</p>
        <p>{t.android}</p>
      </div>
      <button type="button" className="btn btn-primary btn-sm install-tip-ok" onClick={() => remember("done")}>
        {t.ok}
      </button>
    </aside>
  );
}
