"use client";

import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

/**
 * A dialog built on <dialog>: the browser handles focus trapping, the
 * inert background and Escape. We add the open/close animation and
 * close-on-backdrop-click.
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  tone = "default",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  tone?: "default" | "danger";
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      if (typeof d.showModal === "function") d.showModal();
      else d.setAttribute("open", "");
    } else if (!open && d.open) {
      if (typeof d.close === "function") d.close();
      else d.removeAttribute("open");
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`modal modal-${tone}`}
      aria-labelledby="modal-title"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      {open && (
        <div className="modal-card">
          <header className="modal-head">
            <h2 id="modal-title">{title}</h2>
            <button type="button" className="icon-btn" aria-label="Close" onClick={onClose}>
              ×
            </button>
          </header>
          <div className="modal-body">{children}</div>
          {footer && <footer className="modal-foot">{footer}</footer>}
        </div>
      )}
    </dialog>
  );
}
