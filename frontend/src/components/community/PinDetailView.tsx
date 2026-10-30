"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { FishArt } from "@/components/fish/FishArt";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { useLocale, useLocaleTag, useT } from "@/i18n/client";
import { localSpecies } from "@/i18n/names";
import { ApiError } from "@/lib/api/client";
import { addPhotos, deletePhoto, deletePin, getPin, getPinOptions, updatePin } from "@/lib/api/session";
import { waterFor } from "@/lib/fishArt";
import type { PinDetail, PinOptions, PinVisibility } from "@/lib/api/types";
import { PhotoPicker } from "./PhotoPicker";
import { AdminModeration } from "./AdminModeration";
import { formatDay, PhotoAtSpot, PinBadges, placeText, SpeciesCheck, speciesCheckShort } from "./PinCard";
import { ShareSpotToggle, SpeciesOptions, VisibilityToggle } from "./PinForm";
import { ReportDialog } from "./ReportDialog";

const PinMiniMap = dynamic(() => import("./PinMiniMap"), {
  ssr: false,
  loading: () => <div className="sk" style={{ height: "100%", borderRadius: 0 }} />,
});

function StatusBanner({ pin }: { pin: PinDetail }) {
  const t = useT().catch;
  if (pin.status === "removed") return <div className="banner banner-danger">{t.removedBanner}</div>;
  if (pin.status === "hidden")
    return (
      <div className="banner banner-warn">
        {pin.status_reason === "reports" ? t.hiddenReportsBanner : t.hiddenModeratorBanner} {t.hiddenTail}
      </div>
    );
  if (pin.visibility === "private" && pin.is_mine) return <div className="banner banner-info">{t.privateBanner}</div>;
  return null;
}

function Gallery({ pin, onOpen }: { pin: PinDetail; onOpen: (i: number) => void }) {
  const t = useT().catch;
  const [active, setActive] = useState(0);
  const photo = pin.photos[Math.min(active, pin.photos.length - 1)];
  if (!photo) {
    const [wa, wb] = waterFor(pin.species_slug ?? "bluegill");
    return (
      <div className="gallery-empty" style={{ "--wa": wa, "--wb": wb } as React.CSSProperties}>
        {pin.species_slug ? <FishArt slug={pin.species_slug} uid={`pd-${pin.id}`} className="swimming" /> : null}
        <span>{t.noPhotos}</span>
      </div>
    );
  }
  return (
    <div className="gallery">
      <button type="button" className="gallery-main" onClick={() => onOpen(active)} aria-label={t.viewFull}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img key={photo.id} src={photo.url} alt={t.photoOf(active + 1, pin.title)} />
      </button>
      {pin.photos.length > 1 && (
        <div className="gallery-thumbs">
          {pin.photos.map((p, i) => (
            <button
              key={p.id}
              type="button"
              className={i === active ? "gallery-thumb active" : "gallery-thumb"}
              onClick={() => setActive(i)}
              aria-label={t.showPhoto(i + 1)}
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
  const all = useT();
  const t = all.catch;
  const tag = useLocaleTag();
  const locale = useLocale();
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
        setError(e instanceof ApiError ? { status: e.status, message: e.message } : { status: 0, message: t.loadError }),
      );
  }, [pinId, t.loadError]);

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, user, load]);

  if (error) {
    return (
      <div className="empty-state">
        <h2>{error.status === 404 ? t.notHere : t.couldntLoad}</h2>
        <p className="muted">{error.status === 404 ? t.maybePrivate : error.message}</p>
        <Link href="/community" className="btn btn-primary btn-sm" transitionTypes={["nav-back"]}>
          {t.backToCatches}
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

  const when = formatDay(pin.caught_on, tag);
  const checkNote = speciesCheckShort(all, pin, locale);
  const waterHref = pin.water?.kind === "lake" ? `/map?lake=${pin.water.id}` : null;

  return (
    <>
      <Link href="/community" className="back-link" transitionTypes={["nav-back"]}>
        <span aria-hidden="true">←</span> {all.nav.catches}
      </Link>
      <StatusBanner pin={pin} />

      <div className="pin-layout">
        <div className="reveal" style={{ "--i": 0 } as React.CSSProperties}>
          <Gallery pin={pin} onOpen={setLightbox} />
        </div>

        <div className="pin-info">
          <div className="pin-tags reveal" style={{ "--i": 1 } as React.CSSProperties}>
            {pin.species_label && (
              <span className="tag tag-species">{localSpecies(pin.species_slug, pin.species_label, locale)}</span>
            )}
            <SpeciesCheck pin={pin} />
            <PhotoAtSpot pin={pin} />
            <PinBadges pin={pin} />
          </div>
          {checkNote && (
            <p className="pin-check-note muted reveal" style={{ "--i": 1 } as React.CSSProperties}>
              {checkNote}
            </p>
          )}
          <h1 className="reveal" style={{ "--i": 2 } as React.CSSProperties}>
            {pin.title}
          </h1>
          <p className="pin-byline reveal" style={{ "--i": 3 } as React.CSSProperties}>
            <span className="byline-avatar" aria-hidden="true">
              {pin.author.display_name.slice(0, 1).toUpperCase()}
            </span>
            <span>
              {pin.is_mine ? t.you : pin.author.display_name}
              {when && <> · {t.caught(when)}</>}
            </span>
          </p>
          {pin.note && (
            <p className="pin-note reveal" style={{ "--i": 4 } as React.CSSProperties}>
              {pin.note}
            </p>
          )}
          <dl className="pin-facts reveal" style={{ "--i": 5 } as React.CSSProperties}>
            {(pin.water ?? pin.lake) && (
              <div>
                <dt>{t.factWater}</dt>
                <dd>
                  {pin.water ? (
                    waterHref ? (
                      <Link href={waterHref} className="text-link">
                        {pin.water.name}
                      </Link>
                    ) : (
                      pin.water.name
                    )
                  ) : (
                    pin.lake && (
                      <Link href={`/map?lake=${pin.lake.id}`} className="text-link">
                        {pin.lake.name}
                      </Link>
                    )
                  )}
                </dd>
              </div>
            )}
            <div>
              <dt>{t.factLocation}</dt>
              <dd>
                {pin.location_shown === "exact" ? (
                  <>
                    {pin.latitude.toFixed(4)}, {pin.longitude.toFixed(4)}
                  </>
                ) : (
                  // The angler kept the spot to themselves (backend ADR 0038).
                  <>{placeText(all, pin, pin.location_shown)}</>
                )}
              </dd>
            </div>
            {pin.is_mine && pin.visibility === "public" && (
              <div>
                <dt>{t.factOthersSee}</dt>
                <dd>{placeText(all, pin, pin.public_place)}</dd>
              </div>
            )}
            <div>
              <dt>{t.factShared}</dt>
              <dd>{formatDay(pin.created_at, tag)}</dd>
            </div>
          </dl>

          <div className="pin-map reveal" style={{ "--i": 6 } as React.CSSProperties}>
            <PinMiniMap
              lat={pin.latitude}
              lng={pin.longitude}
              isPrivate={pin.visibility === "private"}
              place={pin.location_shown}
            />
            <Link href={`/map?at=${pin.latitude},${pin.longitude}`} className="pin-map-open">
              {t.openInMap}
            </Link>
          </div>

          <div className="pin-actions reveal" style={{ "--i": 7 } as React.CSSProperties}>
            {pin.visibility === "public" && pin.status === "published" && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={async () => {
                  const url = window.location.href;
                  const title = pin.species_label ? `${pin.species_label} · ${pin.title}` : pin.title;
                  // The phone's own share sheet where there is one; else the link.
                  if (navigator.share) {
                    try {
                      await navigator.share({ title, url });
                    } catch {
                      // closed without sharing
                    }
                    return;
                  }
                  try {
                    await navigator.clipboard.writeText(url);
                    toast(t.linkCopied);
                  } catch {
                    toast(t.copyFailed, "error");
                  }
                }}
              >
                {t.share}
              </button>
            )}
            {pin.can_edit && (
              <>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>
                  {t.edit}
                </button>
                {/* Back on the map, at the spot: tap the water it was really on. */}
                <Link href={`/map?move=${pin.id}`} className="btn btn-ghost btn-sm">
                  {t.move}
                </Link>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAdding(true)}>
                  {t.photos}
                </button>
                <button type="button" className="btn btn-ghost btn-sm btn-danger-text" onClick={() => setConfirmDelete(true)}>
                  {t.delete}
                </button>
              </>
            )}
            {/* Locked for editing while moderated, but always the owner's to delete. */}
            {pin.is_mine && !pin.can_edit && (
              <button type="button" className="btn btn-ghost btn-sm btn-danger-text" onClick={() => setConfirmDelete(true)}>
                {t.delete}
              </button>
            )}
            {!pin.is_mine && pin.can_report && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setReporting(true)}>
                {t.report}
              </button>
            )}
            {pin.reported_by_me && <span className="muted small">{t.reportedByMe}</span>}
            {!user && !pin.is_mine && (
              <Link href={`/login?next=/community/${pin.id}`} className="muted small text-link">
                {t.signInToReport}
              </Link>
            )}
          </div>
          {user?.role === "admin" && (
            <AdminModeration pin={pin} onChanged={load} onPurged={() => router.push("/community")} />
          )}
        </div>
      </div>

      <Modal open={lightbox !== null} onClose={() => setLightbox(null)} title={pin.title}>
        {lightbox !== null && pin.photos[lightbox] && (
          <div className="lightbox">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={pin.photos[lightbox].url} alt={t.photoOf(lightbox + 1, pin.title)} />
            {pin.photos.length > 1 && (
              <div className="lightbox-nav">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setLightbox((lightbox + pin.photos.length - 1) % pin.photos.length)}>
                  {t.prev}
                </button>
                <span className="muted">
                  {lightbox + 1} / {pin.photos.length}
                </span>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setLightbox((lightbox + 1) % pin.photos.length)}>
                  {t.next}
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
          toast(hidden ? t.reportHidden : t.reportThanks);
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
            toast(t.updated);
          }}
        />
      )}

      {adding && <PhotosDialog pin={pin} onClose={() => setAdding(false)} onChanged={(p) => setPin(p)} />}

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title={t.deleteTitle}
        tone="danger"
        footer={
          <>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirmDelete(false)}>
              {t.keepIt}
            </button>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              onClick={async () => {
                try {
                  await deletePin(pin.id);
                  toast(t.deleted, "info");
                  router.push("/account#pins");
                } catch (e) {
                  toast(e instanceof ApiError ? e.message : t.deleteFailed, "error");
                }
              }}
            >
              {t.deleteCatch}
            </button>
          </>
        }
      >
        <p>{t.deleteBody}</p>
      </Modal>
    </>
  );
}

function EditPinDialog({ pin, onClose, onSaved }: { pin: PinDetail; onClose: () => void; onSaved: (p: PinDetail) => void }) {
  const all = useT();
  const t = all.catch;
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [title, setTitle] = useState(pin.title);
  const [note, setNote] = useState(pin.note ?? "");
  const [species, setSpecies] = useState(pin.species_slug ?? (pin.species_label ? "__other" : ""));
  const [other, setOther] = useState(pin.species_slug ? "" : (pin.species_label ?? ""));
  const [caughtOn, setCaughtOn] = useState(pin.caught_on ?? "");
  const [visibility, setVisibility] = useState<PinVisibility>(pin.visibility);
  const [shareExact, setShareExact] = useState(pin.share_exact);
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
        share_exact: shareExact,
      });
      onSaved(p);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t.saveFailed);
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t.editTitle}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            {all.common.cancel}
          </button>
          <button type="button" className="btn btn-primary btn-sm" disabled={busy || title.trim().length < 3} onClick={save}>
            {busy ? all.common.saving : all.common.save}
          </button>
        </>
      }
    >
      <div className="pin-form">
        <label className="field">
          <span>{t.title}</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={80} />
        </label>
        <div className="field-row">
          <label className="field">
            <span>{t.fish}</span>
            <select value={species} onChange={(e) => setSpecies(e.target.value)}>
              <SpeciesOptions options={options} otherValue="__other" />
            </select>
          </label>
          <label className="field">
            <span>{t.date}</span>
            <input type="date" value={caughtOn} onChange={(e) => setCaughtOn(e.target.value)} />
          </label>
        </div>
        {species === "__other" && (
          <label className="field">
            <span>{t.whichFish}</span>
            <input value={other} onChange={(e) => setOther(e.target.value)} maxLength={60} />
          </label>
        )}
        {species !== (pin.species_slug ?? (pin.species_label ? "__other" : "")) && species !== "" && (
          <p className="hint">{t.fishChangeNote}</p>
        )}
        <label className="field">
          <span>{t.notes}</span>
          <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
        </label>
        <div className="field">
          <span>{t.whoSees}</span>
          <VisibilityToggle value={visibility} onChange={setVisibility} />
        </div>
        {visibility === "public" && <ShareSpotToggle value={shareExact} onChange={setShareExact} />}
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
  const t = useT().catch;
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
      setError(e instanceof ApiError ? e.message : t.uploadFailed);
    } finally {
      setProgress(null);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t.photos}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            {t.done}
          </button>
          {files.length > 0 && (
            <button type="button" className="btn btn-primary btn-sm" disabled={progress !== null} onClick={upload}>
              {progress !== null ? t.uploading(Math.round(progress * 100)) : t.uploadN(files.length)}
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
              <img src={p.thumb_url} alt={t.photoOf(i + 1, pin.title)} />
              <button
                type="button"
                className="photo-remove"
                aria-label={t.deletePhoto(i + 1)}
                onClick={async () => {
                  try {
                    onChanged(await deletePhoto(pin.id, p.id));
                  } catch (e) {
                    setError(e instanceof ApiError ? e.message : t.deleteFailed);
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
        <p className="muted">{t.maxPhotos}</p>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </Modal>
  );
}
