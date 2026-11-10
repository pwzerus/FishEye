"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { adminFeedback, adminFeedbackExport, adminUpdateFeedback } from "@/lib/api/session";
import type { AdminFeedback, Paged } from "@/lib/api/types";
import { Pager, copyText, errText, when } from "./shared";

/** What people sent through "Send feedback" (backend services/feedback.py).
 * "Copy for Claude" leaves out names and addresses; the same text comes from
 * `python -m app.cli.feedback` on the server. */
export function AdminFeedbackTab() {
  const [status, setStatus] = useState("new");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paged<AdminFeedback> | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Shown when the browser won't let the page use the clipboard.
  const [manual, setManual] = useState<string | null>(null);
  const toast = useToast();

  const load = useCallback(() => {
    adminFeedback({ status, q: query, page }).then(setData).catch((e) => setError(errText(e)));
  }, [status, query, page]);
  useEffect(load, [load]);

  const mark = async (f: AdminFeedback, next: "new" | "done") => {
    try {
      await adminUpdateFeedback(f.id, next);
      load();
    } catch (e) {
      toast(errText(e), "error");
    }
  };

  const copyAll = async () => {
    try {
      const { count, text } = await adminFeedbackExport(status);
      if (await copyText(text)) toast(`Copied ${count} message${count === 1 ? "" : "s"}`);
      else setManual(text);
    } catch (e) {
      toast(errText(e), "error");
    }
  };

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
        <select
          aria-label="Status"
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
        >
          <option value="new">New</option>
          <option value="done">Handled</option>
          <option value="">All</option>
        </select>
        <input className="filter-input" placeholder="Search the messages" value={q} onChange={(e) => setQ(e.target.value)} />
        <button type="submit" className="btn btn-ghost btn-sm">
          Search
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={copyAll}>
          Copy for Claude
        </button>
      </form>
      {error && <div className="backend-error">{error}</div>}
      {!data ? (
        <div className="sk" style={{ height: 160 }} />
      ) : data.items.length === 0 ? (
        <p className="muted">{status === "new" ? "No new feedback." : "Nothing here."}</p>
      ) : (
        <>
          <ul className="feedback-list">
            {data.items.map((f) => (
              <li key={f.id} className="feedback-item">
                <p className="feedback-message">{f.message}</p>
                <div className="feedback-meta muted small">
                  {f.user_id ? (
                    <Link href={`/admin?tab=users&user=${f.user_id}`} className="text-link">
                      {f.author_name}
                    </Link>
                  ) : (
                    <span>{f.signed_out ? (f.contact ? `Signed out · ${f.contact}` : "Signed out, no address") : "Deleted account"}</span>
                  )}
                  <span>{when(f.created_at)}</span>
                  {f.page && <span>{f.page}</span>}
                  {f.lang && <span>{f.lang}</span>}
                </div>
                <div className="row-actions">
                  {(f.author_email ?? f.contact) && (
                    <a className="btn btn-ghost btn-xs" href={`mailto:${f.author_email ?? f.contact}?subject=${encodeURIComponent("Your FishEye feedback")}`}>
                      Reply by email
                    </a>
                  )}
                  {f.status === "new" ? (
                    <button type="button" className="btn btn-ghost btn-xs" onClick={() => mark(f, "done")}>
                      Mark handled
                    </button>
                  ) : (
                    <button type="button" className="btn btn-ghost btn-xs" onClick={() => mark(f, "new")}>
                      Reopen
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <Pager page={data.page} total={data.total} size={data.page_size} onPage={setPage} />
        </>
      )}
      <Modal open={manual !== null} onClose={() => setManual(null)} title="Copy this">
        <textarea readOnly rows={12} className="copy-box" value={manual ?? ""} onFocus={(e) => e.target.select()} />
      </Modal>
    </section>
  );
}
