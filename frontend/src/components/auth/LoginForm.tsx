"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { FishArt } from "@/components/fish/FishArt";
import { offerInstallTip } from "@/components/InstallTip";
import { useToast } from "@/components/ui/Toast";
import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { getProviders, googleStartUrl, login, register } from "@/lib/api/session";
import { LEGAL } from "@/lib/legal";
import { useAuth } from "./AuthProvider";

type Mode = "signin" | "signup";

// Errors the Google callback sends back as ?error=… (backend app/api/auth.py)
// are worded in t.auth.oauth.

/** Only same-site paths — `next` comes from the URL, so it's untrusted. Only
 * visible ASCII, as the backend's _safe_next: a browser drops a tab or a
 * newline from a URL, so "/\t/evil.example" goes to //evil.example. */
export function safeNext(raw: string | null): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\")) return "/";
  if (!/^[!-~]+$/.test(raw)) return "/";
  if (raw.startsWith("/login")) return "/";
  return raw;
}

export function GoogleIcon() {
  return (
    <svg viewBox="0 0 48 48" width="18" height="18" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

export function LoginForm() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { user, loading, setUser } = useAuth();
  const t = useT().auth;
  const next = safeNext(params.get("next"));
  const [mode, setMode] = useState<Mode>(params.get("mode") === "signup" ? "signup" : "signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [name, setName] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(() => {
    const code = params.get("error");
    return code ? (t.oauth[code] ?? t.signInFailed) : null;
  });
  const [google, setGoogle] = useState(false);

  useEffect(() => {
    getProviders()
      .then((p) => setGoogle(p.google))
      .catch(() => setGoogle(false));
  }, []);

  // Already signed in (or just signed in via Google): go where they were headed.
  useEffect(() => {
    if (!loading && user) router.replace(next);
  }, [loading, user, next, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = mode === "signin" ? await login(email, password) : await register(email, password, name);
      setUser(u);
      if (mode === "signin") toast(t.welcomeBack(u.display_name));
      else {
        toast(u.verification_required ? t.welcomeConfirm(u.display_name) : t.welcome(u.display_name));
        // A new account: how to put FishEye on the phone's home screen, once.
        offerInstallTip();
      }
      router.replace(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.wrong);
      setBusy(false);
    }
  }

  const pwTooShort = mode === "signup" && password.length > 0 && password.length < 8;
  const pwDiffer = mode === "signup" && confirm.length > 0 && confirm !== password;

  return (
    <div className="auth-card reveal">
      <div className="auth-art" aria-hidden="true">
        <FishArt slug="bluegill" uid="auth-bg" className="swimming" />
      </div>
      <h1>{mode === "signin" ? t.titleSignIn : t.titleSignUp}</h1>
      <p className="muted auth-sub">{mode === "signin" ? t.subSignIn : t.subSignUp}</p>

      <div className="segmented auth-switch" role="tablist" aria-label={t.switchLabel}>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "signin"}
          className={mode === "signin" ? "segment active" : "segment"}
          onClick={() => {
            setMode("signin");
            setError(null);
          }}
        >
          {t.signIn}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "signup"}
          className={mode === "signup" ? "segment active" : "segment"}
          onClick={() => {
            setMode("signup");
            setError(null);
          }}
        >
          {t.createAccount}
        </button>
      </div>

      {google && (
        <>
          <a className="btn btn-ghost btn-google" href={googleStartUrl(next)}>
            <GoogleIcon /> {t.google}
          </a>
          <div className="or-rule">
            <span>{t.orEmail}</span>
          </div>
        </>
      )}

      <form className="auth-form" onSubmit={submit} noValidate>
        {mode === "signup" && (
          <label className="field">
            <span>{t.displayName}</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="nickname"
              maxLength={40}
              required
              placeholder={t.displayNameHint}
            />
          </label>
        )}
        <label className="field">
          <span>{t.email}</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            inputMode="email"
            required
          />
        </label>
        {/* The label names only the input; the show/hide button and the hint
            sit outside it, so the accessible name is just "Password". */}
        <div className="field">
          <label htmlFor="auth-password" className="field-label">
            {t.password}
          </label>
          <div className="pw-wrap">
            <input
              id="auth-password"
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              minLength={mode === "signup" ? 8 : undefined}
              required
              aria-describedby={mode === "signup" ? "pw-hint" : undefined}
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
          {mode === "signup" && (
            <small id="pw-hint" className={pwTooShort ? "hint hint-warn" : "hint"}>
              {t.pwHint}
            </small>
          )}
          {mode === "signin" && (
            <Link href="/forgot-password" className="text-link forgot-link">
              {t.forgotLink}
            </Link>
          )}
        </div>

        {mode === "signup" && (
          <div className="field">
            <label htmlFor="auth-confirm" className="field-label">
              {t.confirmPassword}
            </label>
            <input
              id="auth-confirm"
              type={showPw ? "text" : "password"}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
              aria-describedby={pwDiffer ? "pw-differ" : undefined}
            />
            {pwDiffer && (
              <small id="pw-differ" className="hint hint-warn" role="alert">
                {t.pwMismatch}
              </small>
            )}
          </div>
        )}

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="btn btn-primary auth-submit"
          disabled={busy || !email || !password || (mode === "signup" && confirm !== password)}
        >
          {busy ? <span className="spinner" aria-hidden="true" /> : null}
          {mode === "signin" ? t.signIn : t.createAccount}
        </button>
      </form>

      <p className="auth-legal muted">
        {t.legal1(LEGAL.minimumAge)}
        <Link href="/terms">{t.terms}</Link>
        {t.and}
        <Link href="/privacy">{t.privacy}</Link>
        {t.legalEnd}
      </p>

      <p className="auth-foot muted">
        {mode === "signin" ? t.newHere : t.haveAccount}
        <button type="button" className="link-btn" onClick={() => setMode(mode === "signin" ? "signup" : "signin")}>
          {mode === "signin" ? t.createAnAccount : t.signIn}
        </button>
        {" · "}
        <Link href="/" className="text-link">
          {t.backHome}
        </Link>
      </p>
    </div>
  );
}
