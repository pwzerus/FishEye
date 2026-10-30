"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { LOCALES, LOCALE_COOKIE, LOCALE_NAMES, LOCALE_SHORT, LOCALE_TAGS, preferredLocale, type Locale } from "@/i18n/config";
import { saveLocale, useLocale, useT } from "@/i18n/client";
import { MESSAGES } from "@/i18n/messages";

function useSwitch() {
  const router = useRouter();
  return (locale: Locale) => {
    saveLocale(locale);
    document.documentElement.lang = LOCALE_TAGS[locale];
    router.refresh();
  };
}

/** The header's language button: the current language, and the others. */
export function LanguageMenu() {
  const t = useT();
  const locale = useLocale();
  const choose = useSwitch();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="lang-menu" ref={ref}>
      <button
        type="button"
        className="lang-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`${t.language.label}: ${LOCALE_NAMES[locale]}`}
        onClick={() => setOpen((v) => !v)}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9M12 3c-2.5 2.6-3.8 5.6-3.8 9s1.3 6.4 3.8 9" />
        </svg>
        <span>{LOCALE_SHORT[locale]}</span>
      </button>
      {open && (
        <div className="menu-pop lang-pop" role="menu" aria-label={t.language.menu}>
          {LOCALES.map((l) => (
            <button
              key={l}
              type="button"
              role="menuitemradio"
              aria-checked={l === locale}
              lang={LOCALE_TAGS[l]}
              className={l === locale ? "menu-item active" : "menu-item"}
              onClick={() => {
                setOpen(false);
                if (l !== locale) choose(l);
              }}
            >
              {LOCALE_NAMES[l]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const DISMISSED = "fisheye.langSuggest";

function hasChoice(): boolean {
  return document.cookie.split("; ").some((c) => c.startsWith(`${LOCALE_COOKIE}=`));
}

function dismissed(): boolean {
  try {
    return window.localStorage.getItem(DISMISSED) === "1";
  } catch {
    return false;
  }
}

const noop = () => () => {};

/** For a browser set to one of the site's other languages that hasn't
 * chosen yet: one line, in that language, offering it. English stays until
 * they say. */
export function LanguageSuggestion() {
  const locale = useLocale();
  const choose = useSwitch();
  const offer = useSyncExternalStore(
    noop,
    () => (hasChoice() || dismissed() ? null : preferredLocale(navigator.languages ?? [navigator.language])),
    () => null,
  );
  const [hidden, setHidden] = useState(false);
  if (!offer || offer === locale || hidden) return null;
  const m = MESSAGES[offer];

  function keep() {
    setHidden(true);
    try {
      window.localStorage.setItem(DISMISSED, "1");
    } catch {
      // private mode: it asks again next visit
    }
  }

  return (
    <div className="lang-suggest" role="region" aria-label={m.language.label} lang={LOCALE_TAGS[offer]}>
      <span>{m.language.suggest}</span>
      <button type="button" className="btn btn-primary btn-sm" onClick={() => choose(offer)}>
        {m.language.use(LOCALE_NAMES[offer])}
      </button>
      <button type="button" className="btn btn-ghost btn-sm" onClick={keep}>
        {m.language.keepEnglish}
      </button>
    </div>
  );
}
