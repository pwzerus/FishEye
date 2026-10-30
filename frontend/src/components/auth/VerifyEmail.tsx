"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { confirmEmail } from "@/lib/api/session";
import { useAuth } from "./AuthProvider";

type State = { kind: "checking" } | { kind: "done"; email: string } | { kind: "failed"; message: string };

/** Where the confirmation email's link lands (backend services/email_verification.py). */
export function VerifyEmail() {
  const params = useSearchParams();
  const token = params.get("token");
  const { user, refresh } = useAuth();
  const all = useT();
  const t = all.auth;
  const [state, setState] = useState<State>(() =>
    token ? { kind: "checking" } : { kind: "failed", message: t.missingCode },
  );
  // A link works once: never send it twice (React runs effects twice in dev).
  const sent = useRef(false);

  useEffect(() => {
    if (!token || sent.current) return;
    sent.current = true;
    confirmEmail(token)
      .then((r) => {
        setState({ kind: "done", email: r.email });
        void refresh();
      })
      .catch((e) =>
        setState({ kind: "failed", message: e instanceof ApiError ? e.message : t.checkFailed }),
      );
  }, [token, refresh, t.checkFailed]);

  return (
    <div className="auth-card verify-card reveal">
      {state.kind === "checking" && (
        <>
          <h1>{t.confirming}</h1>
          <p className="muted">{t.oneMoment}</p>
        </>
      )}
      {state.kind === "done" && (
        <>
          <h1>{t.confirmed}</h1>
          <p className="muted">{t.confirmedText(state.email)}</p>
          <div className="verify-actions">
            <Link href="/map" className="btn btn-primary">
              {all.catch.shareTitle}
            </Link>
            {user ? (
              <Link href="/account" className="btn btn-ghost">
                {t.yourAccount}
              </Link>
            ) : (
              <Link href="/login" className="btn btn-ghost">
                {t.signIn}
              </Link>
            )}
          </div>
        </>
      )}
      {state.kind === "failed" && (
        <>
          <h1>{t.linkFailed}</h1>
          <p className="form-error" role="alert">
            {state.message}
          </p>
          <div className="verify-actions">
            <Link href={user ? "/account" : "/login?next=/account"} className="btn btn-primary">
              {user ? t.sendLink : t.signInToSend}
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
