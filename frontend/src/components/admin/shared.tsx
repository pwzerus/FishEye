import { ApiError } from "@/lib/api/client";

export function when(iso: string | null): string {
  if (!iso) return "never";
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function day(iso: string | null): string {
  if (!iso) return "never";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function errText(e: unknown) {
  return e instanceof ApiError ? e.message : "Something went wrong.";
}

/** Confirm-before-acting, shared by every destructive admin button. */
export interface Pending {
  title: string;
  body: string;
  confirm: string;
  danger?: boolean;
  run: () => Promise<void>;
}

export function Pager({ page, total, size, onPage }: { page: number; total: number; size: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="pager">
      <span className="muted small">
        {total} total · page {page} of {pages}
      </span>
      <button type="button" className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        ←
      </button>
      <button type="button" className="btn btn-ghost btn-sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        →
      </button>
    </div>
  );
}

/** The clipboard, where the browser allows it. */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/** An audit entry's JSON detail as words. */
export function detailText(detail: string | null): string {
  if (!detail) return "";
  try {
    const d = JSON.parse(detail) as Record<string, unknown>;
    return Object.entries(d)
      .filter(([, v]) => v !== null && v !== "")
      .map(([k, v]) => `${k.replaceAll("_", " ")}: ${String(v)}`)
      .join(" · ");
  } catch {
    return detail;
  }
}

export const ACTION_LABEL: Record<string, string> = {
  "pin.auto_hidden": "Auto-hid catch after reports",
  "pin.published": "Restored catch",
  "pin.hidden": "Hid catch",
  "pin.removed": "Removed catch",
  "pin.purged": "Permanently deleted catch",
  "reports.dismissed": "Dismissed reports",
  "reports.hidden": "Hid catch (reports)",
  "reports.removed": "Removed catch (reports)",
  "lake_report.fixed": "Fixed a lake report",
  "lake_report.dismissed": "Dismissed a lake report",
  "user.updated": "Changed user",
  "user.deleted": "Deleted their account",
  "user.deleted_by_admin": "Deleted an account",
  "user.created_admin_cli": "Created admin (command line)",
  "user.role_cli": "Changed role (command line)",
  "user.email_confirmed": "Confirmed an email by hand",
  "user.signed_out": "Signed a user out everywhere",
  "user.reset_link": "Made a password reset link",
  "user.password_reset": "Reset their password",
  "feedback.done": "Marked feedback handled",
  "feedback.new": "Reopened feedback",
};
