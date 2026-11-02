"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useToast } from "@/components/ui/Toast";
import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { checkPasswordReset, confirmPasswordReset } from "@/lib/api/session";
import { useAuth } from "./AuthProvider";

type Link_ = { kind: "checking" } | { kind: "good"; email: string } | { kind: "bad" };

/** Where the reset email's link lands. Checking the link doesn't use it up;
 * saving does, and signs this browser in. */
export function ResetPassword() {
  const params = useSearchParams();
  const token = params.get("token");
  const router = useRouter();
  const toast = useToast();
  const { setUser } = useAuth();
  const t = useT().auth;
  const [link, setLink] = useState<Link_>(() => (token ? { kind: "checking" } : { kind: "bad" }));
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let stale = false;
    checkPasswordReset(token)
      .then((r) => !stale && setLink(r.valid && r.email ? { kind: "good", email: r.email } : { kind: "bad" }))
      .catch(() => !stale && setLink({ kind: "bad" }));
    return () => {
      stale = true;
    };
  }, [token]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await confirmPasswordReset(token ?? "", password);
      setUser(user);
      toast(t.resetDone);
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) setLink({ kind: "bad" });
      else setError(err instanceof ApiError ? err.message : t.checkFailed);
      setBusy(false);
    }
  }

  if (link.kind === "checking") {
    return (
      <div className="auth-card verify-card reveal">
        <h1>{t.confirming}</h1>
        <p className="muted">{t.oneMoment}</p>
      </div>
    );
  }
  if (link.kind === "bad") {
    return (
      <div className="auth-card verify-card reveal">
        <h1>{t.linkFailed}</h1>
        <p className="form-error" role="alert">
          {t.resetBadLink}
        </p>
        <div className="verify-actions">
          <Link href="/forgot-password" className="btn btn-primary">
            {t.sendResetLink}
          </Link>
          <Link href="/login" className="btn btn-ghost">
            {t.backToSignIn}
          </Link>
        </div>
      </div>
    );
  }
  const tooShort = password.length > 0 && password.length < 8;
  return (
    <div className="auth-card reveal">
      <h1>{t.resetTitle}</h1>
      <p className="muted auth-sub">{t.resetFor(link.email)}</p>
      <form className="auth-form" onSubmit={submit} noValidate>
        {/* For password managers: which account this new password is for. */}
        <input type="email" value={link.email} autoComplete="username" readOnly hidden />
        <div className="field">
          <label htmlFor="reset-password" className="field-label">
            {t.resetNewPassword}
          </label>
          <div className="pw-wrap">
            <input
              id="reset-password"
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              autoFocus
              required
              aria-describedby="reset-hint"
            />
            <button
              type="button"
              className="pw-toggle"
              onClick={() => setShowPw((v) => !v)}
              aria-label={showPw ? t.hidePassword : t.showPassword}
            >
              {showPw ? t.hide : t.show}
            </button>
          </div>
          <small id="reset-hint" className={tooShort ? "hint hint-warn" : "hint"}>
            {t.pwHint}
          </small>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy || password.length < 8}>
          {busy ? <span className="spinner" aria-hidden="true" /> : null}
          {t.saveNewPassword}
        </button>
      </form>
    </div>
  );
}
