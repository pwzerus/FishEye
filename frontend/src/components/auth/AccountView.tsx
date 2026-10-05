"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { PinCard } from "@/components/community/PinCard";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/lib/api/client";
import {
  changePassword,
  deleteAccount,
  disconnectGoogle,
  getProviders,
  googleStartUrl,
  isReauthRequired,
  listPins,
  updateProfile,
} from "@/lib/api/session";
import type { PinSummary } from "@/lib/api/types";
import { initials } from "./AccountMenu";
import { useAuth } from "./AuthProvider";
import { ReauthDialog } from "./ReauthDialog";

/** What to do once the user has confirmed it's them. */
interface ReauthRequest {
  action: string;
  retry?: () => Promise<void> | void;
}

const CALLBACK_ERRORS: Record<string, string> = {
  google_in_use: "That Google account is connected to a different FishEye account.",
  google_unverified: "That Google email address isn't verified.",
  google_cancelled: "Connecting Google was cancelled.",
  google_state: "That link expired. Try again.",
  google_failed: "Connecting Google didn't complete. Try again.",
  reauth_required: "For your security, confirm it's you before connecting Google.",
};

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
  const [pins, setPins] = useState<PinSummary[] | null>(null);
  const [google, setGoogle] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const [delOpen, setDelOpen] = useState(false);
  // Connecting a new Google account from an old session bounces back with
  // ?error=reauth_required: confirm, then go straight back to Google.
  const [reauthFor, setReauthFor] = useState<ReauthRequest | null>(() =>
    params.get("error") === "reauth_required"
      ? { action: "connect Google", retry: () => window.location.assign(googleStartUrl("/account")) }
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
    if (params.get("connected") === "google") toast("Google connected");
    const err = params.get("error");
    if (err && err !== "reauth_required") toast(CALLBACK_ERRORS[err] ?? "That didn't work. Try again.", "error");
  }, [params, toast]);

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
                  Admin
                </Link>
              </>
            )}
          </p>
        </div>
        <div className="acct-stats">
          <div>
            <strong>{pins?.length ?? "–"}</strong>
            <span>pins</span>
          </div>
          <div>
            <strong>{counts.public}</strong>
            <span>public</span>
          </div>
          <div>
            <strong>{counts.private}</strong>
            <span>only you</span>
          </div>
        </div>
      </header>

      <div className="acct-grid">
        <div className="acct-col">
          <Section title="Profile">
            {/* Keyed on the saved name so the field resets after a save. */}
            <ProfileForm key={user.display_name} initial={user.display_name} />
          </Section>

          <Section title="Sign-in methods">
            <ul className="method-list">
              <li>
                <div>
                  <strong>Password</strong>
                  <span className="muted">{user.has_password ? "Set" : "Not set: you sign in with Google"}</span>
                </div>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPwOpen(true)}>
                  {user.has_password ? "Change" : "Set a password"}
                </button>
              </li>
              {(google || user.google_connected) && (
                <li>
                  <div>
                    <strong>Google</strong>
                    <span className="muted">{user.google_connected ? "Connected" : "Not connected"}</span>
                  </div>
                  {user.google_connected ? (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={!user.has_password}
                      title={user.has_password ? undefined : "Set a password first"}
                      onClick={async () => {
                        const run = async () => {
                          setUser(await disconnectGoogle());
                          toast("Google disconnected", "info");
                        };
                        try {
                          await run();
                        } catch (err) {
                          if (isReauthRequired(err)) setReauthFor({ action: "disconnect Google", retry: run });
                          else toast(err instanceof ApiError ? err.message : "Couldn't disconnect", "error");
                        }
                      }}
                    >
                      Disconnect
                    </button>
                  ) : (
                    <a className="btn btn-ghost btn-sm" href={googleStartUrl("/account")}>
                      Connect
                    </a>
                  )}
                </li>
              )}
            </ul>
          </Section>

          <Section title="Delete account" tone="danger">
            <p className="muted">Deletes your account, every pin you made and all their photos. This can&apos;t be undone.</p>
            <button type="button" className="btn btn-danger btn-sm" onClick={() => setDelOpen(true)}>
              Delete my account
            </button>
          </Section>
        </div>

        <Section id="pins" title="My pins">
          {pins === null ? (
            <div className="sk" style={{ height: 180 }} />
          ) : pins.length === 0 ? (
            <div className="empty-state compact">
              <p className="muted">No pins yet. Open the map and tap where you fished.</p>
              <Link href="/map?addPin=1" className="btn btn-primary btn-sm">
                Pin a catch
              </Link>
            </div>
          ) : (
            <ul className="pin-grid pin-grid-compact">
              {pins.map((p, i) => (
                <li key={p.id}>
                  <PinCard pin={p} index={i} />
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      {pwOpen && (
        <PasswordDialog
          hasPassword={user.has_password}
          onClose={() => setPwOpen(false)}
          onReauth={() => {
            setPwOpen(false);
            setReauthFor({ action: "set a password" });
          }}
        />
      )}
      {delOpen && (
        <DeleteDialog
          hasPassword={user.has_password}
          onClose={() => setDelOpen(false)}
          onReauth={() => {
            setDelOpen(false);
            setReauthFor({ action: "delete your account" });
          }}
          onDeleted={async () => {
            await signOut().catch(() => undefined);
            toast("Your account was deleted", "info");
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
              toast(err instanceof ApiError ? err.message : "That didn't work. Try again.", "error");
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
          toast("Name updated");
        } catch (err) {
          toast(err instanceof ApiError ? err.message : "Couldn't save", "error");
          setSaving(false);
        }
      }}
    >
      <label className="field">
        <span>Display name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={40} />
      </label>
      <button type="submit" className="btn btn-primary btn-sm" disabled={saving || name.trim() === initial}>
        Save
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
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <Modal
      open
      onClose={onClose}
      title={hasPassword ? "Change password" : "Set a password"}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            Cancel
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
                toast("Password saved. Other devices were signed out.");
                onClose();
              } catch (err) {
                if (isReauthRequired(err)) return onReauth();
                setError(err instanceof ApiError ? err.message : "Couldn't save.");
                setBusy(false);
              }
            }}
          >
            Save
          </button>
        </>
      }
    >
      <div className="pin-form">
        {hasPassword && (
          <label className="field">
            <span>Current password</span>
            <input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          </label>
        )}
        <div className="field">
          <label htmlFor="acct-new-password" className="field-label">
            New password
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
            At least 8 characters. Saving signs out your other devices.
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
      title="Delete your account?"
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            Cancel
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
                setError(err instanceof ApiError ? err.message : "Couldn't delete.");
                setBusy(false);
              }
            }}
          >
            Delete everything
          </button>
        </>
      }
    >
      <div className="pin-form">
        <p>Your pins and photos are deleted with the account.</p>
        {hasPassword && (
          <label className="field">
            <span>Password</span>
            <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
        )}
        <label className="field">
          <span>
            Type <strong>DELETE</strong> to confirm
          </span>
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
