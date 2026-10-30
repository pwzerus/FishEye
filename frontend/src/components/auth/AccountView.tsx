"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { PinCard } from "@/components/community/PinCard";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import {
  changePassword,
  deleteAccount,
  disconnectGoogle,
  getProviders,
  googleStartUrl,
  isReauthRequired,
  listPins,
  sendVerificationEmail,
  updateProfile,
} from "@/lib/api/session";
import type { PinSummary } from "@/lib/api/types";
import { initials } from "./AccountMenu";
import { useAuth } from "./AuthProvider";
import { ReauthDialog } from "./ReauthDialog";

// Leaflet needs `window`: the map loads in the browser only.
const MyCatchesMap = dynamic(() => import("@/components/community/MyCatchesMap"), {
  ssr: false,
  loading: () => <div className="sk" style={{ height: "100%" }} />,
});

/** What to do once the user has confirmed it's them. */
interface ReauthRequest {
  action: string;
  retry?: () => Promise<void> | void;
}

/** Until the address is confirmed, sharing and reporting catches wait
 * (backend services/email_verification.py). */
function VerifyEmailBanner({ email }: { email: string }) {
  const toast = useToast();
  const t = useT().auth;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
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

function Section({ id, title, children, tone }: { id?: string; title: string; children: React.ReactNode; tone?: "danger" }) {
  return (
    <section id={id} className={tone === "danger" ? "acct-section acct-danger" : "acct-section"}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function AccountView() {
  const { user, loading, setUser, signOut } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const toast = useToast();
  const all = useT();
  const t = all.auth;
  const [pins, setPins] = useState<PinSummary[] | null>(null);
  const [google, setGoogle] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const [delOpen, setDelOpen] = useState(false);
  // Connecting a new Google account from an old session bounces back with
  // ?error=reauth_required: confirm, then go straight back to Google.
  const [reauthFor, setReauthFor] = useState<ReauthRequest | null>(() =>
    params.get("error") === "reauth_required"
      ? { action: t.actionConnect, retry: () => window.location.assign(googleStartUrl("/account")) }
      : null,
  );
  const announced = useRef(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login?next=/account");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    listPins({ mine: true, limit: 200 }).then(setPins).catch(() => setPins([]));
    getProviders().then((p) => setGoogle(p.google)).catch(() => undefined);
  }, [user]);

  // One-time messages from the Google callback redirect.
  useEffect(() => {
    if (announced.current) return;
    announced.current = true;
    if (params.get("connected") === "google") toast(t.googleConnected);
    const err = params.get("error");
    if (err && err !== "reauth_required") toast(t.callback[err] ?? t.didntWork, "error");
  }, [params, toast, t]);

  if (loading || !user) {
    return (
      <div aria-busy="true">
        <div className="sk sk-title" />
        <div className="sk sk-line" />
      </div>
    );
  }

  const counts = {
    public: pins?.filter((p) => p.visibility === "public" && p.status === "published").length ?? 0,
    private: pins?.filter((p) => p.visibility === "private").length ?? 0,
  };

  return (
    <>
      <header className="acct-hero reveal">
        <span className="acct-avatar" aria-hidden="true">
          {initials(user.display_name)}
        </span>
        <div>
          <h1>{user.display_name}</h1>
          <p className="muted">
            {user.email}
            {user.role === "admin" && (
              <>
                {" · "}
                <Link href="/admin" className="text-link">
                  {all.account.admin}
                </Link>
              </>
            )}
          </p>
        </div>
        <div className="acct-stats">
          <div>
            <strong>{pins?.length ?? "–"}</strong>
            <span>{t.statCatches}</span>
          </div>
          <div>
            <strong>{counts.public}</strong>
            <span>{t.statPublic}</span>
          </div>
          <div>
            <strong>{counts.private}</strong>
            <span>{t.statPrivate}</span>
          </div>
        </div>
      </header>

      {user.verification_required && <VerifyEmailBanner email={user.email} />}

      <div className="acct-grid">
        <div className="acct-col">
          <Section title={t.profile}>
            {/* Keyed on the saved name so the field resets after a save. */}
            <ProfileForm key={user.display_name} initial={user.display_name} />
          </Section>

          <Section title={t.methods}>
            <ul className="method-list">
              <li>
                <div>
                  <strong>{t.password}</strong>
                  <span className="muted">{user.has_password ? t.set : t.notSet}</span>
                </div>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPwOpen(true)}>
                  {user.has_password ? t.change : t.setPassword}
                </button>
              </li>
              {(google || user.google_connected) && (
                <li>
                  <div>
                    <strong>Google</strong>
                    <span className="muted">{user.google_connected ? t.connected : t.notConnected}</span>
                  </div>
                  {user.google_connected ? (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={!user.has_password}
                      title={user.has_password ? undefined : t.passwordFirst}
                      onClick={async () => {
                        const run = async () => {
                          setUser(await disconnectGoogle());
                          toast(t.googleDisconnected, "info");
                        };
                        try {
                          await run();
                        } catch (err) {
                          if (isReauthRequired(err)) setReauthFor({ action: t.actionDisconnect, retry: run });
                          else toast(err instanceof ApiError ? err.message : t.disconnectFailed, "error");
                        }
                      }}
                    >
                      {t.disconnect}
                    </button>
                  ) : (
                    <a className="btn btn-ghost btn-sm" href={googleStartUrl("/account")}>
                      {t.connect}
                    </a>
                  )}
                </li>
              )}
            </ul>
          </Section>

          <Section title={t.deleteAccount} tone="danger">
            <p className="muted">{t.deleteText}</p>
            <button type="button" className="btn btn-danger btn-sm" onClick={() => setDelOpen(true)}>
              {t.deleteMine}
            </button>
          </Section>
        </div>

        <Section id="pins" title={t.myCatches}>
          {pins === null ? (
            <div className="sk" style={{ height: 180 }} />
          ) : pins.length === 0 ? (
            <div className="empty-state compact">
              <p className="muted">{t.noCatches}</p>
              <Link href="/map?addPin=1" className="btn btn-primary btn-sm">
                {all.catch.shareTitle}
              </Link>
            </div>
          ) : (
            <>
            <div className="acct-map" aria-label={t.catchesMap}>
              <MyCatchesMap pins={pins} />
            </div>
            <ul className="pin-grid pin-grid-compact">
              {pins.map((p, i) => (
                <li key={p.id}>
                  <PinCard pin={p} index={i} />
                </li>
              ))}
            </ul>
            </>
          )}
        </Section>
      </div>

      {pwOpen && (
        <PasswordDialog
          hasPassword={user.has_password}
          onClose={() => setPwOpen(false)}
          onReauth={() => {
            setPwOpen(false);
            setReauthFor({ action: t.actionPassword });
          }}
        />
      )}
      {delOpen && (
        <DeleteDialog
          hasPassword={user.has_password}
          onClose={() => setDelOpen(false)}
          onReauth={() => {
            setDelOpen(false);
            setReauthFor({ action: t.actionDelete });
          }}
          onDeleted={async () => {
            await signOut().catch(() => undefined);
            toast(t.deleted, "info");
            router.replace("/");
          }}
        />
      )}
      {reauthFor && (
        <ReauthDialog
          action={reauthFor.action}
          onClose={() => setReauthFor(null)}
          onConfirmed={async () => {
            try {
              await reauthFor.retry?.();
            } catch (err) {
              toast(err instanceof ApiError ? err.message : t.didntWork, "error");
            }
          }}
        />
      )}
    </>
  );
}

function ProfileForm({ initial }: { initial: string }) {
  const { setUser } = useAuth();
  const toast = useToast();
  const all = useT();
  const t = all.auth;
  const [name, setName] = useState(initial);
  const [saving, setSaving] = useState(false);
  return (
    <form
      className="inline-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
          setUser(await updateProfile(name));
          toast(t.nameUpdated);
        } catch (err) {
          toast(err instanceof ApiError ? err.message : t.saveFailed, "error");
          setSaving(false);
        }
      }}
    >
      <label className="field">
        <span>{t.displayName}</span>
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={40} />
      </label>
      <button type="submit" className="btn btn-primary btn-sm" disabled={saving || name.trim() === initial}>
        {all.common.save}
      </button>
    </form>
  );
}

function PasswordDialog({
  hasPassword,
  onClose,
  onReauth,
}: {
  hasPassword: boolean;
  onClose: () => void;
  onReauth: () => void;
}) {
  const { setUser } = useAuth();
  const toast = useToast();
  const all = useT();
  const t = all.auth;
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <Modal
      open
      onClose={onClose}
      title={hasPassword ? t.changePassword : t.setPassword}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            {all.common.cancel}
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={busy || next.length < 8 || (hasPassword && !current)}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                setUser(await changePassword(next, hasPassword ? current : undefined));
                toast(t.passwordSaved);
                onClose();
              } catch (err) {
                if (isReauthRequired(err)) return onReauth();
                setError(err instanceof ApiError ? err.message : t.saveFailed);
                setBusy(false);
              }
            }}
          >
            {all.common.save}
          </button>
        </>
      }
    >
      <div className="pin-form">
        {hasPassword && (
          <label className="field">
            <span>{t.currentPassword}</span>
            <input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          </label>
        )}
        <div className="field">
          <label htmlFor="acct-new-password" className="field-label">
            {t.newPassword}
          </label>
          <input
            id="acct-new-password"
            type="password"
            autoComplete="new-password"
            aria-describedby="acct-new-password-hint"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
          <small id="acct-new-password-hint" className="hint">
            {t.newPasswordHint}
          </small>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}

function DeleteDialog({
  hasPassword,
  onClose,
  onDeleted,
  onReauth,
}: {
  hasPassword: boolean;
  onClose: () => void;
  onDeleted: () => void;
  onReauth: () => void;
}) {
  const all = useT();
  const t = all.auth;
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ready = confirm === "DELETE" && (!hasPassword || password.length > 0);
  return (
    <Modal
      open
      tone="danger"
      onClose={onClose}
      title={t.deleteTitle}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            {all.common.cancel}
          </button>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            disabled={!ready || busy}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                await deleteAccount(hasPassword ? password : undefined);
                onDeleted();
              } catch (err) {
                if (isReauthRequired(err)) return onReauth();
                setError(err instanceof ApiError ? err.message : t.deleteFailed);
                setBusy(false);
              }
            }}
          >
            {t.deleteEverything}
          </button>
        </>
      }
    >
      <div className="pin-form">
        <p>{t.deleteNote}</p>
        {hasPassword && (
          <label className="field">
            <span>{t.password}</span>
            <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
        )}
        <label className="field">
          <span>{t.typeDelete}</span>
          <input value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
