"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { useLocale, useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { sendFeedback } from "@/lib/api/session";
import { LEGAL } from "@/lib/legal";

const MAX = 2000;

/** One box and one button, sent from the account (backend services/feedback.py).
 * Signed out, it asks to sign in; the address is for someone who can't. */
export function FeedbackDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const t = useT().feedback;
  const common = useT().common;
  const locale = useLocale();
  const pathname = usePathname() ?? "/";
  const toast = useToast();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    setBusy(true);
    setError(null);
    try {
      await sendFeedback(message.trim(), pathname, locale);
      setMessage("");
      toast(t.thanks);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.failed);
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <Modal
        open={open}
        onClose={onClose}
        title={t.title}
        footer={
          <Link href={`/login?next=${encodeURIComponent(pathname)}`} className="btn btn-primary btn-sm" onClick={onClose}>
            {common.signIn}
          </Link>
        }
      >
        <p>{t.signInFirst}</p>
        <p className="muted small">
          {t.cantSignIn} <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
        </p>
      </Modal>
    );
  }
  return (
    <Modal
      open={open}
      onClose={() => !busy && onClose()}
      title={t.title}
      footer={
        <button type="button" className="btn btn-primary btn-sm" disabled={busy || message.trim().length < 2} onClick={send}>
          {busy ? t.sending : t.send}
        </button>
      }
    >
      <label className="field">
        <span className="sr-only">{t.title}</span>
        <textarea
          rows={5}
          maxLength={MAX}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t.placeholder}
          autoFocus
        />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <p className="muted small">{t.fromAccount(user.email)}</p>
    </Modal>
  );
}

/** A button anywhere, server-rendered pages included, that opens the dialog. */
export function FeedbackButton({ className, label }: { className?: string; label: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className={className} onClick={() => setOpen(true)}>
        {label}
      </button>
      {open && <FeedbackDialog open onClose={() => setOpen(false)} />}
    </>
  );
}
