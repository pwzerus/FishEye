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

/** What the photo check said about the species named (backend services/fish_id.py). */
export function speciesCheckText(pin: Pick<PinSummary, "species_check" | "species_check_label" | "species_label">): string | null {
  if (pin.species_check === "confirmed") return `The catch photo shows ${pin.species_label ? `a ${pin.species_label}` : "this fish"}.`;
  if (pin.species_check === "group") {
    return `The catch photo shows ${pin.species_check_label ?? "a look-alike"}; which kind is the angler's call.`;
  }
  return null;
}

export function SpeciesCheck({ pin }: { pin: PinSummary }) {
  const text = speciesCheckText(pin);
  if (!text) return null;
  return (
    <span className={pin.species_check === "confirmed" ? "tag tag-checked" : "tag tag-checked-group"} title={text}>
      ✓ {pin.species_check === "confirmed" ? "Photo-checked" : "Photo: " + (pin.species_check_label ?? "look-alike").replace(/^an? /, "")}
    </span>
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
          {/* The title is the fish's name when none was typed: don't say it twice. */}
          {pin.species_label && pin.species_label !== pin.title && <span className="pin-species">{pin.species_label}</span>}
          <SpeciesCheck pin={pin} />
          {pin.lake ? (
            <span>near {pin.lake.name}</span>
          ) : (
            pin.county_name && <span>{pin.county_name}, {pin.state_code}</span>
          )}
        </p>
        <p className="pin-card-by muted">
          {pin.is_mine ? "You" : pin.author.display_name} · {formatDay(pin.caught_on ?? pin.created_at)}
        </p>
      </div>
    </Link>
  );
}
