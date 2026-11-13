"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useLocaleTag, useT } from "@/i18n/client";
import { LEGAL } from "@/lib/legal";

/**
 * "Our terms of use changed. The new ones apply to you from …", for accounts
 * made before the terms last changed (LEGAL.updated). Both the earlier terms
 * and the new ones promise a notice on the site before a change that matters
 * applies to someone who already has an account (app/terms, "Changes"); this
 * is that notice. It shows until it's dismissed, and stops on its own a
 * month after the change applies.
 */
const DISMISSED = `fisheye.termsNotice.${LEGAL.updatedIso}`;
const SHOW_DAYS_AFTER = 30;
const DAY = 24 * 60 * 60 * 1000;

function utc(day: string): number {
  return Date.parse(`${day}T00:00:00Z`);
}

/** Not dismissed, and not yet a month past the date the change applies. */
function stillShown(): boolean {
  if (Date.now() > utc(LEGAL.existingUsersFromIso) + SHOW_DAYS_AFTER * DAY) return false;
  try {
    return window.localStorage.getItem(DISMISSED) !== "1";
  } catch {
    return true;
  }
}

const noSubscription = () => () => {};

export function TermsNotice() {
  const { user } = useAuth();
  const t = useT().legal;
  const tag = useLocaleTag();
  const path = usePathname();
  const shown = useSyncExternalStore(noSubscription, stillShown, () => false);
  const [hidden, setHidden] = useState(false);

  const before = user && Date.parse(user.created_at) < utc(LEGAL.updatedIso);
  if (!shown || hidden || !before || path === "/terms") return null;

  const date = new Intl.DateTimeFormat(tag, { dateStyle: "long", timeZone: "UTC" }).format(
    utc(LEGAL.existingUsersFromIso),
  );

  function dismiss() {
    setHidden(true);
    try {
      window.localStorage.setItem(DISMISSED, "1");
    } catch {
      // private mode: it shows again next visit
    }
  }

  return (
    <div className="terms-notice" role="region" aria-label={t.terms}>
      <span>{t.changed(date)}</span>
      <Link href="/terms" className="btn btn-primary btn-sm" onClick={dismiss}>
        {t.readThem}
      </Link>
      <button type="button" className="btn btn-ghost btn-sm" onClick={dismiss}>
        {t.gotIt}
      </button>
    </div>
  );
}
