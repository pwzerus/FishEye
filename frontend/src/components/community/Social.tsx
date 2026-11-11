"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { useLocaleTag, useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { addComment, deleteComment, getPinOptions, likePin, listComments, reportComment, unlikePin } from "@/lib/api/session";
import type { PinComment, PinDetail } from "@/lib/api/types";
import { formatDay } from "./PinCard";
import { Heart } from "./SocialCounts";

const MAX_COMMENT = 500;

/** The like button on a catch's page, with what it has so far. */
export function LikeButton({ pin }: { pin: PinDetail }) {
  const t = useT().social;
  const { user } = useAuth();
  const toast = useToast();
  const [state, setState] = useState({ liked: pin.liked_by_me ?? false, count: pin.like_count ?? 0 });
  const [busy, setBusy] = useState(false);
  if (pin.visibility !== "public" || pin.status !== "published") return null;

  if (pin.is_mine) {
    return (
      <span className="like-button is-own">
        <Heart filled={state.count > 0} /> {t.likes(state.count)}
      </span>
    );
  }
  if (!user) {
    return (
      <Link className="like-button" href={`/login?next=/community/${pin.id}`} title={t.signInToLike}>
        <Heart /> {t.likes(state.count)}
      </Link>
    );
  }

  async function toggle() {
    const before = state;
    setBusy(true);
    setState({ liked: !before.liked, count: before.count + (before.liked ? -1 : 1) });
    try {
      const after = await (before.liked ? unlikePin(pin.id) : likePin(pin.id));
      setState({ liked: after.liked, count: after.like_count });
    } catch (err) {
      setState(before);
      toast(err instanceof ApiError ? err.message : t.failed, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className={state.liked ? "like-button is-liked" : "like-button"}
      aria-pressed={state.liked}
      disabled={busy}
      onClick={toggle}
    >
      <Heart filled={state.liked} /> {state.liked ? t.liked : t.like} · {state.count}
    </button>
  );
}

function ReportCommentDialog({ pinId, commentId, onClose, onDone }: { pinId: number; commentId: number | null; onClose: () => void; onDone: () => void }) {
  const all = useT();
  const t = all.social;
  const toast = useToast();
  const [reasons, setReasons] = useState<{ id: string; label: string }[]>([]);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (commentId !== null) getPinOptions().then((o) => setReasons(o.report_reasons)).catch(() => undefined);
  }, [commentId]);
  return (
    <Modal open={commentId !== null} onClose={onClose} title={t.reportTitle}>
      <label className="field">
        <span>{t.reportWhy}</span>
        <select value={reason} onChange={(e) => setReason(e.target.value)}>
          <option value="">{t.reportPick}</option>
          {reasons.map((r) => (
            <option key={r.id} value={r.id}>
              {/* The reader's language, as the catch report has it; a reason
                  added on the server before its words are here stays English. */}
              {all.catch.reasons[r.id] ?? r.label}
            </option>
          ))}
        </select>
      </label>
      <div className="form-actions">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
          {all.common.cancel}
        </button>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={!reason || busy}
          onClick={async () => {
            if (commentId === null) return;
            setBusy(true);
            try {
              await reportComment(pinId, commentId, reason);
              toast(t.reported);
              onDone();
            } catch (err) {
              toast(err instanceof ApiError ? err.message : t.failed, "error");
            } finally {
              setBusy(false);
            }
          }}
        >
          {t.report}
        </button>
      </div>
    </Modal>
  );
}

/** The conversation under a public catch. */
export function CommentsSection({ pin }: { pin: PinDetail }) {
  const all = useT();
  const t = all.social;
  const tag = useLocaleTag();
  const { user, loading } = useAuth();
  const toast = useToast();
  const [comments, setComments] = useState<PinComment[] | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [reporting, setReporting] = useState<number | null>(null);
  // A delete is two taps: on a phone "Delete" sits a thumb's width from "Report".
  const [deleting, setDeleting] = useState<number | null>(null);

  const load = useCallback(() => {
    listComments(pin.id).then(setComments).catch(() => setComments([]));
  }, [pin.id]);

  useEffect(() => {
    if (!loading) load();
  }, [loading, user, load]);

  if (pin.visibility !== "public" || pin.status !== "published") return null;

  async function post(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const added = await addComment(pin.id, text);
      setComments((now) => [...(now ?? []), added]);
      setText("");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : t.failed, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="pin-comments" aria-label={t.comments}>
      <h2>
        {t.comments}
        {comments !== null && comments.length > 0 && <span className="muted"> {comments.length}</span>}
      </h2>
      {comments === null ? (
        <div className="sk sk-line" />
      ) : comments.length === 0 ? (
        <p className="muted">{t.noComments}</p>
      ) : (
        <ul className="comment-list">
          {comments.map((c) => (
            <li key={c.id} className="comment">
              <span className="byline-avatar" aria-hidden="true">
                {c.author.display_name.slice(0, 1).toUpperCase()}
              </span>
              <div>
                <p className="comment-head">
                  <Link href={`/community/anglers/${c.author.id}`} className="comment-author">
                    {c.is_mine ? all.catch.you : c.author.display_name}
                  </Link>
                  <span className="muted small">{formatDay(c.created_at, tag)}</span>
                  {c.status === "hidden" && <span className="tag tag-hidden">{all.catch.hidden}</span>}
                </p>
                <p className="comment-body">{c.body}</p>
                <p className="comment-actions">
                  {c.can_delete && deleting !== c.id && (
                    <button type="button" className="text-link" onClick={() => setDeleting(c.id)}>
                      {t.delete}
                    </button>
                  )}
                  {c.can_delete && deleting === c.id && (
                    <>
                      <button
                        type="button"
                        className="text-link text-link-danger"
                        onClick={async () => {
                          try {
                            await deleteComment(pin.id, c.id);
                            setComments((now) => (now ?? []).filter((o) => o.id !== c.id));
                          } catch (err) {
                            toast(err instanceof ApiError ? err.message : t.failed, "error");
                          }
                          setDeleting(null);
                        }}
                      >
                        {t.deleteSure}
                      </button>
                      <button type="button" className="text-link" onClick={() => setDeleting(null)}>
                        {all.common.cancel}
                      </button>
                    </>
                  )}
                  {c.can_report && (
                    <button type="button" className="text-link" onClick={() => setReporting(c.id)}>
                      {t.report}
                    </button>
                  )}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {user ? (
        <form className="comment-form" onSubmit={post}>
          <label className="sr-only" htmlFor="new-comment">
            {t.commentLabel}
          </label>
          <textarea
            id="new-comment"
            rows={2}
            maxLength={MAX_COMMENT}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t.commentPlaceholder}
            disabled={busy}
          />
          <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !text.trim()}>
            {t.post}
          </button>
        </form>
      ) : (
        !loading && (
          <p>
            <Link href={`/login?next=/community/${pin.id}`} className="text-link">
              {t.signInToComment}
            </Link>
          </p>
        )
      )}

      <ReportCommentDialog
        pinId={pin.id}
        commentId={reporting}
        onClose={() => setReporting(null)}
        onDone={() => {
          setReporting(null);
          load();
        }}
      />
    </section>
  );
}
