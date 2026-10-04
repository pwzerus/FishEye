"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { FishArt } from "@/components/fish/FishArt";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/lib/api/client";
import { addPhotos, deletePhoto, deletePin, getPin, getPinOptions, updatePin } from "@/lib/api/session";
import { waterFor } from "@/lib/fishArt";
import type { PinDetail, PinOptions, PinVisibility } from "@/lib/api/types";
import { PhotoPicker } from "./PhotoPicker";
import { formatDay, PinBadges } from "./PinCard";
import { VisibilityToggle } from "./PinForm";
import { ReportDialog } from "./ReportDialog";

const PinMiniMap = dynamic(() => import("./PinMiniMap"), {
  ssr: false,
  loading: () => <div className="sk" style={{ height: "100%", borderRadius: 0 }} />,
});

function StatusBanner({ pin }: { pin: PinDetail }) {
  if (pin.status === "removed")
    return <div className="banner banner-danger">A moderator removed this pin. Only you (and admins) can see it.</div>;
  if (pin.status === "hidden")
    return (
      <div className="banner banner-warn">
        {pin.status_reason === "reports"
          ? "Hidden after several reports, until a moderator reviews it."
          : "A moderator hid this pin."}{" "}
        Only you (and admins) can see it, and it can&apos;t be edited or deleted until the review.
      </div>
    );
  if (pin.visibility === "private" && pin.is_mine)
    return <div className="banner banner-info">Only you can see this pin.</div>;
  return null;
}

function Gallery({ pin, onOpen }: { pin: PinDetail; onOpen: (i: number) => void }) {
  const [active, setActive] = useState(0);
  const photo = pin.photos[Math.min(active, pin.photos.length - 1)];
  if (!photo) {
    const [wa, wb] = waterFor(pin.species_slug ?? "bluegill");
    return (
      <div className="gallery-empty" style={{ "--wa": wa, "--wb": wb } as React.CSSProperties}>
        {pin.species_slug ? <FishArt slug={pin.species_slug} uid={`pd-${pin.id}`} className="swimming" /> : null}
        <span>No photos yet</span>
      </div>
    );
  }
  return (
    <div className="gallery">
      <button type="button" className="gallery-main" onClick={() => onOpen(active)} aria-label="View full size">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img key={photo.id} src={photo.url} alt={`Photo ${active + 1} of ${pin.title}`} />
      </button>
      {pin.photos.length > 1 && (
        <div className="gallery-thumbs">
          {pin.photos.map((p, i) => (
            <button
              key={p.id}
              type="button"
              className={i === active ? "gallery-thumb active" : "gallery-thumb"}
              onClick={() => setActive(i)}
              aria-label={`Show photo ${i + 1}`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={p.thumb_url} alt="" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function PinDetailView({ pinId }: { pinId: number }) {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [pin, setPin] = useState<PinDetail | null>(null);
  const [error, setError] = useState<{ status: number; message: string } | null>(null);
  const [lightbox, setLightbox] = useState<number | null>(null);
  const [reporting, setReporting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    getPin(pinId)
      .then((p) => {
        setPin(p);
        setError(null);
      })
      .catch((e: unknown) =>
        setError(e instanceof ApiError ? { status: e.status, message: e.message } : { status: 0, message: "Couldn't load." }),
      );
  }, [pinId]);

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, user, load]);

  if (error) {
    return (
      <div className="empty-state">
        <h2>{error.status === 404 ? "This pin isn't here" : "Couldn't load this pin"}</h2>
        <p className="muted">
          {error.status === 404 ? "It may be private, removed, or never existed." : error.message}
        </p>
        <Link href="/community" className="btn btn-primary btn-sm" transitionTypes={["nav-back"]}>
          Back to community
        </Link>
      </div>
    );
  }
  if (!pin) {
    return (
      <div className="pin-layout" aria-busy="true">
        <div className="sk" style={{ aspectRatio: "4 / 3", borderRadius: 24 }} />
        <div className="pin-info">
          <div className="sk sk-title" />
          <div className="sk sk-line" />
          <div className="sk sk-line short" />
        </div>
      </div>
    );
  }

  const when = formatDay(pin.caught_on);

  return (
    <>
      <Link href="/community" className="back-link" transitionTypes={["nav-back"]}>
        <span aria-hidden="true">←</span> Community
      </Link>
      <StatusBanner pin={pin} />

      <div className="pin-layout">
        <div className="reveal" style={{ "--i": 0 } as React.CSSProperties}>
          <Gallery pin={pin} onOpen={setLightbox} />
        </div>

        <div className="pin-info">
          <div className="pin-tags reveal" style={{ "--i": 1 } as React.CSSProperties}>
            {pin.species_label && <span className="tag tag-species">{pin.species_label}</span>}
            <PinBadges pin={pin} />
          </div>
          <h1 className="reveal" style={{ "--i": 2 } as React.CSSProperties}>
            {pin.title}
          </h1>
          <p className="pin-byline reveal" style={{ "--i": 3 } as React.CSSProperties}>
            <span className="byline-avatar" aria-hidden="true">
              {pin.author.display_name.slice(0, 1).toUpperCase()}
            </span>
            <span>
              {pin.is_mine ? "You" : pin.author.display_name}
              {when && <> · caught {when}</>}
            </span>
          </p>
          {pin.note && (
            <p className="pin-note reveal" style={{ "--i": 4 } as React.CSSProperties}>
              {pin.note}
            </p>
          )}
          <dl className="pin-facts reveal" style={{ "--i": 5 } as React.CSSProperties}>
            {pin.lake && (
              <div>
                <dt>Near</dt>
                <dd>
                  <Link href={`/map?lake=${pin.lake.id}`} className="text-link">
                    {pin.lake.name}
                  </Link>
                </dd>
              </div>
            )}
            <div>
              <dt>Location</dt>
              <dd>
                {pin.latitude.toFixed(4)}, {pin.longitude.toFixed(4)}
              </dd>
            </div>
            <div>
              <dt>Pinned</dt>
              <dd>{formatDay(pin.created_at)}</dd>
            </div>
          </dl>

          <div className="pin-map reveal" style={{ "--i": 6 } as React.CSSProperties}>
            <PinMiniMap lat={pin.latitude} lng={pin.longitude} isPrivate={pin.visibility === "private"} />
            <Link href={`/map?at=${pin.latitude},${pin.longitude}`} className="pin-map-open">
              Open in map →
            </Link>
          </div>

          <div className="pin-actions reveal" style={{ "--i": 7 } as React.CSSProperties}>
            {pin.can_edit && (
              <>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>
                  Edit
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAdding(true)}>
                  Photos
                </button>
                <button type="button" className="btn btn-ghost btn-sm btn-danger-text" onClick={() => setConfirmDelete(true)}>
                  Delete
                </button>
              </>
            )}
            {!pin.is_mine && pin.can_report && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setReporting(true)}>
                Report
              </button>
            )}
            {pin.reported_by_me && <span className="muted small">You reported this pin.</span>}
            {!user && !pin.is_mine && (
              <Link href={`/login?next=/community/${pin.id}`} className="muted small text-link">
                Sign in to report
              </Link>
            )}
          </div>
        </div>
      </div>

      <Modal open={lightbox !== null} onClose={() => setLightbox(null)} title={pin.title}>
        {lightbox !== null && pin.photos[lightbox] && (
          <div className="lightbox">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={pin.photos[lightbox].url} alt={`Photo ${lightbox + 1} of ${pin.title}`} />
            {pin.photos.length > 1 && (
              <div className="lightbox-nav">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setLightbox((lightbox + pin.photos.length - 1) % pin.photos.length)}>
                  ← Prev
                </button>
                <span className="muted">
                  {lightbox + 1} / {pin.photos.length}
                </span>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setLightbox((lightbox + 1) % pin.photos.length)}>
                  Next →
                </button>
              </div>
            )}
          </div>
        )}
      </Modal>

      <ReportDialog
        pinId={pin.id}
        open={reporting}
        onClose={() => setReporting(false)}
        onReported={(hidden) => {
          toast(hidden ? "Thanks. The pin is hidden until a moderator reviews it." : "Thanks. A moderator will take a look.");
          load();
        }}
      />

      {editing && (
        <EditPinDialog
          pin={pin}
          onClose={() => setEditing(false)}
          onSaved={(p) => {
            setPin(p);
            setEditing(false);
            toast("Pin updated");
          }}
        />
      )}

      {adding && (
        <PhotosDialog
          pin={pin}
          onClose={() => setAdding(false)}
          onChanged={(p) => setPin(p)}
        />
      )}

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Delete this pin?"
        tone="danger"
        footer={
          <>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirmDelete(false)}>
              Keep it
            </button>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              onClick={async () => {
                try {
                  await deletePin(pin.id);
                  toast("Pin deleted", "info");
                  router.push("/account#pins");
                } catch (e) {
                  toast(e instanceof ApiError ? e.message : "Couldn't delete", "error");
                }
              }}
            >
              Delete pin
            </button>
          </>
        }
      >
        <p>The pin and its photos are deleted for good. This can&apos;t be undone.</p>
      </Modal>
    </>
  );
}

function EditPinDialog({ pin, onClose, onSaved }: { pin: PinDetail; onClose: () => void; onSaved: (p: PinDetail) => void }) {
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [title, setTitle] = useState(pin.title);
  const [note, setNote] = useState(pin.note ?? "");
  const [species, setSpecies] = useState(pin.species_slug ?? (pin.species_label ? "__other" : ""));
  const [other, setOther] = useState(pin.species_slug ? "" : (pin.species_label ?? ""));
  const [caughtOn, setCaughtOn] = useState(pin.caught_on ?? "");
  const [visibility, setVisibility] = useState<PinVisibility>(pin.visibility);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPinOptions().then(setOptions).catch(() => undefined);
  }, []);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const p = await updatePin(pin.id, {
        title,
        note: note.trim() || undefined,
        clear_note: !note.trim(),
        ...(species === ""
          ? { clear_species: true }
          : species === "__other"
            ? { species_other: other, species_slug: undefined }
            : { species_slug: species }),
        ...(caughtOn ? { caught_on: caughtOn } : { clear_caught_on: true }),
        visibility,
      });
      onSaved(p);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't save.");
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Edit pin"
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary btn-sm" disabled={busy || title.trim().length < 3} onClick={save}>
            {busy ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <div className="pin-form">
        <label className="field">
          <span>Title</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={80} />
        </label>
        <div className="field-row">
          <label className="field">
            <span>Fish</span>
            <select value={species} onChange={(e) => setSpecies(e.target.value)}>
              <option value="">Not sure / none</option>
              {options?.species.map((s) => (
                <option key={s.slug} value={s.slug}>
                  {s.label}
                </option>
              ))}
              <option value="__other">Other…</option>
            </select>
          </label>
          <label className="field">
            <span>Date</span>
            <input type="date" value={caughtOn} onChange={(e) => setCaughtOn(e.target.value)} />
          </label>
        </div>
        {species === "__other" && (
          <label className="field">
            <span>Which fish?</span>
            <input value={other} onChange={(e) => setOther(e.target.value)} maxLength={60} />
          </label>
        )}
        <label className="field">
          <span>Notes</span>
          <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
        </label>
        <div className="field">
          <span>Who can see it</span>
          <VisibilityToggle value={visibility} onChange={setVisibility} />
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}

function PhotosDialog({ pin, onClose, onChanged }: { pin: PinDetail; onClose: () => void; onChanged: (p: PinDetail) => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const remaining = 4 - pin.photos.length;

  async function upload() {
    setError(null);
    setProgress(0);
    try {
      const p = await addPhotos(pin.id, files, setProgress);
      onChanged(p);
      setFiles([]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setProgress(null);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Photos"
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            Done
          </button>
          {files.length > 0 && (
            <button type="button" className="btn btn-primary btn-sm" disabled={progress !== null} onClick={upload}>
              {progress !== null ? `Uploading ${Math.round(progress * 100)}%` : `Upload ${files.length}`}
            </button>
          )}
        </>
      }
    >
      {pin.photos.length > 0 && (
        <div className="photo-grid">
          {pin.photos.map((p, i) => (
            <figure key={p.id} className="photo-thumb">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={p.thumb_url} alt={`Photo ${i + 1}`} />
              <button
                type="button"
                className="photo-remove"
                aria-label={`Delete photo ${i + 1}`}
                onClick={async () => {
                  try {
                    onChanged(await deletePhoto(pin.id, p.id));
                  } catch (e) {
                    setError(e instanceof ApiError ? e.message : "Couldn't delete.");
                  }
                }}
              >
                ×
              </button>
            </figure>
          ))}
        </div>
      )}
      {remaining > 0 ? (
        <PhotoPicker files={files} onChange={setFiles} max={remaining} maxMb={10} disabled={progress !== null} />
      ) : (
        <p className="muted">This pin has the maximum of 4 photos. Delete one to add another.</p>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </Modal>
  );
}
