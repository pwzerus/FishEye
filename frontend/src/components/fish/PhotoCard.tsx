import type { SpeciesPhoto } from "@/lib/api/types";

/**
 * The real photo, pinned to the illustration like a snapshot: comic and
 * photo side by side, so the field marks in the drawing can be checked
 * against the real fish. Shown whole (object-fit: contain, no cropping of
 * a CC BY-SA image), with the credit its licence requires on the card.
 *
 * No photo (Wikimedia unreachable, or no free image) renders nothing: the
 * illustration carries the same field marks, and an empty frame would only
 * advertise a gap.
 */
export function HeroPhoto({ photo, name }: { photo: SpeciesPhoto | null; name: string }) {
  if (!photo) return null;
  return (
    <figure className="hero-photo">
      <span className="hero-photo-label">Real photo</span>
      <div className="hero-photo-frame">
        {/* Hot-linked from Wikimedia as served, next to its credit (ADR 0015). */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={photo.url} alt={`Photo of a ${name}`} width={photo.width} height={photo.height} loading="lazy" />
      </div>
      <figcaption>
        {photo.author} ·{" "}
        {photo.license_url ? (
          <a href={photo.license_url} target="_blank" rel="noreferrer">
            {photo.license}
          </a>
        ) : (
          photo.license
        )}{" "}
        ·{" "}
        <a href={photo.file_page} target="_blank" rel="noreferrer">
          Wikimedia
        </a>
      </figcaption>
    </figure>
  );
}
