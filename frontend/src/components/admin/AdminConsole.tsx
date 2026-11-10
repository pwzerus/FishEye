"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { formatDay } from "@/components/community/PinCard";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import {
  adminAskMisses,
  adminAudit,
  adminLakeReports,
  adminPins,
  adminPurgePin,
  adminCommentReports,
  adminReports,
  adminResolveComment,
  adminResolve,
  adminResolveLakeReport,
  adminSetPinStatus,
  adminStats,
} from "@/lib/api/session";
import type {
  AdminCommentReportGroup,
  AdminLakeReport,
  AdminPin,
  AdminReportGroup,
  AdminStats,
  AskMiss,
  AuditEntry,
  Paged,
  PinSummary,
} from "@/lib/api/types";
import { useJurisdictions } from "@/lib/jurisdiction";
import { AdminFeedbackTab } from "./AdminFeedback";
import { Users } from "./AdminUsers";
import { AdminVisitsTab } from "./AdminVisits";
import { ACTION_LABEL, Pager, detailText, errText, when, type Pending } from "./shared";
import { TpwdRefresh } from "./TpwdRefresh";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "feedback", label: "Feedback" },
  { id: "visits", label: "Visits" },
  { id: "reports", label: "Reports" },
  { id: "lakes", label: "Lake reports" },
  { id: "pins", label: "Catches" },
  { id: "users", label: "Users" },
  { id: "audit", label: "Audit log" },
  { id: "ask", label: "Ask misses" },
  { id: "data", label: "Data refresh" },
] as const;
type TabId = (typeof TABS)[number]["id"];

/** The photo check on the species named (backend services/fish_id.py), for moderators. */
function checkNote(pin: Pick<PinSummary, "species_label" | "species_check" | "species_check_label">): string {
  if (!pin.species_label) return "";
  if (pin.species_check === "confirmed") return " (photo-checked)";
  if (pin.species_check === "group") return ` (photo: ${pin.species_check_label ?? "look-alike"})`;
  return " (not photo-checked)";
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
        {tab === "feedback" && <AdminFeedbackTab />}
        {tab === "visits" && <AdminVisitsTab />}
        {tab === "reports" && (
          <>
            <Reports confirmThen={confirmThen} />
            <CommentReports confirmThen={confirmThen} />
          </>
        )}
        {tab === "lakes" && <LakeReports confirmThen={confirmThen} />}
        {tab === "pins" && <Pins confirmThen={confirmThen} />}
        {tab === "users" && <Users meId={user.id} confirmThen={confirmThen} />}
        {tab === "audit" && <Audit />}
        {tab === "ask" && <AskMisses />}
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
        <StatCard
          label="Feedback"
          value={stats.feedback_new ?? 0}
          sub="new messages"
          tone={(stats.feedback_new ?? 0) > 0 ? "warn" : undefined}
          onClick={() => onGo("feedback")}
        />
        <StatCard
          label="AI cost this month"
          value={`$${(stats.ai_spent_usd ?? 0).toFixed(2)}`}
          sub={`estimate · pauses at $${(stats.ai_budget_usd ?? 0).toFixed(2)}`}
          tone={(stats.ai_spent_usd ?? 0) >= (stats.ai_budget_usd ?? 0) * 0.8 ? "warn" : undefined}
        />
        <StatCard
          label="Lake reports"
          value={stats.lake_reports_open ?? 0}
          sub="wrong or missing lakes to check"
          tone={(stats.lake_reports_open ?? 0) > 0 ? "warn" : undefined}
          onClick={() => onGo("lakes")}
        />
        <StatCard label="Catches" value={stats.pins} sub={`+${stats.pins_new_7d} this week`} onClick={() => onGo("pins")} />
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
      dismiss: { title: "Dismiss these reports?", body: "The catch stays up (and comes back if the reports had hidden it).", confirm: "Dismiss", danger: false },
      hide: { title: "Hide this catch?", body: "Only its owner and admins will see it. You can restore it later.", confirm: "Hide catch", danger: false },
      remove: { title: "Remove this catch?", body: "Removed catches are hidden from everyone but admins, and the owner can't edit them (only delete them). Reversible from the Catches tab.", confirm: "Remove catch", danger: true },
    }[action];
    confirmThen({
      ...copy,
      run: async () => {
        await adminResolve(g.pin.id, action);
        toast(action === "dismiss" ? "Reports dismissed" : action === "hide" ? "Catch hidden" : "Catch removed");
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
                by {g.pin.author.display_name} · {g.pin.species_label ?? "no species"}{checkNote(g.pin)} · status {g.pin.status}
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

function CommentReports({ confirmThen }: { confirmThen: (p: Pending) => void }) {
  const [groups, setGroups] = useState<AdminCommentReportGroup[] | null>(null);
  const toast = useToast();
  const load = useCallback(() => {
    adminCommentReports().then(setGroups).catch(() => setGroups([]));
  }, []);
  useEffect(load, [load]);
  if (!groups || groups.length === 0) return null;
  const act = (id: number, action: "dismiss" | "remove") =>
    confirmThen({
      title: action === "dismiss" ? "Dismiss these reports?" : "Remove this comment?",
      confirm: action === "dismiss" ? "Dismiss" : "Remove",
      body: action === "dismiss" ? "The comment stays up, and comes back if the reports had hidden it." : "The comment is deleted.",
      run: async () => {
        await adminResolveComment(id, action);
        toast(action === "dismiss" ? "Reports dismissed" : "Comment removed");
        load();
      },
    });
  return (
    <>
      <h2 className="admin-subhead">Reported comments</h2>
      <ul className="report-list">
        {groups.map((g) => (
          <li key={g.comment.id} className="report-card">
            <div className="report-pin">
              <div>
                <Link href={`/community/${g.comment.pin_id}`} className="report-title">
                  {g.comment.pin_title}
                </Link>
                <p>“{g.comment.body}”</p>
                <p className="muted small">
                  by {g.comment.author}
                  {g.comment.status === "hidden" && " · hidden by reports"}
                </p>
              </div>
              <span className="report-count">{g.reports.length}</span>
            </div>
            <ul className="report-reasons">
              {g.reports.map((r) => (
                <li key={r.id}>
                  <strong>{r.reason_label}</strong>
                  <span className="muted small"> · {r.reporter}</span>
                </li>
              ))}
            </ul>
            <div className="row-actions">
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(g.comment.id, "dismiss")}>
                Dismiss
              </button>
              <button type="button" className="btn btn-danger btn-sm" onClick={() => act(g.comment.id, "remove")}>
                Remove
              </button>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}

// ------------------------------------------------------------ lake reports

/** "Something's wrong with this lake" and "a lake is missing" (backend ADR
 * 0039): check each against a source, fix the data by hand, then mark it. */
function LakeReports({ confirmThen }: { confirmThen: (p: Pending) => void }) {
  const [status, setStatus] = useState<"open" | "resolved">("open");
  const [rows, setRows] = useState<AdminLakeReport[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const load = useCallback(() => {
    adminLakeReports(status).then(setRows).catch((e) => setError(errText(e)));
  }, [status]);
  useEffect(load, [load]);

  const act = (r: AdminLakeReport, resolution: "fixed" | "dismissed") =>
    confirmThen({
      title: resolution === "fixed" ? "Mark as fixed?" : "Dismiss this report?",
      body:
        resolution === "fixed"
          ? "Only once the data is corrected (or the lake added) from a source. This doesn't change the map by itself."
          : "Nothing changes on the map. Use this when a source shows the map was right.",
      confirm: resolution === "fixed" ? "Mark fixed" : "Dismiss",
      danger: false,
      run: async () => {
        await adminResolveLakeReport(r.id, resolution);
        toast(resolution === "fixed" ? "Marked fixed" : "Report dismissed");
        load();
      },
    });

  return (
    <section className="admin-panel">
      <div className="panel-head">
        <h2>Lake reports</h2>
        <div className="segmented" role="group" aria-label="Show">
          {(["open", "resolved"] as const).map((s) => (
            <button
              key={s}
              type="button"
              className={status === s ? "segment active" : "segment"}
              aria-pressed={status === s}
              onClick={() => {
                setRows(null);
                setStatus(s);
              }}
            >
              {s === "open" ? "Open" : "Resolved"}
            </button>
          ))}
        </div>
      </div>
      {error ? (
        <div className="backend-error">{error}</div>
      ) : rows === null ? (
        <div className="sk" style={{ height: 160 }} />
      ) : rows.length === 0 ? (
        <p className="muted">{status === "open" ? "No open lake reports." : "Nothing resolved yet."}</p>
      ) : (
        <ul className="report-list">
          {rows.map((r, i) => {
            const mapHref = r.waterbody_id
              ? `/map?lake=${r.waterbody_id}`
              : r.latitude !== null && r.longitude !== null
                ? `/map?at=${r.latitude},${r.longitude}`
                : null;
            return (
              <li key={r.id} className="report-card reveal" style={{ "--i": Math.min(i, 8) } as React.CSSProperties}>
                <div>
                  <strong>{r.reason_label}</strong>
                  <p className="muted small">
                    {mapHref ? (
                      <Link href={mapHref} className="text-link">
                        {r.lake_name ?? "Unnamed"}
                      </Link>
                    ) : (
                      (r.lake_name ?? "Unnamed")
                    )}
                    {r.state_code ? `, ${r.state_code}` : ""} · {r.reporter ?? "signed out"}, {when(r.created_at)}
                    {r.resolution && ` · ${r.resolution} ${when(r.resolved_at)}`}
                  </p>
                  {r.detail && <p className="small">“{r.detail}”</p>}
                </div>
                {r.status === "open" && (
                  <div className="row-actions">
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(r, "dismissed")}>
                      Dismiss
                    </button>
                    <button type="button" className="btn btn-primary btn-sm" onClick={() => act(r, "fixed")}>
                      Fixed
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

// -------------------------------------------------------------------- pins

function Pins({ confirmThen }: { confirmThen: (p: Pending) => void }) {
  const [status, setStatus] = useState("");
  const [visibility, setVisibility] = useState("");
  const [state, setState] = useState("");
  const states = useJurisdictions();
  const asked = useSearchParams().get("q") ?? "";
  const [q, setQ] = useState(asked);
  const [query, setQuery] = useState(asked);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paged<AdminPin> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const load = useCallback(() => {
    adminPins({ status, visibility, state, q: query, page }).then(setData).catch((e) => setError(errText(e)));
  }, [status, visibility, state, query, page]);
  useEffect(load, [load]);

  const setPinStatus = (p: AdminPin, s: "published" | "hidden" | "removed") =>
    confirmThen({
      title: s === "published" ? "Restore this catch?" : s === "hidden" ? "Hide this catch?" : "Remove this catch?",
      body:
        s === "published"
          ? "It becomes visible again (to everyone, if it's public)."
          : "Only its owner and admins will see it. Reversible.",
      confirm: s === "published" ? "Restore" : s === "hidden" ? "Hide" : "Remove",
      danger: s === "removed",
      run: async () => {
        await adminSetPinStatus(p.id, s);
        toast("Catch updated");
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
        <select aria-label="State" value={state} onChange={(e) => { setState(e.target.value); setPage(1); }}>
          <option value="">Any state</option>
          {states?.map((j) => (
            <option key={j.code} value={j.code}>
              {j.name}
            </option>
          ))}
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
                  <th>Catch</th>
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
                          <div className="muted small">{p.species_label ?? "—"}{checkNote(p)}{p.visibility === "private" ? " · only-me" : ""}</div>
                          {p.county_name && <div className="muted small">{p.lake ? `${p.lake.name} · ` : ""}{p.county_name}, {p.state_code}</div>}
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
                              body: "The catch and its photo files are deleted for good. Use this only for content that must not be kept.",
                              confirm: "Delete forever",
                              danger: true,
                              run: async () => {
                                await adminPurgePin(p.id);
                                toast("Catch deleted", "info");
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
                      No catches match.
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

// ------------------------------------------------------------------- audit

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
                    catch #{r.target_id}
                  </Link>
                ) : (
                  `${r.target_type.replace("_", " ")} #${r.target_id}`
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

const MISS_LABEL: Record<AskMiss["outcome"], string> = {
  no_match: "Nothing matched",
  unguided_fish: "Fish without a guide",
  other_state: "Only another state's rules",
  off_topic: "Not a fishing question",
};

/** Questions Ask couldn't answer, most asked first (backend services/ask_misses.py):
 * what the guides should cover next. Stored without who asked. */
function AskMisses() {
  const [days, setDays] = useState(30);
  const [outcome, setOutcome] = useState("");
  const [rows, setRows] = useState<AskMiss[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    adminAskMisses(days, outcome || undefined)
      .then(setRows)
      .catch((e) => setError(errText(e)));
  }, [days, outcome]);
  return (
    <section className="admin-panel">
      <div className="filter-bar">
        <select aria-label="Period" value={days} onChange={(e) => { setRows(null); setDays(Number(e.target.value)); }}>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
        <select aria-label="Why it missed" value={outcome} onChange={(e) => { setRows(null); setOutcome(e.target.value); }}>
          <option value="">Any reason</option>
          {Object.entries(MISS_LABEL).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <p className="muted small">Kept 90 days, without who asked. Email addresses, phone numbers and links are taken out.</p>
      {error && <div className="backend-error">{error}</div>}
      {!rows ? (
        <div className="sk" style={{ height: 200 }} />
      ) : rows.length === 0 ? (
        <p className="muted">No unanswered questions in this period.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Why</th>
                <th>Language</th>
                <th>Picked</th>
                <th className="num">Asked</th>
                <th>Last</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.outcome}:${r.question}`}>
                  <td lang={r.lang}>{r.question}</td>
                  <td className="small">{MISS_LABEL[r.outcome]}</td>
                  <td className="small">{r.lang}</td>
                  <td className="muted small">{[r.state, r.species_slug].filter(Boolean).join(" · ")}</td>
                  <td className="num">
                    {r.count}
                    {r.days > 1 && <div className="muted small">{r.days} days</div>}
                  </td>
                  <td className="muted small">{r.last_day}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
