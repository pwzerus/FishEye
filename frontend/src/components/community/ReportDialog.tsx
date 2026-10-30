"use client";

import { useEffect, useState } from "react";

import { Modal } from "@/components/ui/Modal";
import { useT } from "@/i18n/client";
import { ApiError } from "@/lib/api/client";
import { getPinOptions, reportPin } from "@/lib/api/session";

export function ReportDialog({
  pinId,
  open,
  onClose,
  onReported,
}: {
  pinId: number;
  open: boolean;
  onClose: () => void;
  onReported: (pinHidden: boolean) => void;
}) {
  const all = useT();
  const t = all.catch;
  const [reasons, setReasons] = useState<{ id: string; label: string }[]>([]);
  const [reason, setReason] = useState("");
  const [detail, setDetail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && reasons.length === 0) {
      getPinOptions()
        .then((o) => setReasons(o.report_reasons))
        .catch(() => setError(t.reasonsError));
    }
  }, [open, reasons.length, t.reasonsError]);

  async function send() {
    setBusy(true);
    setError(null);
    try {
      const r = await reportPin(pinId, reason, detail.trim() || undefined);
      onReported(r.pin_hidden);
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
      title={t.reportTitle}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            {all.common.cancel}
          </button>
          <button type="button" className="btn btn-primary btn-sm" disabled={!reason || busy} onClick={send}>
            {busy ? t.sending : t.sendReport}
          </button>
        </>
      }
    >
      <p className="muted">{t.reportNote}</p>
      <div className="radio-list" role="radiogroup" aria-label={t.reason}>
        {reasons.map((r) => (
          <label key={r.id} className={reason === r.id ? "radio-row active" : "radio-row"}>
            <input type="radio" name="reason" value={r.id} checked={reason === r.id} onChange={() => setReason(r.id)} />
            <span>{t.reasons[r.id] ?? r.label}</span>
          </label>
        ))}
      </div>
      <label className="field">
        <span>{t.anythingElse}</span>
        <textarea rows={2} value={detail} maxLength={500} onChange={(e) => setDetail(e.target.value)} />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </Modal>
  );
}
