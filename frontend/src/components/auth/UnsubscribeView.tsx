"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { unsubscribeAlert } from "@/lib/api/session";

/** Where an alert email's unsubscribe link lands. A button, because mail
 * scanners open links: opening this page must not stop the alert by itself. */
export function UnsubscribeView() {
  const t = useT().alerts;
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(token ? null : t.unsubBad);
  const [busy, setBusy] = useState(false);

  return (
    <div className="auth-card">
      <h1>{t.unsubTitle}</h1>
      {done ? (
        <p>{done}</p>
      ) : error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : (
        <>
          <p className="muted">{t.unsubBody}</p>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                const r = await unsubscribeAlert(token);
                setDone(t.unsubDone(r.species_label, r.place));
              } catch (err) {
                setError(err instanceof ApiError && err.status === 404 ? t.unsubBad : t.failed);
              } finally {
                setBusy(false);
              }
            }}
          >
            {t.unsubButton}
          </button>
        </>
      )}
      <p>
        <Link href="/" className="text-link">
          FishEye
        </Link>
      </p>
    </div>
  );
}
