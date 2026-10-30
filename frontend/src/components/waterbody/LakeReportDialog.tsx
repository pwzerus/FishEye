"use client";

import { useEffect, useState } from "react";

import { Modal } from "@/components/ui/Modal";
import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { getLakeReportOptions, reportLake } from "@/lib/api/session";

export type LakeReportTarget =
  | { kind: "problem"; lakeId: number; lakeName: string }
  // A lake that isn't on the map: placed where the middle of the map is.
  | { kind: "missing"; point: { latitude: number; longitude: number }; atPin?: boolean };

/** "Something wrong here?" on a lake, and "Missing a lake?" on the map
 * (backend ADR 0039). Goes to the admins' queue; anyone can send one. */
export function LakeReportDialog({
  target,
  open,
  onClose,
  onSent,
}: {
  target: LakeReportTarget;
  open: boolean;
  onClose: () => void;
  onSent: () => void;
}) {
  const all = useT();
  const t = all.lake;
  const [reasons, setReasons] = useState<{ id: string; label: string }[]>([]);
  const [reason, setReason] = useState("");
  const [name, setName] = useState("");
  const [detail, setDetail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const missing = target.kind === "missing";

  useEffect(() => {
    if (open && !missing && reasons.length === 0) {
      getLakeReportOptions()
        .then((o) => setReasons(o.reasons))
        .catch(() => setError(t.choicesError));
    }
  }, [open, missing, reasons.length, t.choicesError]);

  const ready = missing ? name.trim().length >= 2 : reason !== "" && (reason !== "other" || detail.trim() !== "");

  async function send() {
    setBusy(true);
    setError(null);
    try {
      await reportLake(
        target.kind === "missing"
          ? { reason: "missing", name: name.trim(), ...target.point, detail: detail.trim() || undefined }
          : { reason, waterbody_id: target.lakeId, detail: detail.trim() || undefined },
      );
      setReason("");
      setName("");
      setDetail("");
      onSent();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.sendError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={target.kind === "missing" ? t.missingTitle : t.wrongTitle(target.lakeName)}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            {all.common.cancel}
          </button>
          <button type="button" className="btn btn-primary btn-sm" disabled={!ready || busy} onClick={send}>
            {busy ? t.sending : t.send}
          </button>
        </>
      }
    >
      {missing ? (
        <>
          <p className="muted">{target.kind === "missing" && target.atPin ? t.missingNoteAtPin : t.missingNote}</p>
          <label className="field">
            <span>{t.lakeName}</span>
            <input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} placeholder={t.lakeNameExample} />
          </label>
        </>
      ) : (
        <>
          <p className="muted">{t.wrongNote}</p>
          <div className="radio-list" role="radiogroup" aria-label={t.whatsWrong}>
            {reasons.map((r) => (
              <label key={r.id} className={reason === r.id ? "radio-row active" : "radio-row"}>
                <input type="radio" name="lake-reason" value={r.id} checked={reason === r.id} onChange={() => setReason(r.id)} />
                <span>{t.reasons[r.id] ?? r.label}</span>
              </label>
            ))}
          </div>
        </>
      )}
      <label className="field">
        <span>{missing || reason === "other" ? t.details : t.detailsOptional}</span>
        <textarea
          rows={3}
          value={detail}
          maxLength={1000}
          onChange={(e) => setDetail(e.target.value)}
          placeholder={missing ? t.missingDetails : t.wrongDetails}
        />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </Modal>
  );
}
