"use client";

import Link from "next/link";
import { useState } from "react";

import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/lib/api/client";
import { adminPurgePin, adminSetPinStatus } from "@/lib/api/session";
import type { PinDetail } from "@/lib/api/types";

type Action = "published" | "hidden" | "removed" | "purge";

const ACTIONS: Record<Action, { label: string; title: string; body: string; confirm: string; danger: boolean }> = {
  published: {
    label: "Restore",
    title: "Restore this catch?",
    body: "It becomes visible again (to everyone, if it's public).",
    confirm: "Restore",
    danger: false,
  },
  hidden: {
    label: "Hide",
    title: "Hide this catch?",
    body: "Only its owner and admins will see it, and the owner can't edit it (only delete it) until you restore it.",
    confirm: "Hide",
    danger: false,
  },
  removed: {
    label: "Remove",
    title: "Remove this catch?",
    body: "Hidden from everyone but its owner and admins, for good unless an admin restores it.",
    confirm: "Remove",
    danger: true,
  },
  purge: {
    label: "Delete forever",
    title: "Delete permanently?",
    body: "The catch and its photo files are deleted for good. Use this only for content that must not be kept.",
    confirm: "Delete forever",
    danger: true,
  },
};

/** An admin's moderation controls on a catch's own page: the same actions
 * as the admin console's Pins tab, each confirmed and written to the audit
 * log by the server. */
export function AdminModeration({ pin, onChanged, onPurged }: { pin: PinDetail; onChanged: () => void; onPurged: () => void }) {
  const toast = useToast();
  const [pending, setPending] = useState<Action | null>(null);
  const [busy, setBusy] = useState(false);
  const actions: Action[] = [
    ...(pin.status !== "published" ? (["published"] as const) : []),
    ...(pin.status === "published" ? (["hidden"] as const) : []),
    ...(pin.status !== "removed" ? (["removed"] as const) : []),
    "purge",
  ];

  const run = async (a: Action) => {
    setBusy(true);
    try {
      if (a === "purge") {
        await adminPurgePin(pin.id);
        toast("Catch deleted", "info");
        onPurged();
      } else {
        await adminSetPinStatus(pin.id, a);
        toast(a === "published" ? "Catch restored" : a === "hidden" ? "Catch hidden" : "Catch removed");
        onChanged();
      }
      setPending(null);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Couldn't update the catch", "error");
    } finally {
      setBusy(false);
    }
  };

  const p = pending ? ACTIONS[pending] : null;
  return (
    <section className="admin-moderation" aria-label="Moderation">
      <div className="admin-moderation-head">
        <span className="tag tag-admin">Admin</span>
        <span className="muted small">
          {pin.status === "published" ? "Published" : pin.status === "hidden" ? "Hidden" : "Removed"}
          {pin.visibility === "private" ? " · only-me" : ""} · by {pin.author.display_name}
        </span>
        <Link href="/admin" className="text-link small">
          Admin console
        </Link>
      </div>
      <div className="admin-moderation-actions">
        {actions.map((a) => (
          <button
            key={a}
            type="button"
            className={ACTIONS[a].danger ? "btn btn-ghost btn-sm btn-danger-text" : "btn btn-ghost btn-sm"}
            onClick={() => setPending(a)}
          >
            {ACTIONS[a].label}
          </button>
        ))}
      </div>
      <Modal
        open={p !== null}
        onClose={() => setPending(null)}
        title={p?.title ?? ""}
        tone={p?.danger ? "danger" : undefined}
        footer={
          <>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPending(null)}>
              Cancel
            </button>
            <button
              type="button"
              className={p?.danger ? "btn btn-danger btn-sm" : "btn btn-primary btn-sm"}
              disabled={busy}
              onClick={() => pending && run(pending)}
            >
              {p?.confirm}
            </button>
          </>
        }
      >
        <p>{p?.body}</p>
      </Modal>
    </section>
  );
}
