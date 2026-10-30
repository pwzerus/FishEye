"use client";

import { useState } from "react";

import { Modal } from "@/components/ui/Modal";
import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { googleStartUrl, reauth } from "@/lib/api/session";
import { useAuth } from "./AuthProvider";
import { GoogleIcon } from "./LoginForm";

/**
 * "Confirm it's you" before a sensitive account change on a session that
 * isn't recent (the server answers 403 + X-Reauth-Required).
 *
 * Password accounts confirm here and the change is retried right away.
 * Google-only accounts confirm by signing in with Google again, which is a
 * full-page round trip, so they come back to `returnTo` and repeat the
 * change themselves.
 */
export function ReauthDialog({
  onClose,
  onConfirmed,
  returnTo = "/account",
  action,
}: {
  onClose: () => void;
  /** Runs after a successful password confirmation (e.g. retry the change). */
  onConfirmed?: () => Promise<void> | void;
  returnTo?: string;
  action?: string;
}) {
  const { user, setUser } = useAuth();
  const all = useT();
  const t = all.auth;
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const withPassword = user?.has_password ?? false;

  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      setUser(await reauth(password));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.confirmFailed);
      setBusy(false);
      return;
    }
    try {
      await onConfirmed?.();
    } finally {
      onClose();
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={t.confirmTitle}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            {all.common.cancel}
          </button>
          {withPassword ? (
            <button type="submit" form="reauth-form" className="btn btn-primary btn-sm" disabled={busy || !password}>
              {busy ? t.checking : t.confirm}
            </button>
          ) : (
            <a className="btn btn-primary btn-sm btn-with-icon" href={googleStartUrl(returnTo)}>
              <GoogleIcon /> {t.google}
            </a>
          )}
        </>
      }
    >
      <div className="pin-form">
        <p className="muted">{t.confirmWith(action ?? t.actionDefault, withPassword)}</p>
        {withPassword && (
          <form
            id="reauth-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (!busy && password) void confirm();
            }}
          >
            <label className="field">
              <span>{t.password}</span>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
              />
            </label>
          </form>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
