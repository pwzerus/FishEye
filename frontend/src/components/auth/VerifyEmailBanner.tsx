"use client";

import { useEffect, useState } from "react";

import { useToast } from "@/components/ui/Toast";
import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { sendVerificationEmail } from "@/lib/api/session";
import { useAuth } from "./AuthProvider";

/** Until the address is confirmed, sharing and reporting catches wait
 * (backend services/email_verification.py). Shown on the account page, and
 * at the top of the forms that would otherwise refuse only once filled in.
 * The link is usually opened in another tab or on the phone, so coming back
 * to this one checks again. */
export function VerifyEmailBanner({ email }: { email: string }) {
  const toast = useToast();
  const t = useT().auth;
  const { refresh } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const recheck = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", recheck);
    return () => document.removeEventListener("visibilitychange", recheck);
  }, [refresh]);

  return (
    <div className="verify-banner reveal" role="status">
      <div>
        <strong>{t.confirmEmail}</strong>
        <p>{t.confirmEmailText(email)}</p>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
      <button
        type="button"
        className="btn btn-primary btn-sm"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            await sendVerificationEmail();
            toast(t.linkSent);
          } catch (e) {
            setError(e instanceof ApiError ? e.message : t.sendFailed);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? t.sending : t.sendLink}
      </button>
    </div>
  );
}
