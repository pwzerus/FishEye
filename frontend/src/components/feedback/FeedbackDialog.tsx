"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { useLocale, useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { sendFeedback } from "@/lib/api/session";

const MAX = 2000;

/** One box and one button (backend services/feedback.py). Signed in, it is
 * sent from the account; signed out, no account is needed, and an email
 * address is asked for only if they want a reply. */
export function FeedbackDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const t = useT().feedback;
  const locale = useLocale();
  const pathname = usePathname() ?? "/";
  const toast = useToast();
  const [message, setMessage] = useState("");
  const [contact, setContact] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    setBusy(true);
    setError(null);
    try {
      await sendFeedback(message.trim(), pathname, locale, user ? undefined : contact.trim());
      setMessage("");
      setContact("");
      toast(t.thanks);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.failed);
    } finally {
      setBusy(false);
    }
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
      {user ? (
        <p className="muted small">{t.fromAccount(user.email)}</p>
      ) : (
        <>
          <label className="field">
            <span>{t.contactLabel}</span>
            <input
              type="email"
              autoComplete="email"
              maxLength={254}
              value={contact}
              onChange={(e) => setContact(e.target.value)}
            />
          </label>
          <p className="muted small">{t.signedOutNote}</p>
        </>
      )}
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
