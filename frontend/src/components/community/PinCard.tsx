"use client";

import Link from "next/link";

import { FishArt } from "@/components/fish/FishArt";
import { useLocale, useLocaleTag, useT } from "@/i18n/client";
import type { Locale } from "@/i18n/config";
import type { Messages } from "@/i18n/messages";
import { localGroup, localSpecies, withoutArticle } from "@/i18n/names";
import { waterFor } from "@/lib/fishArt";
import type { PinSummary } from "@/lib/api/types";

/** A day as people read it in this language: "Oct 29, 2026", "2026年10月29日". */
export function formatDay(iso: string | null, tag = "en-US"): string | null {
  if (!iso) return null;
  // Dates without a time ("2026-09-20") are calendar days: format them in UTC
  // so a viewer west of Greenwich doesn't see the day before.
  const d = iso.length === 10 ? new Date(`${iso}T12:00:00Z`) : new Date(iso);
  return d.toLocaleDateString(tag, {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(iso.length === 10 ? { timeZone: "UTC" } : {}),
  });
}

export function PinBadges({ pin }: { pin: PinSummary }) {
  const t = useT().catch;
  return (
    <>
      {pin.visibility === "private" && <span className="tag tag-private">{t.onlyYou}</span>}
      {pin.status === "hidden" && (
        <span className="tag tag-hidden" title={pin.status_reason === "reports" ? t.hiddenReports : t.hiddenModerator}>
          {t.hidden}
        </span>
      )}
      {pin.status === "removed" && <span className="tag tag-removed">{t.removed}</span>}
    </>
  );
}

/** Where a catch's point is, in words (backend ADR 0038, 0040). For the
 * point this viewer sees when it isn't the spot, and for what others see. */
export function placeText(
  t: Messages,
  pin: Pick<PinSummary, "lake" | "water" | "county_name" | "state_code">,
  place: PinSummary["location_shown"],
): string {
  if (place === "exact") return t.catch.placeExact;
  if (place === "lake") {
    const name = pin.water?.kind === "lake" ? pin.water.name : pin.lake?.name;
    return name ? t.catch.placeLake(name) : t.catch.placeLakeGeneric;
  }
  if (place === "river" && pin.water?.kind === "river") {
    return t.catch.placeRiver(pin.water.name, pin.county_name ?? null);
  }
  if (place === "county" || place === "river") {
    return pin.county_name ? t.catch.placeCounty(pin.county_name, pin.state_code ?? null) : t.catch.placeCountyGeneric;
  }
  return t.catch.placeArea;
}

/** What the photo check said about the species named (backend services/fish_id.py). */
export function speciesCheckShort(
  t: Messages,
  pin: Pick<PinSummary, "species_check" | "species_check_label" | "species_label" | "species_slug">,
  locale: Locale,
): string | undefined {
  if (pin.species_check === "confirmed") return t.catch.checkConfirmed(localSpecies(pin.species_slug, pin.species_label, locale));
  if (pin.species_check === "group") return t.catch.checkGroup(checkedGroup(t, pin, locale));
  return undefined;
}

/** Which look-alikes a "group" check confirmed, in this language. */
export function checkedGroup(t: Messages, pin: Pick<PinSummary, "species_check_label">, locale: Locale): string {
  return pin.species_check_label ? localGroup(pin.species_check_label, locale) : t.catch.lookAlike;
}

export function SpeciesCheck({ pin }: { pin: PinSummary }) {
  const t = useT();
  const locale = useLocale();
  const text = speciesCheckShort(t, pin, locale);
  if (!text) return null;
  return (
    <span className={pin.species_check === "confirmed" ? "tag tag-checked" : "tag tag-checked-group"} title={text}>
      ✓ {pin.species_check === "confirmed"
        ? t.catch.photoChecked
        : t.catch.photoShows(withoutArticle(checkedGroup(t, pin, locale)))}
    </span>
  );
}

/** "Photo taken here": the photo's own GPS was at the spot (backend
 * services/pins.update_photo_at_spot). */
export function PhotoAtSpot({ pin }: { pin: PinSummary }) {
  const t = useT().catch;
  if (!pin.photo_at_spot) return null;
  return (
    <span className="tag tag-at-spot" title={t.photoAtSpotTitle}>
      <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden="true">
        <path d="M12 21s-6-5.3-6-10a6 6 0 0 1 12 0c0 4.7-6 10-6 10z" />
      </svg>
      {t.photoAtSpot}
    </span>
  );
}

/** A pin in a grid: its first photo, or the species illustration. */
export function PinCard({ pin, index = 0 }: { pin: PinSummary; index?: number }) {
  const t = useT();
  const tag = useLocaleTag();
  const locale = useLocale();
  const species = localSpecies(pin.species_slug, pin.species_label, locale);
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
          {species && pin.species_label !== pin.title && <span className="pin-species">{species}</span>}
          <SpeciesCheck pin={pin} />
          <PhotoAtSpot pin={pin} />
          {pin.water ? (
            <span className="pin-water">{pin.water.name}</span>
          ) : pin.lake ? (
            <span className="pin-water">{pin.lake.name}</span>
          ) : (
            pin.county_name && <span>{pin.county_name}, {pin.state_code}</span>
          )}
        </p>
        <p className="pin-card-by muted">
          {pin.is_mine ? t.catch.you : pin.author.display_name} · {formatDay(pin.caught_on ?? pin.created_at, tag)}
        </p>
      </div>
    </Link>
  );
}
