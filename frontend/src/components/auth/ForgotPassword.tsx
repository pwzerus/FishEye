"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { getProviders, requestPasswordReset } from "@/lib/api/session";
import { LEGAL } from "@/lib/legal";

/** Ask for a reset link (backend services/password_reset.py). The answer is the
 * same whether or not the address has an account. While the server can't send
 * mail, it says who to ask, rather than promise a message that never comes. */
export function ForgotPassword() {
  const t = useT().auth;
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [canEmail, setCanEmail] = useState<boolean | null>(null);

  useEffect(() => {
    getProviders()
      .then((p) => setCanEmail(p.email_ready ?? false))
      .catch(() => setCanEmail(true));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await requestPasswordReset(email.trim());
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.checkFailed);
    } finally {
      setBusy(false);
    }
  }

  if (canEmail === false) {
    return (
      <div className="auth-card verify-card reveal">
        <h1>{t.forgotTitle}</h1>
        <p className="muted">{t.forgotNoMail}</p>
        <div className="verify-actions">
          <a className="btn btn-primary" href={`mailto:${LEGAL.contactEmail}`}>
            {LEGAL.contactEmail}
          </a>
          <Link href="/login" className="btn btn-ghost">
            {t.backToSignIn}
          </Link>
        </div>
      </div>
    );
  }
  if (sent) {
    return (
      <div className="auth-card verify-card reveal">
        <h1>{t.resetSentTitle}</h1>
        <p className="muted">{t.resetSentText(email.trim())}</p>
        <div className="verify-actions">
          <Link href="/login" className="btn btn-primary">
            {t.backToSignIn}
          </Link>
          <button type="button" className="btn btn-ghost" onClick={() => setSent(false)}>
            {t.tryAnotherEmail}
          </button>
        </div>
      </div>
    );
  }
  return (
    <div className="auth-card reveal">
      <h1>{t.forgotTitle}</h1>
      <p className="muted auth-sub">{t.forgotSub}</p>
      <form className="auth-form" onSubmit={submit} noValidate>
        <label className="field">
          <span>{t.email}</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            inputMode="email"
            autoFocus
            required
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy || !email.trim().includes("@")}>
          {busy ? <span className="spinner" aria-hidden="true" /> : null}
          {t.sendResetLink}
        </button>
      </form>
      <p className="auth-foot muted">
        <Link href="/login" className="text-link">
          {t.backToSignIn}
        </Link>
      </p>
    </div>
  );
}
