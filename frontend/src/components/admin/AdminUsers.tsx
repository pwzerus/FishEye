"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import {
  adminConfirmEmail,
  adminDeleteUser,
  adminResetLink,
  adminSignOutUser,
  adminUpdateUser,
  adminUser,
  adminUsers,
  getProviders,
} from "@/lib/api/session";
import type { AdminUser, AdminUserCounts, AdminUserDetail, Paged } from "@/lib/api/types";
import { ACTION_LABEL, Pager, copyText, day, detailText, errText, when, type Pending } from "./shared";

const FILTERS = [
  { id: "all", label: "All", count: (c: AdminUserCounts) => c.all },
  { id: "admins", label: "Admins", count: (c: AdminUserCounts) => c.admins },
  { id: "suspended", label: "Suspended", count: (c: AdminUserCounts) => c.suspended },
  { id: "unconfirmed", label: "Email not confirmed", count: (c: AdminUserCounts) => c.unconfirmed },
] as const;
type FilterId = (typeof FILTERS)[number]["id"];

const SORTS = [
  { id: "newest", label: "Newest first" },
  { id: "last_seen", label: "Last sign-in" },
  { id: "catches", label: "Most catches" },
  { id: "reports", label: "Most reported" },
];

/** Accounts: find one, then everything you can do to it on one screen. */
export function Users({ meId, confirmThen }: { meId: number; confirmThen: (p: Pending) => void }) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterId>("all");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<(Paged<AdminUser> & { counts?: AdminUserCounts | null }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  // In the address, so another tab (feedback, an old link) can open an account.
  const openId = Number(params.get("user")) || null;

  const load = useCallback(() => {
    adminUsers({
      q: query,
      page,
      sort,
      role: filter === "admins" ? "admin" : undefined,
      status: filter === "suspended" ? "suspended" : undefined,
      unconfirmed: filter === "unconfirmed" ? true : undefined,
    })
      .then(setData)
      .catch((e) => setError(errText(e)));
  }, [query, page, sort, filter]);
  useEffect(load, [load]);

  const open = (id: number | null) =>
    router.replace(`${pathname}?tab=users${id ? `&user=${id}` : ""}`, { scroll: false });

  return (
    <section className="admin-panel">
      {data?.counts && (
        <div className="segmented user-filters" role="group" aria-label="Show">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={filter === f.id ? "segment active" : "segment"}
              aria-pressed={filter === f.id}
              onClick={() => {
                setPage(1);
                setFilter(f.id);
              }}
            >
              {f.label} <span className="muted small">{f.count(data.counts as AdminUserCounts)}</span>
            </button>
          ))}
        </div>
      )}
      <form
        className="filter-bar"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          setQuery(q);
        }}
      >
        <input className="filter-input" placeholder="Name, email or #number" value={q} onChange={(e) => setQ(e.target.value)} />
        <button type="submit" className="btn btn-ghost btn-sm">
          Search
        </button>
        <select
          aria-label="Sort"
          value={sort}
          onChange={(e) => {
            setPage(1);
            setSort(e.target.value);
          }}
        >
          {SORTS.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </form>
      {error && <div className="backend-error">{error}</div>}
      {!data ? (
        <div className="sk" style={{ height: 200 }} />
      ) : data.items.length === 0 ? (
        <p className="muted">No accounts match.</p>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Joined</th>
                  <th>Last sign-in</th>
                  <th className="num">Catches</th>
                  <th className="num">Reported</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((u) => (
                  <tr key={u.id} className={u.status === "suspended" ? "row-dim" : undefined}>
                    <td>
                      <button type="button" className="link-btn user-open" onClick={() => open(u.id)}>
                        {u.display_name}
                      </button>{" "}
                      {u.id === meId && <span className="tag tag-admin">you</span>}
                      {u.role === "admin" && <span className="tag tag-admin">Admin</span>}
                      <div className="muted small user-email">
                        #{u.id} · {u.email}
                        {u.google_connected ? " · Google" : ""}
                      </div>
                    </td>
                    <td className="muted small">{day(u.created_at)}</td>
                    <td className="muted small">{when(u.last_login_at)}</td>
                    <td className="num">{u.pins}</td>
                    <td className="num">{u.reports_against || ""}</td>
                    <td>
                      <span className={`status-dot status-${u.status}`}>{u.status}</span>
                      {!u.email_verified && <div className="muted small">email not confirmed</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager page={data.page} total={data.total} size={data.page_size} onPage={setPage} />
        </>
      )}
      {openId !== null && (
        <UserDetail
          key={openId}
          id={openId}
          meId={meId}
          confirmThen={confirmThen}
          onClose={() => open(null)}
          onChanged={load}
        />
      )}
    </section>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function UserDetail({
  id,
  meId,
  confirmThen,
  onClose,
  onChanged,
}: {
  id: number;
  meId: number;
  confirmThen: (p: Pending) => void;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [link, setLink] = useState<{ link: string; emailed: boolean; expires_at: string } | null>(null);
  const [canEmail, setCanEmail] = useState(false);
  const toast = useToast();

  const show = useCallback((u: AdminUserDetail) => {
    setUser(u);
    setName(u.display_name);
  }, []);

  useEffect(() => {
    adminUser(id).then(show).catch((e) => setError(errText(e)));
    getProviders()
      .then((p) => setCanEmail(p.email_ready ?? false))
      .catch(() => setCanEmail(false));
  }, [id, show]);

  const act = async (run: () => Promise<AdminUserDetail | AdminUser>, done: string) => {
    try {
      await run();
      show(await adminUser(id));
      onChanged();
      toast(done);
    } catch (e) {
      toast(errText(e), "error");
    }
  };

  const makeLink = async (emailIt: boolean) => {
    try {
      setLink(await adminResetLink(id, emailIt));
      show(await adminUser(id));
    } catch (e) {
      toast(errText(e), "error");
    }
  };

  const me = id === meId;
  const isAdmin = user?.role === "admin";
  return (
    <Modal open onClose={onClose} title={user ? user.display_name : "Account"} wide>
      {error && <div className="backend-error">{error}</div>}
      {!user && !error && <div className="sk" style={{ height: 240 }} />}
      {user && (
        <div className="user-detail">
          <p className="user-detail-who">
            <a href={`mailto:${user.email}`} className="text-link">
              {user.email}
            </a>
            <span className="muted small"> · #{user.id}</span>{" "}
            {isAdmin && <span className="tag tag-admin">Admin</span>}{" "}
            <span className={`status-dot status-${user.status}`}>{user.status}</span>
          </p>
          <dl className="user-facts">
            <Fact label="Joined">{day(user.created_at)}</Fact>
            <Fact label="Last sign-in">{when(user.last_login_at)}</Fact>
            <Fact label="Last active">{when(user.last_seen_at)}</Fact>
            <Fact label="Signed in on">{user.sessions} device{user.sessions === 1 ? "" : "s"}</Fact>
            <Fact label="Email">{user.email_verified ? "Confirmed" : "Not confirmed"}</Fact>
            <Fact label="Signs in with">
              {[user.has_password && "Password", user.google_connected && "Google"].filter(Boolean).join(", ") || "Nothing set"}
            </Fact>
            <Fact label="Catches">
              {user.pins} ({user.pins_public} public, {user.pins_private} only them, {user.pins_hidden} hidden)
            </Fact>
            <Fact label="Reports">
              {user.reports_against} against, {user.reports_filed} filed
            </Fact>
            <Fact label="Feedback sent">{user.feedback}</Fact>
          </dl>

          {user.recent_pins.length > 0 && (
            <div>
              <h3>Recent catches</h3>
              <ul className="user-catches">
                {user.recent_pins.map((p) => (
                  <li key={p.id}>
                    <Link href={`/community/${p.id}`} className="text-link" target="_blank">
                      {p.title}
                    </Link>
                    <span className="muted small">
                      {" "}
                      · {day(p.created_at)}
                      {p.visibility === "private" ? " · only them" : ""}
                      {p.status !== "published" ? ` · ${p.status}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
              <Link href={`/admin?tab=pins&q=${encodeURIComponent(user.email)}`} className="text-link small">
                All their catches →
              </Link>
            </div>
          )}

          <div>
            <h3>Name</h3>
            <form
              className="filter-bar"
              onSubmit={(e) => {
                e.preventDefault();
                void act(() => adminUpdateUser(id, { display_name: name }), "Name changed");
              }}
            >
              <input className="filter-input" value={name} maxLength={40} onChange={(e) => setName(e.target.value)} aria-label="Display name" />
              <button type="submit" className="btn btn-ghost btn-sm" disabled={name.trim() === user.display_name}>
                Save name
              </button>
            </form>
          </div>

          {!me && !isAdmin && (
            <div>
              <h3>Locked out?</h3>
              {link ? (
                <div className="reset-link">
                  <p className="small">
                    {link.emailed ? "Emailed to them. " : ""}Works once, until {when(link.expires_at)}. It won&apos;t be shown
                    again, and whoever has it can take the account, so send it only to them.
                  </p>
                  <div className="filter-bar">
                    <input className="filter-input" readOnly value={link.link} onFocus={(e) => e.target.select()} aria-label="Reset link" />
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={async () => toast((await copyText(link.link)) ? "Copied" : "Select the link and copy it", "info")}
                    >
                      Copy
                    </button>
                  </div>
                </div>
              ) : (
                <div className="row-actions">
                  <button type="button" className="btn btn-ghost btn-xs" onClick={() => makeLink(false)} disabled={user.status !== "active"}>
                    Make a password reset link
                  </button>
                  {canEmail && (
                    <button type="button" className="btn btn-ghost btn-xs" onClick={() => makeLink(true)} disabled={user.status !== "active"}>
                      Email them a reset link
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {!me && (
            <div>
              <h3>Account</h3>
              <div className="row-actions">
                {!user.email_verified && (
                  <button type="button" className="btn btn-ghost btn-xs" onClick={() => act(() => adminConfirmEmail(id), "Email marked as confirmed")}>
                    Confirm their email
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-ghost btn-xs"
                  disabled={user.sessions === 0}
                  onClick={() => act(() => adminSignOutUser(id), "Signed out everywhere")}
                >
                  Sign out everywhere
                </button>
                {/* FishEye Plus by hand until payments are built: no daily
                    limit on AI summaries (backend services/ai_quota.py). */}
                {user.plus_until ? (
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs"
                    title={`Plus until ${new Date(user.plus_until).toLocaleDateString()}`}
                    onClick={() => act(() => adminUpdateUser(id, { plus_days: 0 }), "Plus ended")}
                  >
                    End Plus
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs"
                    onClick={() => act(() => adminUpdateUser(id, { plus_days: 30 }), "Plus for 30 days")}
                  >
                    Give Plus · 30 days
                  </button>
                )}
                {isAdmin ? (
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs"
                    onClick={() =>
                      confirmThen({
                        title: `Remove admin from ${user.display_name}?`,
                        body: "They keep their account and catches, but lose the admin console.",
                        confirm: "Remove admin",
                        run: () => act(() => adminUpdateUser(id, { role: "user" }), "Admin removed"),
                      })
                    }
                  >
                    Remove admin
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs"
                    onClick={() =>
                      confirmThen({
                        title: `Make ${user.display_name} an admin?`,
                        body: "Admins can moderate every catch, read private catches, and manage accounts, including yours.",
                        confirm: "Make admin",
                        run: () => act(() => adminUpdateUser(id, { role: "admin" }), "Now an admin"),
                      })
                    }
                  >
                    Make admin
                  </button>
                )}
                {user.status === "active" ? (
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs btn-danger-text"
                    onClick={() =>
                      confirmThen({
                        title: `Suspend ${user.display_name}?`,
                        body: "They're signed out everywhere immediately and can't sign in until you reactivate them. Their catches stay up unless you hide them.",
                        confirm: "Suspend",
                        danger: true,
                        run: () => act(() => adminUpdateUser(id, { status: "suspended" }), "Suspended"),
                      })
                    }
                  >
                    Suspend
                  </button>
                ) : (
                  <button type="button" className="btn btn-ghost btn-xs" onClick={() => act(() => adminUpdateUser(id, { status: "active" }), "Reactivated")}>
                    Reactivate
                  </button>
                )}
                {!isAdmin && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs btn-danger-text"
                    onClick={() =>
                      confirmThen({
                        title: `Delete ${user.display_name}'s account?`,
                        body: `${user.email}, ${user.pins} catch${user.pins === 1 ? "" : "es"} and their photos are deleted for good. This can't be undone. To stop someone without losing anything, suspend them instead.`,
                        confirm: "Delete for good",
                        danger: true,
                        run: async () => {
                          await adminDeleteUser(id);
                          toast("Account deleted");
                          onChanged();
                          onClose();
                        },
                      })
                    }
                  >
                    Delete account
                  </button>
                )}
              </div>
            </div>
          )}

          {user.history.length > 0 && (
            <div>
              <h3>History</h3>
              <ul className="user-history muted small">
                {user.history.map((h) => (
                  <li key={h.id}>
                    {when(h.created_at)} · {ACTION_LABEL[h.action] ?? h.action}
                    {h.actor !== user.display_name ? ` by ${h.actor}` : ""}
                    {detailText(h.detail) ? ` · ${detailText(h.detail)}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
