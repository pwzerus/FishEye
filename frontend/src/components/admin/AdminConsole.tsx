"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { formatDay } from "@/components/community/PinCard";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/lib/api/client";
import {
  adminAudit,
  adminPins,
  adminPurgePin,
  adminReports,
  adminResolve,
  adminSetPinStatus,
  adminStats,
  adminUpdateUser,
  adminUsers,
} from "@/lib/api/session";
import type { AdminPin, AdminReportGroup, AdminStats, AdminUser, AuditEntry, Paged } from "@/lib/api/types";
import { TpwdRefresh } from "./TpwdRefresh";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "reports", label: "Reports" },
  { id: "pins", label: "Pins" },
  { id: "users", label: "Users" },
  { id: "audit", label: "Audit log" },
  { id: "data", label: "Data refresh" },
] as const;
type TabId = (typeof TABS)[number]["id"];

function when(iso: string | null): string {
  if (!iso) return "never";
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function errText(e: unknown) {
  return e instanceof ApiError ? e.message : "Something went wrong.";
}

/** Confirm-before-acting, shared by every destructive admin button. */
interface Pending {
  title: string;
  body: string;
  confirm: string;
  danger?: boolean;
  run: () => Promise<void>;
}

export function AdminConsole() {
  const { user, loading } = useAuth();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "overview") as TabId;
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  if (loading) return <div className="sk sk-title" />;
  if (!user) {
    return (
      <div className="empty-state">
        <h1>Admin</h1>
        <p className="muted">Sign in with an admin account to continue.</p>
        <Link href="/login?next=/admin" className="btn btn-primary btn-sm">
          Sign in
        </Link>
      </div>
    );
  }
  if (user.role !== "admin") {
    return (
      <div className="empty-state">
        <h1>Admins only</h1>
        <p className="muted">
          Your account doesn&apos;t have admin access. The first admin is created from the server&apos;s command line
          (see backend/README.md).
        </p>
        <Link href="/" className="btn btn-ghost btn-sm">
          Back home
        </Link>
      </div>
    );
  }

  const confirmThen = (p: Pending) => setPending(p);

  return (
    <>
      <header className="admin-head reveal">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Moderation and accounts</h1>
        </div>
      </header>
      <nav className="admin-tabs reveal" aria-label="Admin sections" style={{ "--i": 1 } as React.CSSProperties}>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tab === t.id ? "admin-tab active" : "admin-tab"}
            aria-current={tab === t.id ? "page" : undefined}
            onClick={() => router.replace(`${pathname}?tab=${t.id}`, { scroll: false })}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="admin-body" key={tab}>
        {tab === "overview" && <Overview onGo={(t) => router.replace(`${pathname}?tab=${t}`, { scroll: false })} />}
        {tab === "reports" && <Reports confirmThen={confirmThen} />}
        {tab === "pins" && <Pins confirmThen={confirmThen} />}
        {tab === "users" && <Users meId={user.id} confirmThen={confirmThen} />}
        {tab === "audit" && <Audit />}
        {tab === "data" && <TpwdRefresh />}
      </div>

      <Modal
        open={pending !== null}
        onClose={() => !busy && setPending(null)}
        title={pending?.title ?? ""}
        tone={pending?.danger ? "danger" : "default"}
        footer={
          <>
            <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => setPending(null)}>
              Cancel
            </button>
            <button
              type="button"
              className={pending?.danger ? "btn btn-danger btn-sm" : "btn btn-primary btn-sm"}
              disabled={busy}
              onClick={async () => {
                if (!pending) return;
                setBusy(true);
                try {
                  await pending.run();
                  setPending(null);
                } catch (e) {
                  toast(errText(e), "error");
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "Working…" : pending?.confirm}
            </button>
          </>
        }
      >
        <p>{pending?.body}</p>
      </Modal>
    </>
  );
}

// ---------------------------------------------------------------- overview

function StatCard({ label, value, sub, tone, onClick }: { label: string; value: number | string; sub?: string; tone?: "warn"; onClick?: () => void }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag type={onClick ? "button" : undefined} className={`stat-card${tone ? ` stat-${tone}` : ""}`} onClick={onClick}>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {sub && <span className="stat-sub">{sub}</span>}
    </Tag>
  );
}

function Overview({ onGo }: { onGo: (tab: TabId) => void }) {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [recent, setRecent] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    adminStats().then(setStats).catch((e) => setError(errText(e)));
    adminAudit(1).then((p) => setRecent(p.items.slice(0, 8))).catch(() => setRecent([]));
  }, []);
  if (error) return <div className="backend-error">{error}</div>;
  if (!stats) return <div className="stat-grid">{Array.from({ length: 6 }, (_, i) => <div key={i} className="stat-card sk" style={{ height: 96 }} />)}</div>;
  return (
    <>
      <div className="stat-grid">
        <StatCard
          label="Needs review"
          value={stats.pins_awaiting_review}
          sub={`${stats.open_reports} open report${stats.open_reports === 1 ? "" : "s"}`}
          tone={stats.pins_awaiting_review > 0 ? "warn" : undefined}
          onClick={() => onGo("reports")}
        />
        <StatCard label="Pins" value={stats.pins} sub={`+${stats.pins_new_7d} this week`} onClick={() => onGo("pins")} />
        <StatCard label="Public / only-me" value={`${stats.pins_public} / ${stats.pins_private}`} sub={`${stats.photos} photos`} />
        <StatCard label="Hidden / removed" value={`${stats.pins_hidden} / ${stats.pins_removed}`} onClick={() => onGo("pins")} />
        <StatCard label="Users" value={stats.users} sub={`+${stats.users_new_7d} new, ${stats.users_active_7d} active this week`} onClick={() => onGo("users")} />
        <StatCard label="Admins / suspended" value={`${stats.admins} / ${stats.suspended}`} onClick={() => onGo("users")} />
      </div>
      <section className="admin-panel">
        <div className="panel-head">
          <h2>Recent activity</h2>
          <button type="button" className="link-btn" onClick={() => onGo("audit")}>
            Full log →
          </button>
        </div>
        {recent === null ? <div className="sk" style={{ height: 120 }} /> : recent.length === 0 ? <p className="muted">Nothing yet.</p> : <AuditTable rows={recent} />}
      </section>
    </>
  );
}

// ----------------------------------------------------------------- reports

function PinThumb({ pin }: { pin: { thumb_url: string | null; title: string } }) {
  return pin.thumb_url ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img className="row-thumb" src={pin.thumb_url} alt="" />
  ) : (
    <span className="row-thumb row-thumb-empty" aria-hidden="true" />
  );
}

function Reports({ confirmThen }: { confirmThen: (p: Pending) => void }) {
  const [groups, setGroups] = useState<AdminReportGroup[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const load = useCallback(() => {
    adminReports().then(setGroups).catch((e) => setError(errText(e)));
  }, []);
  useEffect(load, [load]);

  if (error) return <div className="backend-error">{error}</div>;
  if (groups === null) return <div className="sk" style={{ height: 200 }} />;
  if (groups.length === 0)
    return (
      <div className="empty-state compact">
        <h2>All clear</h2>
        <p className="muted">No open reports.</p>
      </div>
    );

  const act = (g: AdminReportGroup, action: "dismiss" | "hide" | "remove") => {
    const copy = {
      dismiss: { title: "Dismiss these reports?", body: "The pin stays up (and comes back if the reports had hidden it).", confirm: "Dismiss", danger: false },
      hide: { title: "Hide this pin?", body: "Only its owner and admins will see it. You can restore it later.", confirm: "Hide pin", danger: false },
      remove: { title: "Remove this pin?", body: "Removed pins are hidden from everyone but admins, and the owner can't edit them. Reversible from the Pins tab.", confirm: "Remove pin", danger: true },
    }[action];
    confirmThen({
      ...copy,
      run: async () => {
        await adminResolve(g.pin.id, action);
        toast(action === "dismiss" ? "Reports dismissed" : action === "hide" ? "Pin hidden" : "Pin removed");
        load();
      },
    });
  };

  return (
    <ul className="report-list">
      {groups.map((g, i) => (
        <li key={g.pin.id} className="report-card reveal" style={{ "--i": i } as React.CSSProperties}>
          <div className="report-pin">
            <PinThumb pin={g.pin} />
            <div>
              <Link href={`/community/${g.pin.id}`} className="report-title">
                {g.pin.title}
              </Link>
              <p className="muted small">
                by {g.pin.author.display_name} · {g.pin.species_label ?? "no species"} · status {g.pin.status}
              </p>
            </div>
            <span className="report-count">{g.reports.length}</span>
          </div>
          <ul className="report-reasons">
            {g.reports.map((r) => (
              <li key={r.id}>
                <strong>{r.reason_label}</strong>
                {r.detail && <span> “{r.detail}”</span>}
                <span className="muted small">
                  {" "}
                  · {r.reporter}, {when(r.created_at)}
                </span>
              </li>
            ))}
          </ul>
          <div className="row-actions">
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(g, "dismiss")}>
              Dismiss
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(g, "hide")}>
              Hide
            </button>
            <button type="button" className="btn btn-danger btn-sm" onClick={() => act(g, "remove")}>
              Remove
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

// -------------------------------------------------------------------- pins

function Pager({ page, total, size, onPage }: { page: number; total: number; size: number; onPage: (p: number) => void }) {
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

function Pins({ confirmThen }: { confirmThen: (p: Pending) => void }) {
  const [status, setStatus] = useState("");
  const [visibility, setVisibility] = useState("");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paged<AdminPin> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const load = useCallback(() => {
    adminPins({ status, visibility, q: query, page }).then(setData).catch((e) => setError(errText(e)));
  }, [status, visibility, query, page]);
  useEffect(load, [load]);

  const setPinStatus = (p: AdminPin, s: "published" | "hidden" | "removed") =>
    confirmThen({
      title: s === "published" ? "Restore this pin?" : s === "hidden" ? "Hide this pin?" : "Remove this pin?",
      body:
        s === "published"
          ? "It becomes visible again (to everyone, if it's public)."
          : "Only its owner and admins will see it. Reversible.",
      confirm: s === "published" ? "Restore" : s === "hidden" ? "Hide" : "Remove",
      danger: s === "removed",
      run: async () => {
        await adminSetPinStatus(p.id, s);
        toast("Pin updated");
        load();
      },
    });

  return (
    <section className="admin-panel">
      <form
        className="filter-bar"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          setQuery(q);
        }}
      >
        <input className="filter-input" placeholder="Search title, author or email" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">Any status</option>
          <option value="published">Published</option>
          <option value="hidden">Hidden</option>
          <option value="removed">Removed</option>
        </select>
        <select value={visibility} onChange={(e) => { setVisibility(e.target.value); setPage(1); }}>
          <option value="">Any visibility</option>
          <option value="public">Public</option>
          <option value="private">Only-me</option>
        </select>
        <button type="submit" className="btn btn-ghost btn-sm">
          Search
        </button>
      </form>
      {error && <div className="backend-error">{error}</div>}
      {!data ? (
        <div className="sk" style={{ height: 200 }} />
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Pin</th>
                  <th>Author</th>
                  <th>Status</th>
                  <th className="num">Reports</th>
                  <th>Created</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div className="cell-pin">
                        <PinThumb pin={p} />
                        <div>
                          <Link href={`/community/${p.id}`} className="text-link">
                            {p.title}
                          </Link>
                          <div className="muted small">{p.species_label ?? "—"}{p.visibility === "private" ? " · only-me" : ""}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      {p.author.display_name}
                      <div className="muted small">{p.author_email}</div>
                    </td>
                    <td>
                      <span className={`status-dot status-${p.status}`}>{p.status}</span>
                      {p.status_reason && <div className="muted small">by {p.status_reason}</div>}
                    </td>
                    <td className="num">{p.open_reports || ""}</td>
                    <td className="muted small">{formatDay(p.created_at)}</td>
                    <td>
                      <div className="row-actions">
                        {p.status !== "published" && (
                          <button type="button" className="btn btn-ghost btn-xs" onClick={() => setPinStatus(p, "published")}>
                            Restore
                          </button>
                        )}
                        {p.status === "published" && (
                          <button type="button" className="btn btn-ghost btn-xs" onClick={() => setPinStatus(p, "hidden")}>
                            Hide
                          </button>
                        )}
                        {p.status !== "removed" && (
                          <button type="button" className="btn btn-ghost btn-xs btn-danger-text" onClick={() => setPinStatus(p, "removed")}>
                            Remove
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-ghost btn-xs btn-danger-text"
                          title="Delete permanently, with photos"
                          onClick={() =>
                            confirmThen({
                              title: "Delete permanently?",
                              body: "The pin and its photo files are deleted for good. Use this only for content that must not be kept.",
                              confirm: "Delete forever",
                              danger: true,
                              run: async () => {
                                await adminPurgePin(p.id);
                                toast("Pin deleted", "info");
                                load();
                              },
                            })
                          }
                        >
                          Purge
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">
                      No pins match.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <Pager page={data.page} total={data.total} size={data.page_size} onPage={setPage} />
        </>
      )}
    </section>
  );
}

// ------------------------------------------------------------------- users

function Users({ meId, confirmThen }: { meId: number; confirmThen: (p: Pending) => void }) {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paged<AdminUser> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const load = useCallback(() => {
    adminUsers({ q: query, page }).then(setData).catch((e) => setError(errText(e)));
  }, [query, page]);
  useEffect(load, [load]);

  const change = (u: AdminUser, patch: { role?: string; status?: string }, title: string, body: string, danger = false) =>
    confirmThen({
      title,
      body,
      confirm: "Confirm",
      danger,
      run: async () => {
        await adminUpdateUser(u.id, patch);
        toast("User updated");
        load();
      },
    });

  return (
    <section className="admin-panel">
      <form
        className="filter-bar"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          setQuery(q);
        }}
      >
        <input className="filter-input" placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} />
        <button type="submit" className="btn btn-ghost btn-sm">
          Search
        </button>
      </form>
      {error && <div className="backend-error">{error}</div>}
      {!data ? (
        <div className="sk" style={{ height: 200 }} />
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th className="num">Pins</th>
                  <th className="num">Reports against</th>
                  <th>Last sign-in</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {data.items.map((u) => {
                  const me = u.id === meId;
                  return (
                    <tr key={u.id}>
                      <td>
                        {u.display_name} {me && <span className="tag tag-admin">you</span>}
                        <div className="muted small">
                          {u.email}
                          {u.google_connected ? " · Google" : ""}
                        </div>
                      </td>
                      <td>{u.role === "admin" ? <span className="tag tag-admin">Admin</span> : "User"}</td>
                      <td>
                        <span className={`status-dot status-${u.status}`}>{u.status}</span>
                      </td>
                      <td className="num">{u.pins}</td>
                      <td className="num">{u.reports_against || ""}</td>
                      <td className="muted small">{when(u.last_login_at)}</td>
                      <td>
                        {!me && (
                          <div className="row-actions">
                            {u.role === "user" ? (
                              <button
                                type="button"
                                className="btn btn-ghost btn-xs"
                                onClick={() => change(u, { role: "admin" }, `Make ${u.display_name} an admin?`, "Admins can moderate every pin and manage every account, including yours.")}
                              >
                                Make admin
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="btn btn-ghost btn-xs"
                                onClick={() => change(u, { role: "user" }, `Remove admin from ${u.display_name}?`, "They keep their account and pins.")}
                              >
                                Remove admin
                              </button>
                            )}
                            {u.status === "active" ? (
                              <button
                                type="button"
                                className="btn btn-ghost btn-xs btn-danger-text"
                                onClick={() =>
                                  change(u, { status: "suspended" }, `Suspend ${u.display_name}?`, "They're signed out everywhere immediately and can't sign in until reactivated. Their pins stay as they are.", true)
                                }
                              >
                                Suspend
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="btn btn-ghost btn-xs"
                                onClick={() => change(u, { status: "active" }, `Reactivate ${u.display_name}?`, "They can sign in again.")}
                              >
                                Reactivate
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pager page={data.page} total={data.total} size={data.page_size} onPage={setPage} />
        </>
      )}
    </section>
  );
}

// ------------------------------------------------------------------- audit

const ACTION_LABEL: Record<string, string> = {
  "pin.auto_hidden": "Auto-hid pin after reports",
  "pin.published": "Restored pin",
  "pin.hidden": "Hid pin",
  "pin.removed": "Removed pin",
  "pin.purged": "Permanently deleted pin",
  "reports.dismissed": "Dismissed reports",
  "reports.hidden": "Hid pin (reports)",
  "reports.removed": "Removed pin (reports)",
  "user.updated": "Changed user",
  "user.created_admin_cli": "Created admin (command line)",
  "user.role_cli": "Changed role (command line)",
};

function detailText(detail: string | null): string {
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

function AuditTable({ rows }: { rows: AuditEntry[] }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>When</th>
            <th>Who</th>
            <th>What</th>
            <th>Target</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="muted small">{when(r.created_at)}</td>
              <td>{r.actor === "System" ? <span className="tag tag-private">System</span> : r.actor}</td>
              <td>{ACTION_LABEL[r.action] ?? r.action}</td>
              <td className="small">
                {r.target_type === "pin" ? (
                  <Link href={`/community/${r.target_id}`} className="text-link">
                    pin #{r.target_id}
                  </Link>
                ) : (
                  `${r.target_type} #${r.target_id}`
                )}
              </td>
              <td className="muted small">{detailText(r.detail)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Audit() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paged<AuditEntry> | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    adminAudit(page).then(setData).catch((e) => setError(errText(e)));
  }, [page]);
  if (error) return <div className="backend-error">{error}</div>;
  if (!data) return <div className="sk" style={{ height: 200 }} />;
  return (
    <section className="admin-panel">
      {data.items.length === 0 ? <p className="muted">Nothing logged yet.</p> : <AuditTable rows={data.items} />}
      <Pager page={data.page} total={data.total} size={data.page_size} onPage={setPage} />
    </section>
  );
}
