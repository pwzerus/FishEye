import Link from "next/link";

import { FishArt } from "@/components/fish/FishArt";
import { waterFor } from "@/lib/fishArt";
import type { PinSummary } from "@/lib/api/types";

export function formatDay(iso: string | null): string | null {
  if (!iso) return null;
  // Dates without a time ("2026-09-20") are calendar days: format them in UTC
  // so a viewer west of Greenwich doesn't see the day before.
  const d = iso.length === 10 ? new Date(`${iso}T12:00:00Z`) : new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(iso.length === 10 ? { timeZone: "UTC" } : {}),
  });
}

export function PinBadges({ pin }: { pin: PinSummary }) {
  return (
    <>
      {pin.visibility === "private" && <span className="tag tag-private">Only you</span>}
      {pin.status === "hidden" && (
        <span className="tag tag-hidden" title={pin.status_reason === "reports" ? "Hidden after reports, pending review" : "Hidden by a moderator"}>
          Hidden
        </span>
      )}
      {pin.status === "removed" && <span className="tag tag-removed">Removed</span>}
    </>
  );
}

/** A pin in a grid: its first photo, or the species illustration. */
export function PinCard({ pin, index = 0 }: { pin: PinSummary; index?: number }) {
  const art = pin.species_slug;
  const [wa, wb] = waterFor(art ?? "bluegill");
  return (
    <Link
      href={`/community/${pin.id}`}
      className="pin-card reveal"
      style={{ "--i": Math.min(index, 8) } as React.CSSProperties}
      transitionTypes={["nav-forward"]}
    >
      <div className="pin-card-media" style={{ "--wa": wa, "--wb": wb } as React.CSSProperties}>
        {pin.thumb_url ? (
          // A member's own upload, already resized by the server.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={pin.thumb_url} alt="" loading="lazy" />
        ) : art ? (
          <div className="pin-card-art">
            <FishArt slug={art} uid={`pc-${pin.id}`} />
          </div>
        ) : (
          <div className="pin-card-empty" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M12 21s-6-5.3-6-10a6 6 0 0 1 12 0c0 4.7-6 10-6 10z" />
              <circle cx="12" cy="11" r="2.2" />
            </svg>
          </div>
        )}
        {pin.photo_count > 1 && <span className="pin-card-count">+{pin.photo_count - 1}</span>}
        <div className="pin-card-badges">
          <PinBadges pin={pin} />
        </div>
      </div>
      <div className="pin-card-body">
        <h3>{pin.title}</h3>
        <p className="pin-card-meta">
          {pin.species_label && <span className="pin-species">{pin.species_label}</span>}
          {pin.lake && <span>near {pin.lake.name}</span>}
        </p>
        <p className="pin-card-by muted">
          {pin.is_mine ? "You" : pin.author.display_name} · {formatDay(pin.caught_on ?? pin.created_at)}
        </p>
      </div>
    </Link>
  );
}
